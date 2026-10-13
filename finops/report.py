"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend:** ${optimized_usd:,.0f}  ",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Cleanest region: {sustainability.get('best_region', 'n/a')}",
        ]
    lines += ["", "_Figures are June-2026 as-of snapshots; re-baseline before acting._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str, baseline: float | None = None) -> str:
    """Write a simple savings bar chart PNG. Returns the path. No-op if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    if baseline is None:
        bars = ax.bar(names, vals, color="#2e548a")
    else:
        remaining = baseline
        bottoms = [0]
        heights = [baseline]
        for value in vals:
            remaining -= value
            bottoms.append(remaining)
            heights.append(value)
        bottoms.append(0)
        heights.append(remaining)
        names = ["Baseline"] + names + ["Optimized"]
        bars = ax.bar(names, heights, bottom=bottoms,
                      color=["#2e548a"] + ["#38956b"] * len(vals) + ["#2e548a"])
        for bar, value in zip(bars, heights):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_y() + bar.get_height() + 120,
                    f"${value:,.0f}", ha="center", fontsize=9)
        ax.set_ylim(0, baseline * 1.15)
    ax.set_ylabel("USD / modeled 30-day month")
    ax.set_title("Lab portfolio scenario: baseline, four savings levers, optimized")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
