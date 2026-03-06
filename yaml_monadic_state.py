"""
YAML Anchors as Monadic Stateful Computation
=============================================

Core idea: YAML anchors (&name) and aliases (*name) form a natural model for
the State monad. An anchor *defines* a value and threads it forward; an alias
*references* that previously-defined value. This mirrors how the State monad
threads hidden state through a chain of computations:

    State s a  =  s -> (a, s)
    bind (>>=) :  State s a -> (a -> State s b) -> State s b

We encode this in YAML by treating anchors as "put" (write state) and aliases
as "get" (read state). A YAML document becomes a monadic program where each
mapping step can read prior state and produce new state for subsequent steps.

Requirements: pip install pyyaml
"""

import yaml
from typing import Any


# ---------------------------------------------------------------------------
# 1. The YAML "program" — anchors thread state between computation steps
# ---------------------------------------------------------------------------

PROGRAM = """\
# Each step is a monadic action: it can read previous state (*alias)
# and write new state (&anchor) for downstream steps.

# --- bind step 1: initialize state ---
- step: init
  state: &s0 10                    # put 10 into state

# --- bind step 2: read state, double it, write new state ---
- step: double
  input: *s0                       # get  -> 10
  state: &s1 20                    # put 20 (we compute this below dynamically)

# --- bind step 3: read state, add 7, write new state ---
- step: add7
  input: *s1                       # get  -> 20
  state: &s2 27                    # put 27

# --- bind step 4: read two prior states (demonstrates shared context) ---
- step: combine
  older: *s0                       # get original state  -> 10
  newer: *s2                       # get latest state    -> 27
  state: &s3 37                    # put 37 (sum)

# --- return: extract final value ---
- step: return
  result: *s3                      # 37
"""


def run_yaml_program(source: str) -> list[dict]:
    """Parse a YAML monadic program and return its steps."""
    return yaml.safe_load(source)


# ---------------------------------------------------------------------------
# 2. A Python State monad that mirrors the YAML structure
# ---------------------------------------------------------------------------

class State:
    """
    State s a: a computation that takes state s and returns (a, s').

    This is the classic Haskell State monad translated to Python.
    We'll show that the YAML anchor/alias pattern above is isomorphic to
    chaining these with bind.
    """

    def __init__(self, run):
        # run : s -> (a, s)
        self.run = run

    def bind(self, f):
        """
        (>>=) :: State s a -> (a -> State s b) -> State s b

        Thread state through: run self, feed result to f, run that.
        """
        def new_run(s):
            a, s1 = self.run(s)        # run first computation
            return f(a).run(s1)        # feed result + new state to next
        return State(new_run)

    def then(self, next_state):
        """(>>) :: discard result, keep state threading."""
        return self.bind(lambda _: next_state)

    @staticmethod
    def ret(a):
        """return :: a -> State s a  — inject a value, leave state unchanged."""
        return State(lambda s: (a, s))

    @staticmethod
    def get():
        """get :: State s s  — read the current state."""
        return State(lambda s: (s, s))

    @staticmethod
    def put(s):
        """put :: s -> State s ()  — overwrite the state."""
        return State(lambda _: (None, s))

    @staticmethod
    def modify(f):
        """modify :: (s -> s) -> State s ()  — apply f to the state."""
        return State(lambda s: (None, f(s)))


# ---------------------------------------------------------------------------
# 3. Replicate the YAML program as a monadic computation
# ---------------------------------------------------------------------------

def yaml_equivalent_monad() -> State:
    """
    This is the *same* program as the YAML above, but expressed with bind.

    YAML anchors   <=>  put / modify
    YAML aliases   <=>  get
    YAML step list <=>  bind chain
    """
    return (
        State.put(10)                          # &s0  10
        .then(State.get())                     # *s0
        .bind(lambda s0:                       # s0 = 10
            State.put(s0 * 2)                  # &s1  20
            .then(State.get())                 # *s1
            .bind(lambda s1:                   # s1 = 20
                State.put(s1 + 7)              # &s2  27
                .then(State.get())             # *s2
                .bind(lambda s2:               # s2 = 27
                    State.put(s0 + s2)         # &s3  37 (note: s0 still accessible via closure = alias)
                    .then(State.get())         # *s3
                    .bind(lambda s3:
                        State.ret(s3)          # return 37
                    )
                )
            )
        )
    )


# ---------------------------------------------------------------------------
# 4. A YAML-driven interpreter that actually executes anchors as state ops
# ---------------------------------------------------------------------------

DYNAMIC_PROGRAM = """\
# This version uses symbolic operations so the interpreter computes values.
# Anchors still thread the state forward.

- op: put
  value: &s0 10

- op: modify
  fn: "double"
  input: *s0
  result: &s1 __computed__

- op: modify
  fn: "add7"
  input: *s1
  result: &s2 __computed__

- op: modify
  fn: "sum"
  inputs: [*s0, *s2]
  result: &s3 __computed__

- op: get
  result: *s3
"""

FUNCTIONS = {
    "double": lambda x: x * 2,
    "add7":   lambda x: x + 7,
    "sum":    lambda xs: sum(xs),
}


def interpret_yaml_monad(source: str) -> tuple[Any, list[dict]]:
    """
    Interpret a YAML document as a sequence of State monad operations.

    Returns (final_value, trace) where trace logs each step.
    """
    steps = yaml.safe_load(source)
    state = None
    trace = []

    for step in steps:
        op = step["op"]

        if op == "put":
            state = step["value"]
            trace.append({"op": "put", "state": state})

        elif op == "modify":
            fn = FUNCTIONS[step["fn"]]
            # The YAML alias (*sN) resolves to the literal anchor value,
            # but for __computed__ placeholders we use the live state instead.
            raw = step.get("input") or step.get("inputs")
            if isinstance(raw, list):
                arg = [state if v == "__computed__" else v for v in raw]
            else:
                arg = state if raw == "__computed__" else raw
            state = fn(arg)
            trace.append({"op": "modify", "fn": step["fn"], "arg": arg, "state": state})

        elif op == "get":
            trace.append({"op": "get", "result": state})

    return state, trace


# ---------------------------------------------------------------------------
# 5. Run everything and show the isomorphism
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("YAML ANCHORS AS MONADIC STATE — DEMONSTRATION")
    print("=" * 60)

    # --- Static YAML program (precomputed values in anchors) ---
    print("\n--- 1. Static YAML program (anchors carry literal values) ---")
    steps = run_yaml_program(PROGRAM)
    for s in steps:
        print(f"  {s['step']:>8}: {s}")
    final_yaml = steps[-1]["result"]
    print(f"\n  Final result from YAML: {final_yaml}")

    # --- Python State monad (equivalent computation) ---
    print("\n--- 2. Python State monad (equivalent computation) ---")
    result, final_state = yaml_equivalent_monad().run(None)
    print(f"  Monad result: {result}")
    print(f"  Final state:  {final_state}")

    # --- Dynamic YAML interpreter ---
    print("\n--- 3. Dynamic YAML interpreter (anchors + computed state) ---")
    result, trace = interpret_yaml_monad(DYNAMIC_PROGRAM)
    for t in trace:
        print(f"  {t}")
    print(f"\n  Final result: {result}")

    # --- Verify isomorphism ---
    print("\n--- 4. Isomorphism check ---")
    assert final_yaml == result == final_state == 37, "Mismatch!"
    print("  All three representations produce 37. The isomorphism holds.")

    print("\n" + "=" * 60)
    print("EXPLANATION")
    print("=" * 60)
    print("""
YAML anchor/alias  |  State monad equivalent
-------------------+---------------------------
  &s0 10           |  put 10
  *s0              |  get  (reads 10)
  &s1 20           |  put 20
  *s1              |  get  (reads 20)
  step list order  |  bind (>>=) chaining

Why this works:

1. YAML anchors (&name) define a named value at one point in the document.
   This is analogous to `put` — writing a value into the state.

2. YAML aliases (*name) reference a previously-defined anchor.
   This is analogous to `get` — reading the current (or a prior) state.

3. The sequential ordering of YAML list items mirrors monadic `bind`:
   each step can depend on state produced by earlier steps, but not
   later ones — exactly like the State monad's threading discipline.

4. Unlike the pure State monad (which has exactly one "current" state),
   YAML anchors let you reference ANY prior state by name. This is
   actually *more* powerful — it's equivalent to a State monad over
   a dictionary/map of named slots, or equivalently, the Reader monad
   layered on top of State (giving you a persistent environment).

Key insight: YAML's anchor scoping rules enforce the same causality
constraint as monadic bind — you cannot reference an anchor before
it is defined, just as you cannot use a value before the State monad
has computed it.
""")
