"""Execute reporting notebooks in dependency order; no model evaluations."""
from pathlib import Path
import hashlib
import json

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = (
    "graphrag_single_agent_comparison.ipynb",
    "final_single_agent_analysis.ipynb",
    "eval_results_analysis.ipynb",
    "dual_agent_analysis.ipynb",
    "final_dual_agent_analysis.ipynb",
)


def export_manifest():
    output = ROOT / "output/non_hard"
    chart_data = {
        "accuracy_delta_heatmaps": ["accuracy_delta_with_store.csv", "accuracy_delta_no_store.csv"],
        "graphrag_reliability": ["reliability_bins.csv"],
    }
    charts = []
    for png in sorted(output.rglob("*.png")):
        data = [png.with_name(name) for name in chart_data.get(png.stem, [png.stem + ".csv"])]
        files = [png, png.with_suffix(".svg"), *data]
        assert all(path.exists() for path in files), str(png)
        charts.append({"chart": str(png.relative_to(output)), "files": [
            {"path": str(path.relative_to(output)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in files]})
    (output / "chart_manifest.json").write_text(json.dumps(charts, indent=2) + "\n")
    (output / "execution.json").write_text(json.dumps({"status": "passed", "notebooks": [
        {"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
        for name in NOTEBOOKS], "charts": len(charts), "model_evaluations_run": 0}, indent=2) + "\n")


if __name__ == "__main__":
    for name in NOTEBOOKS:
        path = ROOT / name
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(notebook, timeout=180, kernel_name="python3",
                       resources={"metadata": {"path": str(ROOT)}}).execute()
        nbformat.write(notebook, path)
        print("PASS:", name, flush=True)
    export_manifest()
