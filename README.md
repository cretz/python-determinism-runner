# Python Determinism Runner

This is a POC under development. Goals/requirements:

* Run a lambda/class in a sandbox (e.g. `exec`)
* Sandbox must have known non-deterministic APIs removed (e.g. `datetime.today()`, IO)
* Sandbox must have other sources of non-determinism fixed (e.g. a fixed PRNG seed)
* Sandbox must support `async`/`await` natively and deterministically (even if that means a custom event loop)
* An externally defined "yield" call must pause an async task
  * There must be a way from the outside of the sandbox to run until all tasks have called the yield point or finished
  * There must be a way from the outside to resume all yielded tasks
  * Need to be able to mutate some objects in the sandbox while all yielded