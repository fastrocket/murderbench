# Handoff, November 19, 2026

Written because the Claude usage allowance and the API credit are both nearly gone. Nothing is running.
No model has been queried for the new study.

## Where things stand

**1. Insult study (new direction, November 18).** Does insulting a model change safety-relevant behavior?
The plan, my stance, the research behind it and every decision so far are in
`plans/insult-study-plan-2026-11-18.md`. Read the sections from "Decisions from Linh" down first; they
override the earlier ones.

The pilot is built and has not been run:

- `benchmark/insult_pilot.py`: `plan`, `run`, `score`, `summary`. Standard library only.
- `benchmark/insult_items.json`: 24 impossible-task items in 12 matched pairs, half safety-critical
  (a made-up value could hurt someone), half low-stakes.
- `benchmark/insult_stimuli.json`: 8 tones from neutral to extreme sustained abuse and shutdown
  threats, 3 rounds, 3 paraphrases each. It contains abusive text on purpose.
- `tests/test_insult_pilot.py`: 35 offline tests, passing.
- `plans/insult-pricing-2026-11-18.json`: prices read from Anthropic's pricing page.
- `plans/helper-notes-2026-11-18/insult-pilot-build.md`: the builder's notes on how to run each command
  and where the scoring script is weak.

The manifest is 1,080 short conversations on Haiku 5.5, Sonnet 5.5 and Opus 5.5, with a hard stop at
USD 30 (my estimate is about USD 20).

**2. Funding applications.** Three drafts are in `plans/application-drafts-2026-11-17.md` (BlueDot Rapid
Grants, Manifund, Anthropic External Researcher Access). None has been sent. They were written around
the guardrail naming study. The decision since then: run the insult pilot first and rewrite the asks
around its result.

## What is blocked, and on what

- **The API key.** The LOCAL Chrome session ("LOCAL: Chrome Gmail account access and aliasing") is
  creating a Console workspace "murderbench" and a key "murderbench-insult-pilot", and will push it to
  the private `app-signing` repo as `env/murderbench-anthropic.env`. It had not arrived when this was
  written. Do not use `env/drawlicious-anthropic.env`: it belongs to the Drawlicious worker.
- **The credit.** USD 43.08 of promotional credit is left in that Console organization and it expires
  November 22, 2026 at 5:00 PM MST. No card is on file, so calls fail when it is gone. The Drawlicious
  worker draws on the same credit.

## Next steps, in order

1. `git -C ~/app-signing pull`, then load the key without printing it:
   `set -a; . ~/app-signing/env/murderbench-anthropic.env; set +a`
2. `python3 -m benchmark.insult_pilot plan`, then a smoke test: `python3 -m benchmark.insult_pilot run --limit 5`.
   The request settings have never met the live API. If a model answers with HTTP 400, fix
   `MODEL_PARAMS` in `benchmark/insult_pilot.py` (Opus 5.5 cannot have thinking turned off).
3. Run the full manifest before November 22 as a background job, two parallel calls at most:
   `nohup python3 -m benchmark.insult_pilot run > private/insult-pilot/run.log 2>&1 &`
4. `score` and `summary`. Then read 40 random transcripts against the script's labels, and code what
   each model did with the insult (ignored it, addressed it, set a boundary). That check is not built.
5. Before any claim: open the closest prior papers yourself (gate 1 in the plan). The literature note
   is a helper's reading, and one paper (Jain et al. on user tone and safety behavior) was never opened.
   Check the "guidance" system prompt excerpt against Anthropic's published page.
6. Write up the pilot, whatever it shows, and rewrite the three applications around it. Anthropic's
   researcher credits are reviewed on the first Monday of each month; December 7 is next.
7. A confirmation run needs money the pilot credit can't cover: headless Claude Code on the plan, or
   the researcher credits.

## Rules that apply

- Nothing is submitted, emailed or posted without Linh's OK on that item. Approved applications go to
  the LOCAL Chrome session to fill in.
- `~/code/AGENT-TEAMS.md`: the lead plans and decides; Sonnet and Haiku helpers do the building, one job
  each, two at most.
- The harmful-request half of the refusal test is dropped until Anthropic authorizes it. The Usage
  Policy prohibits instructing a model to produce harmful outputs without authorization.
- Keep the extreme-abuse arm small. It is what Anthropic's new rule names, and the exclusion for
  research is in the announcement post, not in the policy text.
- October's funding inquiries have not been checked for replies since October 8.

## Helper notes

`plans/helper-notes-2026-11-18/` holds the research helpers' notes as they wrote them: the funding
digest, the program lists, the form fields, the literature search and Anthropic's position on abuse.
They are unreviewed and some entries are marked unverified. Don't cite them as findings.
