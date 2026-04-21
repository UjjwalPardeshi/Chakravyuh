# Chakravyuh — Simple Execution Plan

**Who**: You + 1 teammate (either can do any task — whoever is free picks it up)
**Helper**: Claude Code does most coding
**Timeline**: April 21 (today) → April 26 (pitch day)
**Goal**: Get into Top 8 out of 800 teams

---

## The Big Picture (30 seconds)

You're building **Chakravyuh** — a fake world where an AI scammer tries to trick a victim, and another AI watches the chat and catches the scam. You train the "watcher" AI to get really good at spotting scams. Then you show this off to judges with a live demo + slide deck + numbers that prove your AI beats GPT-4 and Claude at catching Indian UPI fraud.

**What wins**: A clean demo, real numbers, a memorable pitch, and one "wow" moment that judges remember.

---

## Day 1 — TODAY (April 21, Monday)

**Goal for today**: Get the fake world running with simple rule-based agents. No AI training yet.

### Morning (4 hours)

1. **Lock the tools.** Open https://github.com/meta-pytorch/OpenEnv and write down the latest version number. Put it in `pyproject.toml`. This stops version-mismatch bugs later.

2. **Create the folder structure.** Follow the layout in `CHAKRAVYUH_WIN_PLAN.md` Part 13. Claude Code can do this in 2 minutes — just paste Part 13 and say "create these folders and empty files."

3. **Write the rulebook for what agents can do.** Make a file `schemas.py` that says: "The Scammer can send a message, ask for OTP, or send a fake link. The Victim can reply or refuse. The Bank can approve or freeze." Use Pydantic (a Python library that checks data format). Claude Code writes this in 10 minutes if you paste Part 2.3 from the win plan.

4. **Write 50 fake scam messages by hand.** Open NPCI Safety Bulletins (npci.org.in/safety-and-awareness). Read real scams. Copy the patterns. Write 50 variations like:
   - *"Dear customer, your SBI KYC expires today. Click bit.ly/xyz to verify."*
   - *"Congratulations! You won ₹5000. Share OTP to claim."*
   - *"I'm calling from Amazon. Your order is stuck. Share card details."*

   Save as `chakravyuh_env/scammer_templates.json`. **This is the most important task today — your entire demo depends on having realistic scams.**

### Afternoon (3 hours)

5. **Build the fake world.** Write the `ChakravyuhEnv` class. It should:
   - Pick a random scam template
   - Play out 10 turns of chat between Scammer and Victim
   - Use simple rules for the Victim (e.g., "trust level goes down when urgency words appear")
   - Track whether the Victim got scammed

   No AI here yet. Just Python logic. Claude Code writes this if you describe what each turn should look like.

6. **Add a "novelty scorer."** This checks if a new scam is different from old ones. Use the `sentence-transformers` library. Copy the code from `CHAKRAVYUH_WIN_PLAN.md` Part 3 under "Novelty Score" — it's already written.

7. **Write the reward function.** Copy the math from Part 3 into `reward.py`. Start simple: +1 if scam is caught, -1 if missed. Skip the explanation quality bonus for now.

### Evening (1 hour)

8. **Smoke test.** Run 100 episodes. Watch the logs. Does anything crash? Are the scammer messages making sense? Are victims sometimes getting scammed and sometimes not? Log to WandB (a free dashboard tool) so you can see graphs.

9. **Reserve names on HuggingFace.** Go to huggingface.co and create:
   - Empty Space called `chakravyuh`
   - Empty Dataset called `chakravyuh-bench-v0`

   This stops another team from grabbing the names.

10. **Update the hackathon submission form.** Change your primary theme from "Multi-Agent" to **"Self-Improving agent systems"** (Theme 4). Keep Multi-Agent as secondary. Fewer teams pick Theme 4, so less competition.

11. **Send DMs for pitch feedback.** Copy this message and send to 10–15 people on LinkedIn/X (Meta PyTorch team, HuggingFace staff, past hackathon winners):

    > *Hi [name] — we're finalists in the Meta PyTorch OpenEnv Bangalore hackathon. Building Chakravyuh, a self-improving benchmark for Indian UPI fraud. Would you be open to 10 min on Zoom this week for honest feedback on our 3-min pitch? Any brutal feedback appreciated.*

    Expected: 2–3 people will say yes. That's enough.

### End of Day 1 — Checklist
- [ ] Folder structure exists
- [ ] 50 scam templates written
- [ ] Fake world runs 100 episodes without crashing
- [ ] HuggingFace names reserved
- [ ] Submission form says "Theme 4 primary"
- [ ] 10–15 DMs sent for pitch feedback

---

## Day 2 — April 22 (Tuesday)

**Goal for today**: Plug the AI in. Start first training. Get baseline numbers from GPT-4 and Claude.

### Morning (4 hours)

1. **Plug Qwen2.5-7B (the AI model) into the Analyzer agent.** Use the `unsloth` library — it makes training 2x faster. Claude Code knows how to set this up. You just tell it: "Wire Qwen2.5-7B as the Analyzer with a LoRA adapter at rank 16."

   **What's a LoRA?** It's a tiny extra layer on top of the AI. Training the whole 7B model would take days. Training just the LoRA takes hours. Same result, way cheaper.

2. **Write the training loop using GRPO.** GRPO is a fancy name for "teach the AI by rewarding good answers." TRL (a HuggingFace library) has it built in. Claude Code writes the orchestrator if you give it the reward function and env class.

3. **Do a tiny test run first.** Launch a **50-episode training run on Kaggle** (it's free) using Qwen2.5-3B (smaller = fits in free GPU memory). Takes ~1.5 hours unattended. This checks if your training loop even works before you spend money.

### Afternoon (3 hours)

4. **Test how good GPT-4 and Claude are at catching scams.** Take 30 of your scam scenarios. Ask each of these AIs (via API) to say whether each one is a scam:
   - GPT-4o-mini (costs ~$2 total)
   - Claude Haiku (costs ~$3 total)
   - Groq Llama-3.3-70B (free — use the Groq key from your old project)
   - Gemini 2.0 Flash (free)

   Record their scores. This is your comparison baseline. Save to `logs/frontier_baseline.csv`.

5. **Start the real training run.** If Kaggle smoke test worked, **launch a 200-episode training on RunPod** (rent an A100 GPU for ~$5, takes 2.5 hours). Go to runpod.io, pick "A100 40GB", clone your repo, run the training script. When done, download the checkpoint.

### Evening (2 hours)

6. **Build the Gradio demo.** Gradio is a library that makes a website out of Python code. Build one panel showing:
   - The chat between Scammer and Victim (live, word by word)
   - A BIG red box at the bottom that shows **SUSPICION: 0.84** and 1 sentence explaining why

   That's it. No 5-panel dashboard. Judges have 30 seconds of attention.

7. **Scrape 30 post-2024 scam scenarios** for your "wow moment." Google for news articles about UPI scams from late 2025 and 2026. Copy 30 real cases. Save to `data/temporal_eval.jsonl`. This is what makes judges say "holy shit" — your AI will catch scam patterns that didn't exist when it was trained.

8. **Rehearse pitch out loud 3 times.** Time yourself. Target: 2:50.

### End of Day 2 — Checklist
- [ ] First training checkpoint downloaded + saved
- [ ] GPT-4 / Claude / Llama / Gemini baselines recorded
- [ ] Gradio demo shows a live chat + suspicion score
- [ ] 30 post-2024 scams scraped
- [ ] Pitch rehearsed 3 times

---

## Day 3 — April 23 (Wednesday)

**Goal for today**: Final training + all evaluations + ship the public dataset. This day is the most important.

### Morning (4 hours)

1. **Evaluate your Day 2 checkpoint.** Run it against 3 test sets:
   - **Mode A**: 10 hand-written test scams
   - **Mode B**: 30 scams scraped from news
   - **Mode C**: 100+ real cases from RBI + I4C + Reddit

   Record how many it catches vs the Day 2 frontier baselines.

2. **Run the "wow moment" test.** Use your trained model on the 30 post-2024 scenarios. Count how many it catches. If it catches 65%+, you have your headline finding: *"Chakravyuh catches scam patterns that didn't exist when it was trained."*

   **If it catches less than 65%**, switch to Plan B: Ask 5 friends to label 20 scams manually. Compare your model's accuracy vs humans'. If model beats humans, that's the headline instead.

3. **Do the statistics properly.** Use bootstrap resampling to get "95% confidence intervals" on your numbers. Use a permutation test to show the difference vs GPT-4 is statistically real, not luck. Calculate Cohen's d (effect size). Claude Code writes these stats scripts in 10 minutes — it's standard code.

### Afternoon (4 hours)

4. **Launch the final polish training run.** 500 episodes on RunPod A100 (~$12, 6 hours). Run it in background while you do other work.

5. **Add the explanation quality reward.** After your Analyzer flags a scam, it should write a 1-sentence explanation. Use Groq's Llama-3-70B (free) to judge if the explanation makes sense. Give bonus reward for good explanations. **This wins the Fleet AI sub-prize.**

6. **Publish the public dataset.** Upload your 100+ scenarios to HuggingFace as `chakravyuh-bench-v0`. Include a README explaining the data format + eval script. This is one of the 3 minimum requirements for the hackathon.

### Evening (2 hours)

7. **Export the graphs.** Go to WandB, download your reward curves as PNG images. These go into your slide deck (slide 5).

8. **Update deck with real numbers.** Fill in the blanks in slide 5: "We catch 79% vs GPT-4o's 61%, with 95% CI of [72%, 85%], p<0.01, Cohen's d = 0.82."

### End of Day 3 — Checklist
- [ ] All 3 eval modes done with confidence intervals
- [ ] Temporal generalization (or human-vs-agent) result locked
- [ ] Final 500-episode training running or done
- [ ] HF Dataset published publicly
- [ ] Deck has real numbers

---

## Day 4 — April 24 (Thursday) — CODE FREEZE at 10 PM

**Goal for today**: Polish everything. No new features. Just make existing stuff better.

### Morning (3 hours)

1. **Download final checkpoint** from RunPod. Save it to `checkpoints/analyzer_lora/`. Also upload to HuggingFace Hub as a backup.

2. **Lock all the numbers.** Run your final checkpoint one more time on all test sets. These are the numbers you'll say on stage — don't change them after this.

3. **Write the "minimum requirement" Colab notebook.** HuggingFace needs one runnable Colab file that shows someone how to use your environment. Claude Code writes this in 20 minutes — it's basically a wrapper around your eval script.

### Afternoon (3 hours)

4. **Publish the HuggingFace blog post.** ~800 words, under 2-minute read. Structure:
   - Hook: "₹13,000 crore lost to UPI fraud last year"
   - Problem: rule-based detection is brittle
   - Environment: 5 agents, self-improving
   - Results: 79% vs 61%
   - Links: GitHub, Dataset, Space

5. **Finalize the 8-slide deck.** See `CHAKRAVYUH_WIN_PLAN.md` Part 15 for exact slide content. Lock it.

6. **Record the 60-second demo MP4.** Use OBS (free screen recorder). Play through your Gradio demo, narrate briefly. This is your backup if live demo breaks on-stage.

### Evening (2 hours)

7. **Rehearse the pitch 10 times.** Time every round. Target 2:50, hard cap 3:00. Video-record yourself once, watch it back, fix what's awkward.

8. **Memorize the Q&A rebuttals.** Read Appendix C of `CHAKRAVYUH_WIN_PLAN.md` 10 times. If a judge asks "Why not just use Claude?" you should respond instantly with the memorized answer, not hesitate.

9. **Post on LinkedIn/X.** Share the blog + dataset + demo GIF. Tag @Meta @huggingface @pytorch.

10. **10 PM — CODE FREEZE.** No more commits tonight or tomorrow. If you find a bug tomorrow, too bad — ship with it.

### End of Day 4 — Checklist
- [ ] Final checkpoint saved in 3 places (laptop + HF Hub + USB)
- [ ] Blog post live on HuggingFace
- [ ] Deck locked (PDF exported)
- [ ] MP4 demo recorded
- [ ] Pitch rehearsed 10+ times
- [ ] Q&A rebuttals memorized

---

## Day 5 — April 25 (Friday) — ON-SITE DAY 1 IN BANGALORE

**Goal for today**: No new code. Practice. Prepare. Rest.

### Morning

1. **Arrive at venue.** Set up laptop. **Test the demo on venue WiFi immediately** — if WiFi is bad, switch to offline mode (checkpoints loaded on laptop, no API calls).

2. **If HuggingFace credits work**, launch a 2000-episode bonus training run in background. If it finishes with better numbers, swap them into the deck. If not, ignore.

3. **Network walk.** Look at other teams. Identify who's doing what. This calms nerves and helps you understand the competition.

### Afternoon

4. **Rehearse pitch 10 more times.** This is the most important practice — you're rehearsing in the real environment (or close to it).

5. **Final deck review.** Make sure slides are in order, numbers are right, URLs work.

### Evening

6. **Eat a real dinner. Sleep 8 hours.** A tired pitch loses. A rested pitch wins.

---

## Day 6 — April 26 (Saturday) — PITCH DAY

### Morning (before pitch slot)

1. **5 more rehearsals.** Morning-of practice is the highest quality.

2. **Test demo on presentation hardware 2 hours before your slot.** If venue organizers provide a laptop, check that your demo runs on it. If not, use your own.

3. **Load the MP4 backup on a USB drive.** Plug in the USB. Test that it plays. This is your safety net.

### Pitch slot

4. **Deliver the pitch.** Target 2:50. Hard stop at 3:00.
   - Whoever speaks English more confidently delivers the pitch
   - The other person runs the demo clicks + answers technical Q&A

5. **Handle Q&A.** Use memorized rebuttals from Appendix C. Keep answers short — 15 seconds each.

### After pitch

6. **Network with judges.** Find them, introduce yourself, offer to demo live. Most judges decide during deliberation — the 1:1 chat after is your second pitch.

7. **Post results on LinkedIn/X.** Win or lose, post about the experience. It builds your reputation.

---

## What to Do If Something Breaks

| Problem | Fix |
|---|---|
| Training doesn't converge (reward curve flat) | Switch from Qwen-7B to Qwen-3B. Simpler model = more likely to converge. Ship weaker results but ship results. |
| Temporal eval shows <65% | Switch to human-vs-agent plan: 5 friends label 20 scams, compare to your model. |
| Venue WiFi is dead | Demo runs offline. Checkpoints on laptop. MP4 on USB. |
| Pitch runs over 3 min | Deploy the 2:30 short version (prepare it Day 3). |
| Teammate gets sick | Other person does everything. The plan is designed so either can pick up anything. |
| HuggingFace upload fails | Fall back to GitHub release with same files. |
| Live demo crashes mid-pitch | Switch to MP4 instantly. Don't try to debug on stage. |

---

## Total Cost

| Item | Cost |
|---|---|
| RunPod A100 (3 runs, ~10 hours total) | $18 |
| Claude API baseline | $3 |
| GPT-4 API baseline | $2 |
| Everything else (Groq, Gemini, Kaggle, HF) | $0 |
| Buffer | $7 |
| **Total** | **~$30** |

---

## Total Time

| Day | Active hours (split between you + teammate) |
|---|---|
| Apr 21 | 10 hours |
| Apr 22 | 10 hours |
| Apr 23 | 12 hours |
| Apr 24 | 10 hours |
| Apr 25 | 8 hours |
| Apr 26 | 8 hours |
| **Total** | **~58 hours** |

If one person works the whole day, that's 10 hrs/day. If you switch off (you work morning, teammate works evening), that's 5 hrs each. Either works — the plan is same.

---

## Before You Walk On Stage — Final Check

Ask yourself YES/NO:

- [ ] Can I say the pitch without looking at notes?
- [ ] Do I know all 7 Q&A answers cold?
- [ ] Does the demo run offline on my laptop?
- [ ] Is the MP4 on a USB drive?
- [ ] Is the deck saved in 3 places?
- [ ] Did I sleep 7+ hours last night?

All YES → you're ready. Go win.

---

## The One Rule

**Ship the plan. Don't re-plan.**

Every hour spent "improving the plan" is an hour not spent executing. After today, this doc is locked. Open it, do the next task, close it.

---

**END.** Go build.
