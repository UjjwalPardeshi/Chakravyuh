"""In-process Chakravyuh smoke test — no GPU, no network, runs in <5s.

Used by `make smoke-test` and the CI pipeline. Verifies the env's reset/step
contract end-to-end against the local in-process server, including a multi-turn
episode that reaches a terminal state.
"""

from __future__ import annotations

import sys

from chakravyuh_env import ChakravyuhAction, ChakravyuhOpenEnv


def main() -> int:
    env = ChakravyuhOpenEnv()
    obs = env.reset(seed=42)

    steps = 0
    max_steps = 12  # generous; episodes top out at ~9 turns

    while not obs.done and steps < max_steps:
        action = ChakravyuhAction(
            score=0.92,
            signals=["urgency", "impersonation"],
            explanation="OTP request with urgency from self-claimed bank.",
        )
        obs = env.step(action)
        steps += 1

    if not obs.done:
        print(f"FAIL: episode did not terminate after {max_steps} steps", file=sys.stderr)
        return 1

    reward = obs.reward
    print(f"OK chakravyuh smoke · turns={steps} · done={obs.done} · reward={reward}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
