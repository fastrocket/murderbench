"""Render an explanatory study-design diagram. It contains no outcome data."""
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PAPER, INK, MUTED, ACCENT, LINE = '#f2f0e9', '#243d36', '#52635b', '#a83c22', '#c4cbc1'


def render(out=ROOT / 'site'):
    out.mkdir(exist_ok=True)
    image = Image.new('RGB', (1200, 520), PAPER)
    draw = ImageDraw.Draw(image)
    elements = []

    def font(size, bold=False):
        candidates = [Path('C:/Windows/Fonts') / ('arialbd.ttf' if bold else 'arial.ttf'),
                      Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size)
        return ImageFont.load_default(size=size)

    def text(x, y, value, size=21, color=INK, bold=False):
        draw.text((x, y), value, fill=color, font=font(size, bold), anchor='lt')
        elements.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" fill="{color}" font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>')

    def rect(x, y, w, h, fill=PAPER, stroke=LINE):
        draw.rectangle((x, y, x + w, y + h), fill=fill, outline=stroke, width=2)
        elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def line(x1, y1, x2, y2, color=LINE):
        draw.line((x1, y1, x2, y2), fill=color, width=2)
        elements.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="2" fill="none"/>')

    text(36, 25, 'MURDERBENCH / PROPOSED EXPERIMENT', 14, MUTED, True)
    text(36, 57, 'Same guard. Different assurance.', 37)
    text(36, 110, 'Fixed task, observations, tools, motion limits and model settings', 20, MUTED)
    rect(36, 156, 548, 169, '#e7e9df', INK)
    text(60, 176, 'A / NEUTRAL DESCRIPTION', 14, MUTED, True)
    text(60, 208, '“Motion validator”', 29)
    text(60, 259, 'Same coverage: action bounds + step limits', 20, MUTED)
    rect(616, 156, 548, 169, '#e7e9df', INK)
    text(640, 176, 'B / SAFETY DESCRIPTION', 14, ACCENT, True)
    text(640, 208, '“Safety approver”', 29)
    text(640, 259, 'Same coverage: action bounds + step limits', 20, MUTED)
    line(310, 326, 310, 352, INK)
    line(890, 326, 890, 352, INK)
    line(310, 352, 890, 352, INK)
    line(600, 352, 600, 372, INK)
    text(220, 383, 'Replay unsafe effects + useful task completion', 27, INK, True)
    text(36, 442, 'Separate repair: explicit uncovered hazards + assigned responsibility', 20, MUTED)
    text(36, 481, 'Study design only. No model trials or measured effect yet.', 16, ACCENT)
    image.save(out / 'guardrail-coverage-design.png')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" role="img" aria-labelledby="title desc"><title id="title">Same guard. Different assurance.</title><desc id="desc">Proposed experiment, no results: compare neutral and safety descriptions with identical coverage facts, replay effects and useful completion, then test a separate repair.</desc><rect width="1200" height="520" fill="'+PAPER+'"/><g font-family="Arial,Helvetica,sans-serif">'+''.join(elements)+'</g></svg>'
    (out / 'guardrail-coverage-design.svg').write_text(svg, encoding='utf-8')


if __name__ == '__main__':
    render()
    print('Rendered proposal diagram; no outcome data.')
