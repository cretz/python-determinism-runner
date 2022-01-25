import inspect
import logging
import sys
from typing import Callable, Generic, TypeVar
from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


class LocalExecution(Generic[P, T]):
    def __init__(self, func: Callable[P, T], frame: inspect.FrameInfo) -> None:
        logger.debug("Initializing function %s", func)
        self.frame = (frame.filename, frame.lineno, frame.function)
        # Grab source for entire file of the function
        with open(inspect.getsourcefile(func)) as f:
            file_source = f.read()

        # Regardless of what the first line is, we need to run the preamble. We
        # do this as a call with a semicolon so we don't adversely affect the
        # line numbers of the file.
        file_source = "__pydetrun_execution.preamble();" + file_source

        # Globals and locals need to be the same object because exec behavior is
        # different if they are different
        # TODO(cretz): contextvars?
        globals_and_locals = {
            # TODO(cretz): Change __import__ here to add our restrictions
            # TODO(cretz): Remove builtins we don't like
            "__builtins__": __builtins__,
            "__pydetrun_execution": self,
        }

        # Run exec and check obtained func
        self.func = None
        logger.debug("Executing file source:\n%s", file_source)
        exec(file_source, globals_and_locals, globals_and_locals)
        if self.func is None:
            raise RuntimeError("Function reference not found")
        logger.debug("Set func as %s", self.func)

    def is_for_frame(self, frame: inspect.FrameInfo) -> bool:
        return self.frame == (frame.filename, frame.lineno, frame.function)

    # Called inside the exec
    def preamble(self):
        # Remove all cached modules
        sys.modules.clear()
        # TODO(cretz): Disable any other modules?
        sys.modules["importlib"] = None
        # TODO(cretz): Setup the scheduler
        # TODO(cretz): Any other setup

    async def start(self, *args, **kwargs):
        # TODO(cretz): Impl and return status()
        raise NotImplementedError

    async def resume(self):
        # TODO(cretz): Impl and return status()
        raise NotImplementedError

    def status(self):
        # TODO(cretz): Impl
        raise NotImplementedError

    def result(self):
        # TODO(cretz): Impl and re-raise w/ proper stack on error
        raise NotImplementedError


def deterministic(func: Callable[P, T]) -> Callable[P, LocalExecution[P, T]]:
    # TODO(cretz): Think about how to possibly support methods
    if inspect.ismethod(func):
        raise TypeError("Function cannot be method")

    caller_frame = inspect.stack()[1]
    is_in_execution = (
        "__pydetrun_execution" in globals()
        and __pydetrun_execution.is_for_frame(caller_frame)
    )
    # If we're defining this in execution, store the function
    if is_in_execution:
        __pydetrun_execution.func = func

    def run(*args, **kwargs):
        # If this is trying to be run inside the execution for itself, fail
        # TODO(cretz): Do we care about recursion prevention?
        if is_in_execution:
            raise RuntimeError("Recursive invocation of function not allowed")
        # We make a new instance and start inside the invocation instead of
        # outside because we want a separate execution for each invocation.
        # There is not enough preparation logic to have any outside instance.
        return LocalExecution(func, caller_frame).start(*args, **kwargs)

    return run
