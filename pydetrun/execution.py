import asyncio
import concurrent.futures
import inspect
import logging
import sys
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union

from typing_extensions import ParamSpec

import pydetrun

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


class Execution(Generic[P, T]):
    _executor: Optional[concurrent.futures.Executor]
    _func_in_exec: Callable[P, Union[T, Awaitable[T]]]
    _scheduler: Optional["pydetrun.Scheduler"]

    def __init__(
        self,
        func: Callable[P, Union[T, Awaitable[T]]],
        executor: Optional[concurrent.futures.Executor] = None,
    ) -> None:
        self._executor = executor
        self._scheduler = None
        # Must be a top-level function and not a lambda
        if (
            not inspect.isfunction(func)
            or inspect.ismethod(func)
            or func.__name__ == "<lambda>"
        ):
            raise TypeError("Must be top-level function")
        # Must have executor if it's not a coroutine
        if not inspect.iscoroutinefunction(func) and executor is None:
            raise TypeError("Must have executor if not coroutine function")

        logger.debug("Initializing function %s", func)
        # Grab source for entire file of the function
        source_file = inspect.getsourcefile(func)
        if source_file is None:
            raise RuntimeError("Unable to find file for function")
        with open(source_file) as f:
            file_source = f.read()

        # Regardless of what the first line is, we need to run the preamble. We
        # do this as a call with a semicolon so we don't adversely affect the
        # line numbers of the file.
        file_source = "__pydetrun_execution.preamble();" + file_source

        # As the last statement in the file, we set the function
        # TODO(cretz): Do we need to escape for special function names?
        file_source += f"\n__pydetrun_execution._func_in_exec = {func.__name__}"

        # Globals and locals need to be the same object because exec behavior is
        # different if they are different
        # TODO(cretz): contextvars?
        globals_and_locals = {
            # TODO(cretz): Change __import__ here to add our restrictions
            # TODO(cretz): Remove builtins we don't like
            "__builtins__": __builtins__,
            "__pydetrun_execution": self,
            # TODO(cretz): Other special variables
            # TODO(cretz): Should this be a global or just set at the module level?
            "__file__": source_file,
        }

        # Run exec and check obtained func
        logger.debug("Executing file source:\n%s", file_source)
        # We use compile before exec to have a meaningful filename in traces
        ast = compile(file_source, source_file, "exec")
        exec(ast, globals_and_locals, globals_and_locals)
        if not hasattr(self, "_func_in_exec"):
            raise RuntimeError("Function reference not found")
        logger.debug("Set func as %s", self._func_in_exec)

    # Called inside the exec
    def preamble(self):
        global _current_execution
        _current_execution = self
        # Remove cached modules
        sys.modules = {
            "sys": sys.modules["sys"],
            "builtins": sys.modules["builtins"],
            # TODO(cretz): Needed because importing it checks sys.modules["warnings"]
            "warnings": sys.modules["warnings"],
            # TODO(cretz): Inspect expects this key
            "__main__": None,
        }
        # TODO(cretz): Disable any other modules?
        # sys.modules["importlib"] = None
        # TODO(cretz): Setup the scheduler
        # TODO(cretz): Any other setup

    def start(self, *args, **kwargs) -> asyncio.Task:
        if self._scheduler is not None:
            raise RuntimeError("Already started")
        # Add the future to the scheduler
        scheduler = pydetrun.Scheduler()
        self._scheduler = scheduler
        if inspect.iscoroutinefunction(self._func_in_exec):
            awaitable = self._func_in_exec(*args, **kwargs)
            assert inspect.isawaitable(awaitable)
            fut = scheduler.add_future(awaitable)
        elif self._executor is None:
            raise RuntimeError("No executor")
        else:
            fut = scheduler.add_future(
                self._executor.submit(self._func_in_exec, *args, **kwargs)
            )
        scheduler.tick()
        return fut

    def resume(self) -> None:
        if self._scheduler is None:
            raise RuntimeError("Not started")
        self._scheduler.tick()

    def status(self):
        # TODO(cretz): Impl
        raise NotImplementedError

    def result(self):
        # TODO(cretz): Impl and re-raise w/ proper stack on error
        raise NotImplementedError
