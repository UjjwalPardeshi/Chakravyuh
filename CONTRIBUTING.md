# Contributing to Chakravyuh

Thanks for your interest. Chakravyuh is a research environment, not a maintained product, but contributions that improve reproducibility, extend the bench, or close limitations called out in [`docs/limitations.md`](docs/limitations.md) are welcome.

## What we accept

- Bug fixes (with a regression test).
- New scenarios for `data/chakravyuh-bench-v0/scenarios.jsonl` — must include a category, difficulty, language, and ground-truth label, and pass `make link-check`.
- Additional language coverage for the Scammer / Victim / Analyzer agents.
- New evaluation scripts in `eval/` that emit a JSON artifact in `logs/` (so claims stay measurement-backed).
- Documentation that fixes or extends — never duplicates — an existing file in `docs/`.

## What we do not accept

- New scammer templates or attack patterns intended for live deployment. See [`docs/RESPONSIBLE_USE.md`](docs/RESPONSIBLE_USE.md).
- Changes that break the OpenEnv contract (`openenv validate .` must stay clean).
- Changes that remove or relax tests in `tests/` without a replacement.
- New aggregate-only metrics — every claim needs a per-row or per-scenario backing artifact.

## Workflow

1. Open an issue first describing the change. For larger work, link to a sketch in `docs/` or a comment on an existing limitation.
2. Fork, branch, commit. Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`).
3. Run the local checks before pushing:
   ```bash
   make install            # editable install with eval extras
   pytest tests/ -v        # 341 collected; 338 pass + 3 GROQ-gated skip
   make smoke-test         # in-process env reset+step
   make link-check         # local-link integrity
   ```
4. Open a PR against `main`. CI runs the same checks on Python 3.10 / 3.11 / 3.12 / 3.13.
5. The maintainer will request changes or merge. Squash merges only.

## Adding a new evaluation script

Convention enforced by `tests/test_eval_artifacts.py`:

- Script lives in `eval/<name>.py` and is runnable with `python eval/<name>.py [--args]`.
- Output JSON lives in `logs/<name>.json`.
- The JSON includes a top-level `meta` block with `model_id`, `bench_path`, `seed`, and `timestamp`.
- The script writes nothing outside `logs/` and never overwrites without a `--force` flag.

## Adding a new agent template

Convention enforced by `tests/test_template_loading.py`:

- Templates live in `chakravyuh_env/<agent>_templates.json` (one file per agent).
- Each template has `id`, `category`, `language`, `text`, and `tags` fields.
- New IDs cannot collide with existing ones.

## Reporting a security issue

See [`SECURITY.md`](SECURITY.md). Do not file security issues on the public tracker.

## Code of conduct

By contributing, you agree to abide by the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md).
