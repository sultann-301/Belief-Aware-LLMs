"""Run after notebook execution: python3 -m tests.test_non_hard_reporting."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.analysis_reporting import DOMAINS, MODELS, OUTPUT, benchmark_frame, verify_sources
from scripts.normalize_eval_csvs import _baseline_from_eval_prompt


def test_reporting():
    metadata = verify_sources()
    assert len(DOMAINS) == 16 and not any(d.endswith("_hard") for d in DOMAINS)
    sample = pd.DataFrame({"Domain": ["loan_absurd", "loan_hard", "loan_absurd_temporal_noise"]})
    assert benchmark_frame(sample).Domain.tolist() == ["loan_absurd"]
    cells = pd.read_csv(OUTPUT / "accuracy_cells.csv", index_col=0)
    assert set(cells.Model) == set(MODELS)
    assert not cells.duplicated(["Model", "Domain", "System"]).any()
    assert cells.groupby(["Model", "System"]).size().eq(16).all()
    assert cells.groupby(["Model", "System"]).Domain.apply(lambda s: set(s) == set(DOMAINS)).all()
    variants = pd.read_csv(OUTPUT / "accuracy_prompt_cells.csv").set_index(["Model", "Domain", "Temp", "Runs"])
    assert len(variants) == 80 and variants.notna().all().all()
    actual = cells.pivot(index=["Model", "Domain", "Temp", "Runs"], columns="System", values="Accuracy")
    for label, prompts in [("With Store (mean v15/v16)", ["With Store (v15)", "With Store (v16)"]),
                           ("No Store (mean v1/v2)", ["No Store (v1)", "No Store (v2)"])]:
        np.testing.assert_allclose(actual[label], variants[prompts].mean(axis=1).reindex(actual.index))
    assert metadata["prompt_mapping"] == {v: _baseline_from_eval_prompt(v) for v in ["v15", "v16"]}
    for dimension in ["Model", "Scenario", "Family"]:
        summary = pd.read_csv(OUTPUT / ("accuracy_by_" + dimension.lower() + ".csv")).set_index([dimension, "System"])
        direct = cells.groupby([dimension, "System"]).Accuracy.agg(mean="mean", sd="std", n="count")
        np.testing.assert_allclose(summary.loc[direct.index], direct, rtol=1e-12)
    plotted = pd.read_csv(OUTPUT / "charts/aggregated_accuracy_by_model.csv", index_col=0)
    expected = cells.groupby(["Model", "System"]).Accuracy.mean().unstack()
    np.testing.assert_allclose(plotted, expected.reindex(index=plotted.index, columns=plotted.columns))
    metric_cells = pd.read_csv(OUTPUT / "metric_cells.csv", index_col=0)
    assert not metric_cells.Domain.str.endswith("_hard").any()
    assert not metric_cells.duplicated(["Model", "Domain", "Temp", "Runs", "Metric", "System"]).any()
    coverage = pd.read_csv(OUTPUT / "metric_coverage.csv", index_col=0)
    counts = metric_cells.groupby(["Model", "Metric", "System"]).Value.count()
    assert coverage.set_index(["Model", "Metric", "System"]).available.eq(counts).all()
    assert pd.read_csv(OUTPUT / "missing_accuracy_combinations.csv").empty
    # A mean over an empty correct/incorrect response group is undefined, not zero.
    word_cells = metric_cells[metric_cells.Metric.str.startswith("TPCA_Words_")].merge(
        metric_cells[metric_cells.Metric.eq("Average_Accuracy")][["Model", "Domain", "System", "Value"]],
        on=["Model", "Domain", "System"], suffixes=("_words", "_accuracy"), validate="many_to_one")
    undefined = ((word_cells.Metric.eq("TPCA_Words_Correct") & word_cells.Value_accuracy.eq(0)) |
                 (word_cells.Metric.eq("TPCA_Words_Wrong") & word_cells.Value_accuracy.eq(1)))
    assert word_cells.loc[undefined, "Value_words"].isna().all()
    afr = metric_cells[metric_cells.Metric.eq("AFR_Answer_Flip_Rate")].merge(
        metric_cells[metric_cells.Metric.eq("EFR_Extraction_Failure_Rate")][["Model", "Domain", "System", "Value"]],
        on=["Model", "Domain", "System"], suffixes=("_afr", "_efr"), validate="one_to_one")
    assert afr.loc[afr.Value_efr.eq(1), "Value_afr"].isna().all()
    for chart in json.loads((OUTPUT / "chart_manifest.json").read_text()):
        for artifact in chart["files"]:
            assert hashlib.sha256((OUTPUT / artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
    # Backups and all input CSVs must be byte-for-byte unchanged.
    backup = Path("backups/before_non_hard_standardization_2026-10-07")
    for name, digest in json.loads((backup / "sha256.json").read_text()).items():
        path = backup / name if name.endswith(".ipynb") else Path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, str(path)
    # Every refreshed notebook must have executed all code cells without stale errors.
    for path in Path(".").glob("*.ipynb"):
        notebook = json.loads(path.read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                assert cell["execution_count"] is not None, str(path)
                assert not any(out["output_type"] == "error" for out in cell["outputs"]), str(path)
    print("PASS: exclusions, expected grid, uniqueness, prompt mapping/weights, recomputed means/SDs, "
          "chart/export agreement, missingness counts, unchanged sources/backups and notebook execution.")


if __name__ == "__main__":
    test_reporting()
