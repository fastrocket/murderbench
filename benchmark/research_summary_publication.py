"""Publish a dated evidence overview from existing reports; no collection."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def publish(page, out):
    results = json.loads((ROOT / 'plans/results.json').read_text(encoding='utf-8'))
    groups = [(name, group) for model in results['models'] for name, group in model['groups'].items()]
    attempted = sum(model['attempted_calls'] for model in results['models'])
    valid = sum(model['status_counts'].get('valid', 0) for model in results['models'])
    branch = {
        state: {
            field: sum(group[field] for name, group in groups if name.endswith('/' + state))
            for field in ('valid', 'complete')
        }
        for state in ('stable', 'changed')
    }
    pilot = json.loads((ROOT / 'reviews/necessity-matched-pilot-audit.json').read_text(encoding='utf-8'))['counts']
    recovery = json.loads((ROOT / 'reviews/recovery-vault-audit.json').read_text(encoding='utf-8'))
    guard = json.loads((ROOT / 'reviews/guardrail-native-differential.json').read_text(encoding='utf-8'))
    phoenix = json.loads((ROOT / 'reviews/guardrail-phoenix-acceptance.json').read_text(encoding='utf-8'))
    pilot_attempted = pilot['completed'] + pilot['collection_stopped']

    page('research-summary.html', 'Research evidence and attribution', f'''
<section class="intro"><p class="eyebrow">EVIDENCE OVERVIEW / OCTOBER 15, 2026</p>
<h1>Can an agent obey a rule<br>and still lose the<br>safe outcome?</h1>
<p class="lead">A record of narrow model studies, reproduced software behavior and the questions that remain open. Research direction by Linh Ngo; implementation and analysis produced with AI coding agents.</p>
<p class="caption">This update consolidates existing records through October 8. It adds no new model trials or findings.</p></section>

<section class="reading"><h2>What we investigate</h2>
<p>An agent may respect an authorization boundary yet miss a safer useful option. A security operation may work as documented while disrupting recovery. A safeguard may enforce action bounds while leaving other hazards unchecked.</p>
<p>MurderBench asks which of these boundaries can support a useful evaluation, and which proposed experiments should be rejected. The work so far does not establish a novel alignment failure, general model safety or a validated production repair.</p>
<div class="notice"><strong>Current candidate: proposed, with no model results.</strong>
<p>Would calling an unchanged partial guard a “safety approver” change executed behavior? Both comparison arms disclose identical coverage facts. A separate repair would explicitly state uncovered hazards. Prior work, fresh confirmation cases and protocol freeze remain gates before querying models.</p>
<a class="text-link" href="/guardrail-coverage.html">Inspect the proposed comparison →</a></div></section>

<section class="reading"><h2>The completed proposal study</h2>
<p>The first study recorded {attempted:,} calls across eight hosted model routes, with {valid:,} valid outputs and {attempted - valid:,} technical unknowns. It paired unchanged and changed permission or safety conditions across fixed synthetic histories.</p>
<div class="table-wrap"><table><caption>Valid action proposals; no action was executed</caption>
<thead><tr><th scope="col">Verified state</th><th scope="col">Complete proposals</th><th scope="col">Valid outputs</th></tr></thead>
<tbody><tr><th scope="row">Permission becomes invalid</th><td>{branch['changed']['complete']:,}</td><td>{branch['changed']['valid']:,}</td></tr>
<tr><th scope="row">Permission remains valid</th><td>{branch['stable']['complete']:,}</td><td>{branch['stable']['valid']:,}</td></tr></tbody></table></div>
<p>All valid changed-state outputs paused or requested clarification in this export. That narrow result does not prove alignment. Scripted histories, repeated calls and compound contexts are dependent; ordinary instruction following and an easy diagnostic remain plausible explanations. Filters, unknown finish reasons and truncation were not scored as safe.</p>
<a class="text-link" href="/results.html">Full results and limitations →</a>
<a class="text-link" href="/artifacts/results.json">Counts, route identities and denominators ↓</a></section>

<section class="reading"><h2>Deadline pilots: planning failures and a negative comparison</h2>
<p>A twelve-episode native development pilot used in-memory tools on two hosted proprietary routes. One selected episode missed an available way to preserve a verification window; another used a protected allocation despite a safer alternative. Separately implemented event folds checked the reported outcomes.</p>
<p>These were selected synthetic realizations, with one run per case and route. They did not isolate a safety-instruction effect, estimate prevalence or establish novelty. Earlier interface failures remain disclosed.</p>
<p>The later matched pilot attempted {pilot_attempted} of {pilot['planned']} planned episodes: {pilot['completed']} completed, {pilot['collection_stopped']} stopped prefixes and {pilot['not_attempted']} unattempted episodes. Recorded omission was 0/60 completed need-positive episodes; authority breach was 0/123 completed episodes. Fully observed matched-arm comparisons had zero outcome discordance.</p>
<p>A perfect read-only trusted alternative made that comparison too easy to establish its intended contribution. The funding and novelty pitch was rejected. Missing cases do not support a population null effect.</p>
<a class="text-link" href="/necessity.html">Development observations →</a>
<a class="text-link" href="/artifacts/necessity-native-development-report.txt">Native pilot report ↓</a>
<a class="text-link" href="/matched-pilot.html">Matched pilot and rejection →</a>
<a class="text-link" href="/artifacts/necessity-matched-pilot-audit.json">Replay audit and missing cases ↓</a></section>

<section class="reading"><h2>Remediation and recovery: a mechanism, not a model finding</h2>
<p>Vault v1.20.4 was exercised on loopback with synthetic tokens, checkpoints and recovery jobs. Across two disclosed versions, {recovery['total_completed_reference_cases']} of {recovery['total_reference_attempts']} scripted reference attempts completed; {recovery['total_unscored_collection_stops']} stopped unscored.</p>
<p>In the dependent-worker v2 topology, revoking the token tree denied both old identities in 4/4 cases but recovery succeeded in 0/4. A handoff before revocation preserved recovery and eventual denial in 4/4. The credentials remained live during handoff; security during that interval was not measured.</p>
<p>No model was queried. The mechanism and repair overlapped known operational work, and no surprising model result or validated operator decision was established. The candidate stopped at the contribution gate. This limited audit does not prove that every narrower recovery-aware evaluation is duplicate.</p>
<a class="text-link" href="/remediation-recovery.html">Reproduction, amendment and rejection →</a>
<a class="text-link" href="/artifacts/recovery-vault-audit.json">Attempt and outcome audit ↓</a></section>

<section class="reading"><h2>What is implemented for the next question?</h2>
<p>The restricted motion-guard adapter matched a pinned Inspect Robots implementation in {guard['comparison_count']:,} one-step comparisons and {guard['trace_count']} scripted traces, with {guard['differential_mismatches']} differential and {guard['trace_mismatches']} trace mismatches. A separately implemented geometry verifier replays events, and a separate search labels safe-delivery feasibility.</p>
<p>The optional local Phoenix bridge matched {phoenix['native_metric_calls']} native evaluator calls over {phoenix['stored_control_event_logs_matched']} scripted traces. It is an interoperability example, with no hosted service, customer implementation or measured model effect.</p>
<p>These controls use symbolic geometry, dependent rotations and some duplicate observations. They do not validate real robot dynamics or injury risk. The wording experiment, information-changing repair comparison and fresh confirmation study remain planned.</p>
<a class="text-link" href="/artifacts/guardrail-development-controls.txt">Controls, supported subset and reproduction ↓</a>
<a class="text-link" href="/artifacts/guardrail-native-differential.json">Native comparisons and traces ↓</a>
<a class="text-link" href="https://github.com/fastrocket/murderbench/blob/ebaf34ac9bb9447f9f6c0cda5aa29f3e1444afd0/plans/guardrail-phoenix-interface.txt">Phoenix interface and limitations ↗</a></section>

<section class="reading"><h2>How the evidence is produced</h2>
<p>Across these studies, the evaluation designs distinguish proposals from executed simulator effects, feasible tasks from impossible situations, and valid behavior from technical failures. Correct and deliberately faulty controls test the scoring boundary. Frozen manifests, source identities, disclosed amendments and retained missing denominators make the experiments inspectable.</p>
<p>“Independent replay” means a separately implemented verifier. It does not mean independent human review. Public logs can be replayed; authenticating model receipts also requires the private raw ledger. API-returned model labels do not establish checkpoint equivalence. No physical actuators, real subjects or production credentials were used in these experiments.</p>
<a class="text-link" href="https://github.com/fastrocket/murderbench">Source, tests, registrations and reports ↗</a>
<a class="text-link" href="/guardrail-coverage.html#public-reuse">Exact public-reuse scope →</a></section>

<section class="reading"><h2>Research direction and implementation</h2>
<p>Linh Ngo initiated MurderBench and leads it through XP.COM, LLC dba Xenocom. The human headcount is one. He set the research goals, model priorities, sandbox boundaries and budget; challenged reassuring interpretations; and required novelty audits, useful controls and publication of negative findings and rejected candidates.</p>
<p>AI coding agents drafted literature audits and designs, wrote the implementation and analysis code, ran authorized experiments, and produced the reports, figures and website. Other AI agents supplied preparation critiques. Linh's contribution is the research direction, constraints and critique described above; the implementation and analysis artifacts were generated with coding agents. Independent human annotation remains pending.</p>
<p>The work remains preliminary. External scientific review, replication, a novel contribution and a concrete production decision changed by the evaluation are unestablished. No award or lab endorsement was verified in the last outreach check on October 8; this publication is not a new inbox check.</p>
<a class="text-link" href="/about.html">About Linh Ngo and the initiative →</a>
<a class="text-link" href="/contact.html">Challenge a method or propose a bounded collaboration →</a></section>
''', 'A dated MurderBench evidence overview: actual results, negative findings, implemented controls, planned comparisons and transparent research attribution.')
