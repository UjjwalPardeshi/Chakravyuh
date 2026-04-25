# Submission Guidelines

## ✅ Non-Negotiables

> These are non-negotiable. Submissions missing any of these are at a serious disadvantage.

- **Use OpenEnv (latest release).** Build on top of the framework; don't reinvent the wheel.
- **A working training script** using Unsloth or Hugging Face TRL, ideally as a Colab notebook so judges can re-run it.
- **Evidence that you actually trained** — at minimum, loss and reward plots from a real run.
- **A short writeup** — a mini-blog on Hugging Face or a < 2 minute video on YouTube explaining what your environment does and what you trained, or a short slide deck/presentation. Make sure all materials are linked from your README so judges can access them easily.
- **Push your environment to a Hugging Face Space** so it's discoverable and runnable.
- **A README** that motivates the problem, explains how the env works, and shows results.
  - Must include a link to the environment in the Hugging Face Space.
  - Must link to all additional materials (videos, blog posts, slides, presentations, etc.).
- **Do not include large video files** in your Env submission on HF Hub — keep submission size small and use URLs as reference links to additional materials.

---

## 🚀 Pick an Ambitious, Original Problem

The themes (problems) are deliberately open. Use them as launching pads, not boxes. Judges have seen a lot of chess, snake, tic-tac-toe, and grid-world clones. To score well on innovation, you need a genuinely fresh angle.

Ask yourself:

- Does this environment exist to teach an LLM something it currently can't do well?
- Is the domain underexplored in RL/LLM training?
- Could a researcher write a paper about training on this?

---

## 🎯 Design a Reward Signal That Actually Teaches

A great environment has a reward function that:

- Provides a **rich, informative signal** (not just 0/1 at the end)
- **Captures something hard to measure** in a clever way
- Uses **OpenEnv's Rubric system thoughtfully** (composable rubrics > monolithic scoring)
- Is **hard to game** — an agent that exploits the reward without solving the task should not get high scores

---

## 🏋️ Show Real Training, End to End

The bar isn't "training script exists." The bar is **"training script runs against the environment, the agent learns, and you can show it."**

Concretely:

- Your training loop should **connect to your environment** (not a static dataset)
- Train long enough that the **curves mean something**
- **Compare a trained agent vs. a random/untrained baseline** — quantitatively and/or qualitatively
- Include the **plots and numbers** in your README and writeup

---

## 📊 Make Your Plots Readable

Reviewers spend seconds, not minutes, on each plot. Help them out:

- **Label both axes** (e.g. "training step" / "episode" on x, "reward" / "loss" on y) and include units where they apply
- **Save plots as `.png` or `.jpg`** and commit them to the repo — don't leave them only in a Colab cell or a deleted W&B run (if you ran via W&B, include a link to that specific run)
- **Embed key plots in your README** with a one-line caption explaining what each one shows
- If you have multiple runs (baseline vs. trained, ablations, etc.), **put them on the same axes** so the comparison is obvious

---

## 📖 Tell a Story, Not an API Doc

Your README, blog, and pitch should answer:

| Section | Question |
|---|---|
| **Problem** | What capability gap or interesting domain are you targeting? |
| **Environment** | What does the agent see, do, and get rewarded for? |
| **Results** | What changed after training? Show it. |
| **Why it matters** | Who would care, and why? |

A reviewer should be able to read your README in **3–5 minutes** and want to try your environment.

> If you have a video, HF post, or anything else interesting, make sure it's linked from your README.

---

## 🔧 Engineer It Cleanly (Table Stakes)

Engineering quality matters less than ambition, but sloppy work hurts. Make sure you:

- Use OpenEnv's `Environment` / `MCPEnvironment` base classes properly
- Respect the **client / server separation** — clients should never import server internals
- Follow the **standard Gym-style API** (`reset`, `step`, `state`)
- Have a valid **`openenv.yaml` manifest**
- Do **not** use reserved tool names (`reset`, `step`, `state`, `close`) for MCP tools

---

## 💡 Final Note

Judges are looking for environments that **push the frontier of what we can train LLMs to do.**

Be ambitious. Pick a problem you find genuinely interesting — that almost always produces better work than chasing what you think judges want.

**Good luck.**
