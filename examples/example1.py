from pydetrun import deterministic


@deterministic
def run_in_sandbox(foo: str, bar: str):
    print("foo", foo, "bar", bar)
