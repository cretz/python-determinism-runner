
def deterministic(func):
    def run(*args, **kwargs):
        print("pre")
        func(*args, **kwargs)
        print("post")
    return run