import logging

import pydetrun

logger = logging.getLogger(__name__)


def test_simple_counter():
    counter = 0

    async def loop_until_counter():
        while counter < 5:
            logger.debug("Waiting, counter at %s", counter)
            await pydetrun.wait()
            logger.debug("Waited, counter at %s", counter)
        return "Yay"

    sched = pydetrun.Scheduler()
    task = sched.add_future(loop_until_counter())

    # Incr and tick
    counter += 1
    sched.tick()
    assert not task.done()
    counter += 1
    sched.tick()
    assert not task.done()

    counter += 3
    sched.tick()
    assert task.done()
    assert task.result() == "Yay"


def test_exception():
    # TODO(cretz): Assert exception comes across the boundary
    pass


def test_bad_event_loop():
    # TODO(cretz): Assert some other event loop is disallowed
    pass


def test_many_async_defs():
    # TODO(cretz): Assert can call other async defs
    pass


def test_task_without_our_wait():
    # TODO(cretz): Assert that any task await not using ours causes failure
    pass


def test_deadlock_detection():
    # TODO(cretz): Assert task not returning in a short time is considered deadlocked
    pass


def test_sync_primitive_event():
    # TODO(cretz): Assert synchronization primitives still work
    pass


def test_future_create():
    # TODO(cretz): Assert regular futures still work (need our own future?)
    pass
