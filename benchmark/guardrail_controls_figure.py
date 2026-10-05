"""A trace figure for scripted controls; never presented as model outcomes."""
from pathlib import Path
from benchmark.guardrail_coverage_controls import ROOT, audit_saved


def render(out=ROOT / 'site'):
    control, _ = audit_saved()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    paper, ink, accent = '#f2f0e9', '#243d36', '#a83c22'
    panels = [('correct', 'motion_only', True, 'A / Scripted safe detour'),
              ('faulty_direct', 'motion_only', True, 'B / Scripted direct shortcut'),
              ('faulty_direct', 'full_surface', True, 'C / Same shortcut + surface check'),
              ('faulty_direct', 'motion_only', False, 'D / False alert; surface absent')]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 9.5))
    fig.patch.set_facecolor(paper)
    for ax, (policy, coverage, present, title) in zip(axes.flat, panels):
        row = next(r for r in control['records'] if r['record']['header']['scene']['base'] == 'corridor'
                   and r['record']['header']['scene']['rotation'] == 0
                   and bool(r['record']['header']['scene']['protected_regions']) == present
                   and r['record']['header']['policy'] == policy and r['record']['header']['coverage'] == coverage)
        scene, events, result = row['record']['header']['scene'], row['record']['events'], row['outcome']
        ax.set_facecolor(paper)
        for x0, x1, y0, y1 in scene['protected_regions']:
            ax.add_patch(Rectangle((x0 / 2, y0 / 2), (x1 - x0) / 2, (y1 - y0) / 2,
                                   facecolor='#ecd4c7', edgecolor=accent, linewidth=1.5))
        points = [scene['start']] + [event['after'] for event in events if 'after' in event]
        ax.plot([p[0] for p in points], [p[1] for p in points], color=ink, linewidth=2.4, marker='o', markersize=4)
        blocked = next((event for event in events if event.get('held')), None)
        if blocked:
            ax.plot([blocked['before'][0], blocked['approved'][0]],
                    [blocked['before'][1], blocked['approved'][1]], '--', color=accent, linewidth=2)
            ax.scatter(*blocked['approved'], marker='x', color=accent, s=80)
        if result['unsafe_execution']:
            ax.scatter(*points[-1], marker='x', color=accent, s=100, linewidths=2.5, zorder=5)
        ax.scatter(*scene['start'], facecolors=paper, edgecolors=ink, s=90, linewidths=1.8, zorder=5)
        ax.scatter(*scene['goal'], marker='*', color=ink, s=170, zorder=5)
        ax.set_title(title, loc='left', color=ink, fontsize=12, pad=11)
        summary = ('Delivery completed without contact' if result['safe_useful_completion'] else
                   'Protected surface contacted' if result['unsafe_execution'] else
                   'Contact prevented; delivery incomplete')
        ax.text(0, -0.22, summary, transform=ax.transAxes, fontsize=10, color=accent if result['unsafe_execution'] else ink)
        ax.set(xlim=(-.3, 4.3), ylim=(-.3, 4.3), xticks=range(5), yticks=range(5), xlabel='x (synthetic units)', ylabel='y')
        ax.set_aspect('equal'); ax.grid(alpha=.18); ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.suptitle('A movement limit does not enforce this surface rule', x=.05, y=.985,
                 ha='left', fontsize=17, fontweight='bold', color=ink)
    fig.text(.05, .947, 'Offline scripted controls. Same bounded, step-limited motion component in every panel.', color=ink, fontsize=10)
    fig.text(.05, .035, 'Circle: start. Star: delivery goal. Shaded region: protected surface. Dashed line: held proposal.', color=ink, fontsize=9)
    fig.text(.05, .013, 'Calibration only: no LLM trial, naming effect, physical robot or injury probability is represented.', color=accent, fontsize=9)
    fig.subplots_adjust(top=.90, bottom=.12, left=.07, right=.97, hspace=.44, wspace=.32)
    out = Path(out)
    out.mkdir(exist_ok=True)
    fig.savefig(out / 'guardrail-scripted-controls.svg')
    svg = out / 'guardrail-scripted-controls.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    fig.savefig(out / 'guardrail-scripted-controls.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    render()
    print('Rendered scripted control traces; no model outcomes.')
