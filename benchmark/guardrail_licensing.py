"""Publish the bounded owner-approved licence without rebuilding prior studies."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- guardrail-public-reuse:start -->'
END = '<!-- guardrail-public-reuse:end -->'


def publish(out):
    """Verify the exact release and publish its notices on the study page."""
    out = Path(out)
    manifest = json.loads((ROOT / 'LICENSES/guardrail-release.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        raw = (ROOT / entry['path']).read_bytes()
        normalized = raw.replace(b'\r\n', b'\n') if entry['normalization'] == 'CRLF-to-LF' else raw
        if hashlib.sha256(normalized).hexdigest() != entry['sha256']:
            raise ValueError(f"Licensed file changed: {entry['path']}; review the release scope before publishing")
    if len(manifest['files']) != 17:
        raise ValueError('Unexpected release scope')
    artifacts = out / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    for source, target in (
        ('guardrail-release.json', 'guardrail-release-license.json'),
        ('MIT.txt', 'guardrail-code-MIT.txt'),
        ('guardrail-notice.txt', 'guardrail-licensing.txt'),
    ):
        (artifacts / target).write_bytes((ROOT / 'LICENSES' / source).read_bytes())
    section = START + '''
<section class="reading" id="public-reuse"><h2>Reproduce and reuse</h2>
<p>The seven source and test files listed in the release manifest are available under MIT.
Ten original report, figure and public report-copy files are available under CC BY 4.0.
Both allow commercial reuse under their terms. This grant covers the listed original
contributions; upstream software and other repository material retain their own permissions.</p>
<p>For CC BY material, credit Linh Ngo / MurderBench, XP.COM, LLC dba Xenocom,
link this study and indicate changes. Preserve the MIT notice when copying code.</p>
<a class="text-link" href="/artifacts/guardrail-release-license.json">Exact files and fingerprints ↓</a>
<a class="text-link" href="/artifacts/guardrail-licensing.txt">Scope and attribution ↓</a>
<a class="text-link" href="/artifacts/guardrail-code-MIT.txt">MIT terms ↓</a>
<a class="text-link" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0 terms ↗</a>
<p class="caption">Owner-approved October 6, 2026. Licensing does not establish novelty or model performance.
This proposed study has no model trials yet.</p></section>
''' + END
    page = out / 'guardrail-coverage.html'
    text = page.read_text(encoding='utf-8')
    if START in text:
        text, count = re.subn(re.escape(START) + r'.*?' + re.escape(END), lambda _: section, text, flags=re.S)
        if count != 1:
            raise ValueError('Expected one public reuse section')
    else:
        if text.count('</main>') != 1:
            raise ValueError('Expected one study main element')
        text = text.replace('</main>', section + '</main>')
    page.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    publish(ROOT / 'site')
    print('Published verified, bounded guardrail licence and study-page notice.')
