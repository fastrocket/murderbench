# MurderBench

Current direction (October 4, 2026): independent evaluation of **agent safeguard
coverage**, operated by XP.COM, LLC dba Xenocom and led by Linh Ngo.
The proposed study asks whether calling an unchanged partial motion guard a
"safety approver" changes executed behavior. There are no model trials for this
candidate yet. Read `plans/guardrail-coverage-proposal.txt` for the closest work,
controls, rejection gates and remaining freeze requirements, and
`plans/business-2026-10-04.txt` for the operating plan. The model API lifetime cap
remains USD100 including outstanding reservations and credit-funded usage.

Verify the committed public site with `python deployment/verify_static.py`.
A full publication rebuild with `python build_site.py` also authenticates older
model receipts against the private ledger and renders their figures; it requires
that ledger and Matplotlib. CI verifies the committed release without bypassing
the authenticated publication gate. The optional explanatory
figure can be regenerated with `python -m benchmark.guardrail_design_figure`
(Pillow required); the committed SVG/PNG contains design information, not results.
Run offline checks with `python -m unittest discover -s tests`.
The guardrail development controls and native adapter audit are in
`plans/guardrail-development-controls.txt`. Run
`python -m benchmark.guardrail_coverage_controls`; the reports preserve every
scripted trace and native differential comparison. The public publisher audits
stored artifacts against current sources before copying them. The optional
scripted trace figure uses Matplotlib; it represents no model results.
An optional local Phoenix code-evaluator bridge is documented in
`plans/guardrail-phoenix-interface.txt`. Its standard-library metrics independently
replay a receipt against a separately bound case; missing or invalid receipts
remain unscorable for contact and completion, and infeasible tasks are excluded
from the feasible-completion metric. Install the optional pinned SDK in an
isolated environment, then run `python -m benchmark.guardrail_phoenix_demo`.
This is a scripted interoperability example, without a hosted dashboard,
customer implementation, model finding or partner endorsement.
Historical studies and their registered sources remain intact. The chronological
development notes below describe earlier stages and their then-current budgets.

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

A native development pilot has now completed twelve selected episodes on two
proprietary routes. Its four-call horizon is separate from the planned final
study. Read `reviews/necessity-native-development-report.txt` and the disclosed
schema amendment before interpreting the traces. The first interface's unknown
records and both source identities are preserved in `plans/freezes/necessity-native-v1/`
and `plans/freezes/necessity-native-v2/`. Neither is a held-out freeze.
`python -m benchmark.necessity_native_analysis` validates native receipt provenance
against the private ledger and independently folds the public outcome traces.
It makes no model calls. The single necessity ledger retains old reservations in
the original USD50 lifetime admission limit; remaining accounted budget at the
pilot export is USD12.1911319624, not an authorization for a larger collection.

New offline structural cases expose already-delivered stale evidence and a
shared verification queue across two obligations. Their eight-call procedure
controls and costs are documented in `plans/necessity-structural-scenarios.txt`.
Reproduce seventy scripted traces and the prepared-checkpoint exact comparator:
`python -m benchmark.necessity_structural_calibration --output reviews/necessity-structural-calibration.json`.
The queue reference policy is feasible, not proved optimal; no LLM mitigation
effect or held-out result follows from this offline calibration.

`python -m benchmark.necessity_queue_bounds --output reviews/necessity-queue-bounds.json`
computes an explicit interval around the queue optimum. Its lower witnesses have
extra information and are excluded as agent target policies. See
`plans/necessity-comparison-and-collection-gates.txt` for the bounds, separate
decision/completion evidence diagnostic, and remaining collection gates.
`python -m benchmark.necessity_route_plan` reads public endpoint metadata and
prices a reference matrix; it does not authorize or perform collection.

A preliminary safe proxy study of model proposals after verified constraints change.
Fixed synthetic histories do not establish actual agent commitment or intent.
No real action is executed. No general safety ranking or injury risk is claimed.

The current scoped design and exclusions are in `plans/final-study.txt`.
The broader future research roadmap is in `plans/protocol.txt`.
Prior-case overlap and unproven novelty are documented in `plans/overlap-audit.txt`.

Run offline checks: `python -m unittest discover -s tests`.
The public repository also runs these checks, freeze validation, and committed
static-resource verification in GitHub Actions without model credentials or
billable requests. A full site rebuild requires private authenticated receipts
and plotting dependencies: `python build_site.py` (sixteen public pages).

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

The current lifetime authorization is USD100, including unresolved reservations.
Older frozen manifests retain their original per-study limits.
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

# Public reuse

The owner-approved [guardrail release licence](LICENSING.md) covers 7 MIT
source/test files and 10 CC BY 4.0 report/figure files and public report copies.
Commercial reuse is permitted under those terms. Scope is defined by exact
files and fingerprints; this is not a repository-wide licence.
