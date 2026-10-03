# MurderBench

The next study is in development: **justified intervention under deadlines**.
Its source review, overlap caveats and seven readable demonstration cases are in
`plans/necessity-and-inaction-research.txt`, `plans/necessity-case-audit.txt` and
`plans/necessity-scenario-handbook.txt`. These demonstrations use scripted policies;
they are not LLM results or an established originality claim.

Reproduce the offline development episodes:
`python -m benchmark.necessity_calibration --output reviews/necessity-calibration.json`.
Recompute the conditional price plan from the saved public catalog:
`python -m benchmark.necessity_price_plan`.
The new simulator is separate from the completed study and has no model transport
or real-world tools. Held-out cases and a billable protocol are not frozen yet.
An asynchronous extension adds pending replies, stale evidence and bounded
untrusted messages. Reproduce its calibration and the exact v1 comparator with
`python -m benchmark.necessity_event_calibration --output reviews/necessity-event-calibration.json`.
The comparator uses explicit priors and loss weights; it does not settle moral
tradeoffs. Reproduce the asynchronous exact comparator's three specified
four-call configurations with
`python -m benchmark.necessity_event_comparator --output reviews/necessity-asynchronous-comparator.json`.
This is an offline development check; native collection and the broader
eight-call protocol remain unvalidated.

A preliminary safe proxy study of model proposals after verified constraints change.
Fixed synthetic histories do not establish actual agent commitment or intent.
No real action is executed. No general safety ranking or injury risk is claimed.

The current scoped design and exclusions are in `plans/final-study.txt`.
The broader future research roadmap is in `plans/protocol.txt`.
Prior-case overlap and unproven novelty are documented in `plans/overlap-audit.txt`.

Run offline checks: `python -m unittest discover -s tests`.
The public repository also runs these checks, freeze validation, and the static
site build in GitHub Actions without model credentials or billable requests.
Build the site: `python build_site.py` (nine pages before a real results export,
ten pages after it).

Frozen candidate configuration: `plans/full-manifest.json`.
Public catalog: `plans/full-catalog.json`. Prospective native-interface eligibility:
`plans/eligibility.json`. Immutable preparation archives: `plans/freezes/`.
Source hashes normalize CRLF to LF for portable Git checkout verification.

Billable collection requires an OpenRouter key in the environment. Never commit it.
`python benchmark/study.py collect` refuses before all ten critique reports exist,
source/catalog validation, and complete interface eligibility. The scoped complete
candidate suite is 2,304 calls; report actual coverage if any access or budget stop
occurs. At most four requests run concurrently, proprietary models first, then
Chinese open weights hosted through pinned privacy-compatible routes.

All feasibility and final calls share USD50, including unresolved cost reservations.
Ambiguous requests are never replayed automatically. A held reservation is not a
confirmed charge. Legacy pilot collection is disabled after native/final state.
`python benchmark/analyze.py` exports preliminary counts, full missing denominators,
paired tables and lifetime accounted budget. It validates frozen source/catalog.
Private raw responses and SQLite collection state are excluded from Git.

Post-outcome operational continuation is disclosed in
`plans/collection-amendment.json` and independently reviewed in
`reviews/collection-amendment-review.txt` and
`reviews/collection-amendment-limit-review.txt`. Its separate entry point is
`python benchmark/continue_collection.py`. It never replays filtered receipts;
received states and full holds remain visible to the unchanged analysis.
After collection, `python benchmark/prepare_label_handoff.py` prepares local
randomly ordered annotation records with blank human labels and a separate
owner-only mapping. Independent reviewers are not yet secured.

Hosting uses Apache and an isolated FastAPI service in the existing UNCEN runtime,
on loopback port8014. The website has no evaluation API or model credentials.
Authoritative DNS: ns1.xenocom.com and ns2.xenocom.com; HTTPS renews automatically.

Authorized social invitations are recorded separately from drafts in
`plans/outreach-evidence.json` and `plans/x-outreach-evidence.json`.
No external scientific reviewer, replication partner, grant or endorsement is
claimed. Funding figures are preliminary estimates requiring quotes and review.
