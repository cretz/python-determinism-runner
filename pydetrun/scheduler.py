import asyncio
import collections
import concurrent.futures
from typing import Awaitable, Deque, Optional, Union


class Scheduler:
    _loop: asyncio.AbstractEventLoop
    _waiters: Deque[asyncio.Future]

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        # Set of tasks waiting on a single wakeup (modeled off asyncio.Event)
        self._waiters = collections.deque()
        # Put ourself on the loop
        setattr(self._loop, "__pydetrun_scheduler", self)

    @staticmethod
    def get_running_scheduler() -> "Scheduler":
        scheduler: Optional[Scheduler] = getattr(
            asyncio.get_running_loop(), "__pydetrun_scheduler", None
        )
        if scheduler is None:
            raise RuntimeError("no scheduler in this event loop")
        return scheduler

    def add_future(
        self, future: Union[Awaitable, concurrent.futures.Future]
    ) -> asyncio.Task:
        if isinstance(future, concurrent.futures.Future):
            future = asyncio.wrap_future(future, loop=self._loop)
        return asyncio.ensure_future(future, loop=self._loop)

    async def wait(self) -> None:
        # Mark current task as having reached our wait
        curr_task = asyncio.current_task(self._loop)
        if curr_task is None:
            raise RuntimeError("no current task or not in current event loop")
        setattr(curr_task, "__pydetrun_waiting", True)

        # Create future and wait on it
        fut = self._loop.create_future()
        self._waiters.append(fut)
        try:
            await fut
            return
        finally:
            # Unset that the task is waiting and remove from waiters
            setattr(curr_task, "__pydetrun_waiting", False)
            self._waiters.remove(fut)

    def tick(self) -> None:
        # Go over every waiter and set it as done
        for fut in self._waiters:
            if not fut.done():
                fut.set_result(True)

        # Run one iteration
        # Ref https://stackoverflow.com/questions/29782377/is-it-possible-to-run-only-a-single-step-of-the-asyncio-event-loop
        self._loop.call_soon(self._loop.stop)
        self._loop.run_forever()

        # Make sure every task is done or waiting on our future
        for task in asyncio.all_tasks(self._loop):
            if not getattr(task, "__pydetrun_waiting", False):
                raise RuntimeError(
                    "Task did not complete and is not waiting on this scheduler"
                )


async def wait() -> None:
    await Scheduler.get_running_scheduler().wait()
