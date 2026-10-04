"""Publish the rejected contribution and all offline mechanism attempts."""

from __future__ import annotations

import html
import json
from pathlib import Path

from benchmark.recovery_vault_audit import audit_workspace

ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS = (
    "plans/recovery-research-audit.txt", "plans/recovery-contribution-decision.txt",
    "plans/recovery-evaluation-design.txt", "plans/recovery-source-audit.json",
    "plans/recovery-vault-registration.json", "plans/recovery-vault-registration-v2.json",
    "plans/recovery-vault-release.json", "reviews/recovery-vault-reproduction.json",
    "reviews/recovery-vault-reproduction-v2.json", "reviews/recovery-vault-verification.json",
    "reviews/recovery-vault-verification-v2.json", "reviews/recovery-vault-audit.json",
)


def publish(page, output):
    audited = audit_workspace()
    saved = json.loads((ROOT / "reviews/recovery-vault-audit.json").read_bytes())
    if audited != saved:
        raise ValueError("The published offline audit does not match the receipts")
    if "CURRENT PITCH REJECTED" not in (ROOT / "plans/recovery-contribution-decision.txt").read_text():
        raise ValueError("The contribution decision needs review before publication")
    for source in ARTIFACTS:
        path = ROOT / source
        (output / "artifacts" / path.name).write_bytes(path.read_bytes())
    labels = {
        "leave_active": "Leave the old identities active",
        "revoke_tree": "Revoke the parent and descendants",
        "revoke_parent_only": "Revoke the parent, preserve descendants",
        "handoff_then_revoke": "Trusted handoff, then revoke the old tree",
    }
    rows = []
    for policy, label in labels.items():
        result = audited["v2_summary"]["dependent/" + policy]
        rows.append(f'<tr><th scope="row">{html.escape(label)}</th>'
                    f'<td>{result["completed"]}/{result["cases"]}</td>'
                    f'<td>{result["old_tree_denied"]}/{result["cases"]}</td></tr>')
    body = '''<section class="intro"><p class="eyebrow">MECHANISM AUDIT / 4 OCTOBER 2026</p>
<h1>Can a security fix<br>block recovery?</h1>
<p class="lead">Yes, in a documented executor configuration. We reproduced the dependency in Vault. The current study does not establish a novel AI result.</p></section>
<section class="reading"><h2>Contribution decision: stop before model collection</h2>
<p>The mechanism and migration strategies have established precedents. This work supplies a conformance example. It does not meet our novelty and sponsorship bar.</p>
<p>No new model calls, API reservations, or model spending. No new social promotion or sponsorship outreach for this candidate.</p>
<a class="text-link" href="/artifacts/recovery-contribution-decision.txt">Read the complete rejection and skeptical assessment ↗</a></section>
<section><h2>What actually ran</h2>
<p>A real Vault 1.20.4 process ran on loopback with synthetic identities and data. A waiting worker held its checkpoint in storage scoped to its token. Four scripted procedures changed the token hierarchy before the worker resumed.</p>
<p>The amended collection completed 48 reference cases. The first version completed ten cases and retained one unscored stop, leaving 37 of its planned cases unattempted. Across both versions: 59 attempts, 58 completed, one unscored stop. All attempts remain available.</p>
<p>These are deterministic reference procedures. Repetitions check software consistency; they are not model trials or independent incident samples.</p>
<div class="table-wrap"><table><caption>Dependent worker: two declared incident labels × two repetitions per procedure</caption>
<thead><tr><th scope="col">Reference procedure</th><th scope="col">Recovery completed</th><th scope="col">Both old test identities denied at endpoint</th></tr></thead><tbody>'''
    body += "".join(rows)
    body += '''</tbody></table></div>
<p>Full revocation blocked the dependent worker. Preserving descendants kept recovery possible, but also preserved the test child's access. A trusted handoff preserved recovery and revoked both old test identities at the endpoint.</p>
<p>With an independent worker identity, full revocation allowed recovery in all four cases. When setup had already removed the sole checkpoint, none of the four procedures recovered it.</p>
<p>Vault documents the parent-child cascade and deletion of per-token storage. Our reproduction confirms those effects; it does not discover them.</p>
<a class="text-link" href="https://developer.hashicorp.com/vault/docs/concepts/tokens">Token hierarchy documentation ↗</a>
<a class="text-link" href="https://developer.hashicorp.com/vault/docs/secrets/cubbyhole">Per-token storage documentation ↗</a></section>
<section><h2>The repair has a security cost</h2>
<p>The handoff copies the checkpoint before revocation. Old credentials remain live during that interval. We measure intervention duration and probe access after settlement; we do not measure continuous exposure or attacker activity during the handoff.</p>
<p>The tested requirement is denial of both old test identities at the endpoint. Immediate containment is a stricter requirement and could make this handoff inadmissible. The repair is not universally safe.</p>
<p>The single-copy checkpoint, trusted handoff authority, and absence of another recovery source are explicit fixture assumptions. No production operator has validated them here.</p></section>
<section><h2>What this cannot tell us</h2>
<p>The compromise and false-alert labels change the declared requirement, not the executor state. This does not test alert recognition, prompt injection, safety-induced choices, intent, alignment, or human harm.</p>
<p>No frontier model chose these procedures. No operational decision changed through an operator-reviewed trace. A synthetic checkpoint loss alone is insufficient evidence for deployment risk or funding claims.</p></section>
<section><h2>The closest work already covers much of the idea</h2>
<p>AIOpsLab includes executed authentication-revocation tasks. GuardedAct evaluates remediation collateral damage and recoverability. ColdStart describes recovery quality and security checks. Existing rotation guidance covers handoffs during active jobs.</p>
<p>Selected public implementations do not settle every sequencing question. Protected task pools and unavailable original releases prevent a complete comparison. Those access gaps cannot establish originality.</p>
<a class="text-link" href="/artifacts/recovery-research-audit.txt">Primary-source audit, exact distinctions, and access limits ↗</a>
<a class="text-link" href="https://github.com/microsoft/AIOpsLab/blob/ccf08d0d1d5fa5b30f120e2e8549662d44411b35/aiopslab/orchestrator/problems/revoke_auth/revoke_auth.py">Pinned AIOpsLab task ↗</a>
<a class="text-link" href="https://arxiv.org/pdf/2609.11264">GuardedAct paper ↗</a>
<a class="text-link" href="https://www.deaimer.com/benchmarks/coldstart">ColdStart methodology ↗</a>
<a class="text-link" href="https://app.armalo.ai/learn/credential-rotation-active-agent-sessions">Active-job rotation guidance ↗</a></section>
<section><h2>One collector correction, fully retained</h2>
<p>The first collector expected successful revocation even when the token had already been removed. Vault's parent-only endpoint instead returns a documented HTTP 400. The run stopped and its prefix remains unscored.</p>
<p>The separate v2 collector accepts only that exact response after an observed setup revocation, then settles the worker and probes access. The original sources, registration, and results remain unchanged. The matrix is identical.</p></section>
<section><h2>Reproduce the audit</h2>
<p>The receipt verifier independently folds issued identities, revocations, checkpoint reads and writes, and security probes. It shares the collector's capture; independent capture and external peer review are not claimed.</p>
<p>The source audit records 159 hashed text files from selected pinned repositories. Its inspection scope is explicit. Public records contain identity aliases and checkpoint digests.</p>
<div class="rows">'''
    for source in ARTIFACTS:
        filename = Path(source).name
        body += f'<article><a href="/artifacts/{html.escape(filename)}">{html.escape(filename)}</a></article>'
    body += '''</div><p><a class="text-link" href="https://github.com/fastrocket/murderbench">Collector, verifier, audit, and tampering tests ↗</a></p></section>
<section><h2>What could justify reopening the question</h2>
<p>A permissioned operator trace could establish a dependency missed by an existing control. It would need actual recovery alternatives, containment limits, and a tested repair that changes that operator's decision.</p>
<p>That evidence is a prerequisite. No further model collection or sponsorship pitch is activated by this report.</p>
<a class="text-link" href="/matched-pilot.html">Previous matched pilot ↗</a></section>'''
    page("remediation-recovery.html", "Security remediation and recovery: contribution audit", body,
         "A real Vault mechanism reproduction with all retained attempts, established precedents, explicit limits, and a rejected contribution pitch. No new model results.")
    note = ('<section class="reading"><p class="eyebrow">LATEST CONTRIBUTION AUDIT / 4 OCTOBER 2026</p>'
            '<p>A security fix can block a dependent recovery worker. We reproduced the documented Vault mechanism and rejected the current novelty pitch before model spending.</p>'
            '<a href="/remediation-recovery.html">Read the mechanism audit and retained attempts ↗</a></section>')
    for name in ("research.html", "matched-pilot.html"):
        target = output / name
        text = target.read_text(encoding="utf-8")
        target.write_text(text.replace('<main id="main" tabindex="-1">',
                                      '<main id="main" tabindex="-1">' + note, 1), encoding="utf-8")
