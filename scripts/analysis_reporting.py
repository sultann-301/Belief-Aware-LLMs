"""Shared reporting policy and checked chart exports; never writes source data."""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FAMILIES = ("loan", "alien_clinic", "crime_scene", "thorncrester")
SCENARIOS = ("belief_maintenance", "absurd", "absurd_temporal", "grounding")
DOMAINS = tuple(f"{family}_{scenario}" for family in FAMILIES for scenario in SCENARIOS)
QWEN_LABEL = "Qwen3:4b, no thinking"
MODEL_ALIASES = {"qwen3:4b": QWEN_LABEL, "hoangquan456/qwen3-nothink:4b": QWEN_LABEL}
MODELS = ("gemma3:1b", "gemma4:e2b", "llama3.2:1b", "ministral-3:3b", QWEN_LABEL)
OUTPUT = Path("output/non_hard")
COVERAGE_LABEL = "Hard excluded · 4 domains × 4 scenario types"


def benchmark_frame(frame, column="Domain"):
    identifiers = frame[column]
    assert identifiers.notna().all(), f"Missing scenario identifiers in {column}"
    return frame.loc[~identifiers.str.endswith("_hard") & identifiers.isin(DOMAINS)].copy()


def scenario_name(domain):
    return next(s for s in SCENARIOS if domain.endswith("_" + s))


def export_table(table, name, folder=OUTPUT):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    table.to_csv(path, float_format="%.17g")
    return path


def save_figure(fig, name, folder=OUTPUT / "charts", coverage=COVERAGE_LABEL):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    # Place the scope note below all tick labels, including labels outside the canvas.
    fig.canvas.draw()
    bounds = fig.get_tightbbox(fig.canvas.get_renderer())
    fig.text(bounds.x0 / fig.get_figwidth(), bounds.y0 / fig.get_figheight() - .045,
             coverage, fontsize=8, color="#555555")
    for suffix in ("png", "svg"):
        fig.savefig(folder / f"{name}.{suffix}", dpi=180, bbox_inches="tight", pad_inches=.2)


def bar_chart(table, title, ylabel, ylim=None, *, folder=OUTPUT / "charts",
              colors=("#7c3aed", "#0284c7", "#ea580c", "#059669", "#d97706"), name=None,
              coverage=COVERAGE_LABEL):
    name = name or re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    path = export_table(table, name, folder)
    # Verify the exported values against both the table and the rendered bar heights.
    plotted = pd.read_csv(path, index_col=list(range(table.index.nlevels)))
    np.testing.assert_allclose(plotted.to_numpy(float), table.to_numpy(float), equal_nan=True)
    ax = table.plot.bar(figsize=(max(8, len(table) * 1.6), 4.5), color=list(colors), width=.8)
    ax.set(title=title, ylabel=ylabel + (" ↑" if ylabel == "Accuracy" else ""), xlabel="")
    if ylim is not None:
        ax.set_ylim(*ylim)
    tick_labels = [str(value).replace("Qwen3:4b, no thinking", "Qwen3:4b\n(no thinking)")
                   .replace(" | ", "\n→ ").replace("hoangquan456/", "hoangquan456/\n")
                   for value in table.index]
    ax.set_xticks(ax.get_xticks(), tick_labels, rotation=20, ha="right")
    ax.grid(axis="y", alpha=.2)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    assert len(ax.containers) == len(table.columns)
    for container, column in zip(ax.containers, table.columns):
        # Matplotlib renders NaN as a zero-height bar; omit it instead.
        for patch, value in zip(container.patches, table[column]):
            if pd.isna(value):
                patch.set_visible(False)
            else:
                assert np.isclose(patch.get_height(), value)
    plt.tight_layout(rect=(0, .05, 1, 1))
    save_figure(ax.figure, name, folder, coverage=coverage)
    plt.show()
    plt.close(ax.figure)


def verify_sources():
    metadata = json.loads((OUTPUT / "definitions.json").read_text())
    for source in metadata["sources"]:
        assert hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() == source["sha256"], (
            "Source changed; execute graphrag_single_agent_comparison.ipynb first: " + source["file"])
    return metadata
