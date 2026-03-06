"""
Sieve of Eratosthenes as a YAML Monadic State Program
======================================================

The state threaded through the monad is a list of candidate numbers.
Each "sieve" step reads the current candidates (*alias), removes
multiples of a prime, and writes the reduced list into a new anchor (&name).
The chain of anchors IS the bind chain of the State monad.
"""

import yaml
from typing import Any


# ---------------------------------------------------------------------------
# The YAML program — Sieve of Eratosthenes via anchored state
# ---------------------------------------------------------------------------

SIEVE_PROGRAM = """\
# ---------------------------------------------------------------
# Sieve of Eratosthenes: primes below 100
# ---------------------------------------------------------------
# State = list of remaining candidate integers.
# Each step:  get candidates -> remove multiples of p -> put result
# Anchors (&) = put,  Aliases (*) = get,  list order = bind (>>=)
# ---------------------------------------------------------------

# Step 0: initialize candidates [2..99]
- op: range
  start: 2
  stop: 100
  result: &candidates_init __computed__

# Step 1: p=2 — first prime; sieve out its multiples
- op: sieve
  prime: 2
  from: *candidates_init
  result: &after_2 __computed__

# Step 2: p=3
- op: sieve
  prime: 3
  from: *after_2
  result: &after_3 __computed__

# Step 3: p=5  (4 was already removed by step 1)
- op: sieve
  prime: 5
  from: *after_3
  result: &after_5 __computed__

# Step 4: p=7  (the last prime whose square is < 100)
- op: sieve
  prime: 7
  from: *after_5
  result: &after_7 __computed__

# No more sieving needed: next prime is 11, and 11^2 = 121 > 99.
# Every composite <= 99 has a factor <= 9, so we've caught them all.

# Final step: extract the primes
- op: get
  from: *after_7
"""


# ---------------------------------------------------------------------------
# Extended interpreter with sieve-aware operations
# ---------------------------------------------------------------------------

def interpret(source: str) -> tuple[Any, list[dict]]:
    """
    Interpret a YAML sieve program.

    Supported ops:
      range  — put list(range(start, stop)) into state
      sieve  — remove multiples of `prime` from state (keep prime itself)
      get    — return current state
    """
    steps = yaml.safe_load(source)
    state = None
    trace = []

    for step in steps:
        op = step["op"]

        if op == "range":
            state = list(range(step["start"], step["stop"]))
            trace.append({
                "op": "range",
                "desc": f"candidates {step['start']}..{step['stop'] - 1}",
                "size": len(state),
            })

        elif op == "sieve":
            p = step["prime"]
            before = len(state)
            # Keep p itself, remove all other multiples of p
            state = [n for n in state if n == p or n % p != 0]
            removed = before - len(state)
            trace.append({
                "op": "sieve",
                "prime": p,
                "removed": removed,
                "remaining": len(state),
            })

        elif op == "get":
            trace.append({"op": "get", "result_size": len(state)})

    return state, trace


# ---------------------------------------------------------------------------
# Run it
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("SIEVE OF ERATOSTHENES — YAML MONADIC STATE PROGRAM")
    print("=" * 60)

    print("\n--- YAML source ---")
    for i, line in enumerate(SIEVE_PROGRAM.strip().splitlines(), 1):
        print(f"  {i:3}: {line}")

    print("\n--- Execution trace ---")
    primes, trace = interpret(SIEVE_PROGRAM)
    for t in trace:
        if t["op"] == "range":
            print(f"  range  → {t['desc']} ({t['size']} candidates)")
        elif t["op"] == "sieve":
            print(f"  sieve p={t['prime']:>2} → removed {t['removed']:>2} composites, {t['remaining']} remain")
        elif t["op"] == "get":
            print(f"  get    → returning {t['result_size']} primes")

    print(f"\n--- Primes below 100 ({len(primes)} total) ---")
    # Print in rows of 10
    for i in range(0, len(primes), 10):
        row = primes[i:i + 10]
        print("  " + "  ".join(f"{p:>2}" for p in row))

    # Verify against a simple trial-division reference
    def is_prime(n):
        if n < 2:
            return False
        for d in range(2, int(n**0.5) + 1):
            if n % d == 0:
                return False
        return True

    expected = [n for n in range(2, 100) if is_prime(n)]
    assert primes == expected, f"Mismatch!\n  got:      {primes}\n  expected: {expected}"
    print(f"\n  Verified: matches trial-division reference.")
