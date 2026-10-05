"""Verify a committed public release without private receipts or model access."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'site'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value and value.startswith('/'):
                self.paths.add(value.split('#')[0].split('?')[0])


def main():
    parser = Links()
    pages = list(ROOT.glob('*.html'))
    if not pages:
        raise ValueError('No committed public pages')
    for page in pages:
        parser.feed(page.read_text(encoding='utf-8'))
    missing = []
    for path in sorted(parser.paths):
        local = ROOT / ('index.html' if path == '/' else path.lstrip('/'))
        if not local.resolve().is_relative_to(ROOT.resolve()) or not local.is_file():
            missing.append(path)
    if missing:
        raise ValueError(f'Missing or out-of-tree static links: {missing}')
    print(f'Verified {len(pages)} committed pages and {len(parser.paths)} local resource paths; no private ledger or model calls.')


if __name__ == '__main__':
    main()
