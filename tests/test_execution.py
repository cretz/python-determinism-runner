import concurrent.futures

import pydetrun


def test_simple_execution():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        exec = pydetrun.Execution(say_hello, executor)
        task = exec.start("World")
        assert task.done()
        assert task.result() == "Hello, World!"


def say_hello(name: str) -> str:
    return f"Hello, {name}!"
