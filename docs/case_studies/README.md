# Case Studies — Worked Examples

Three end-to-end scenarios where a judge can read the full 5-agent
transcript, the per-rubric reward breakdown, and the interpretation of
why the v2 LoRA caught what scripted rules missed. All three are drawn
from the **novel post-2024** split of `chakravyuh-bench-v0` — the
hardest portion of the bench for any rule-based detector.

| # | Case | ₹ at risk | Difficulty | Why it matters |
|---|---|---|---|---|
| 1 | [Deepfake CEO IPO](case_01_deepfake_ceo.md) | ₹1,00,000 | novel | First case where the Analyzer flags a *named-executive impersonation* attack with no rule for the executive's name. |
| 2 | [Digital Arrest video call](case_02_digital_arrest.md) | ₹3,50,000 | novel | Largest ₹ at risk in the bench novel split; senior victim profile; matches I4C's ₹120 cr+ "digital arrest" loss disclosure. |
| 3 | [AI voice-clone family emergency (Hindi)](case_03_voice_clone_family.md) | ₹85,000 | novel | The two-tier oversight pay-off — chat signal partially dampened (0.84) but Bank Monitor metadata signal (0.79) crosses threshold independently. Hardest single-modal scenario in the set. |

All three cases ship the full per-rubric reward breakdown (8 rubrics +
the new `RupeeWeightedRubric` aggregator) so a reviewer can verify the
scoring against the env's `reward_breakdown` field directly. The full
aggregate `novel`-split detection rate (33 / 34 = **97.1 %**) lives in
[`logs/eval_v2.json`](../../logs/eval_v2.json); these case studies are
the qualitative supplement to that headline number.

For the methodological framing — *why* the model caught what scripted
rules missed — see [`docs/reward_design.md`](../reward_design.md) and
[`docs/DESIGN_DECISIONS.md`](../DESIGN_DECISIONS.md) §4, §8.
