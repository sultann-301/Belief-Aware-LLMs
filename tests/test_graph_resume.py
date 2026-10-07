"""Recover pre-resume batch output without duplicating or resampling results."""

import csv
import fcntl
import json

import pytest

from evaluation.graphrag import run_batch


@pytest.fixture
def batch(tmp_path, monkeypatch):
    config = run_batch.load_config(run_batch.DEFAULT_CONFIG)
    config.update(models=["qwen3:4b"], domains=["loan_grounding"], runs_per_config=2, workers=1)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    output = tmp_path / "results.csv"
    calls = []

    class FakeLLM:
        def __init__(self, **kwargs):
            pass

        def generate_with_history_and_logprobs(self, messages):
            calls.append(messages)
            return "ANSWER: [test]", None

    monkeypatch.setattr(run_batch, "OllamaClient", FakeLLM)
    run_batch.main(["--config", str(config_path), "--csv-out", str(output)])
    with output.open(newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fields = reader.fieldnames
    calls.clear()
    return config_path, output, fields, rows, calls


def rewrite(output, fields, rows):
    with output.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("partial,torn", [(0, False), (3, False), (3, True)])
def test_resume_skips_complete_runs_and_recovers_interrupted_tail(batch, monkeypatch, partial, torn):
    path, output, fields, rows, calls = batch
    # Emulate the old runner, which saved a completed group of ten at a time.
    rewrite(output, fields, rows[:10 + partial])
    if torn:
        with output.open("a") as file:
            file.write('loan_grounding,2,"unfinished quoted result')
    before = output.read_bytes()

    def no_sampling(*args, **kwargs):
        raise AssertionError("Resume must use the saved manifest")

    monkeypatch.setattr(run_batch, "prepare_runs", no_sampling)
    # Dry-run checks must be safe even while an old runner is still active.
    run_batch.main(["--resume", "--dry-run", "--csv-out", str(output)])
    assert output.read_bytes() == before
    assert calls == []
    run_batch.main(["--resume", "--csv-out", str(output)])
    assert len(calls) == 10
    with output.open(newline="") as source:
        resumed = list(csv.DictReader(source))
    assert len(resumed) == 20
    assert resumed[:10] == rows[:10]
    assert len({(r["model"], r["domain"], r["run"], r["turn"]) for r in resumed}) == 20
    backups = list(output.parent.glob("*.before-resume-*.bak"))
    if partial or torn:
        assert len(backups) == 1
        assert backups[0].read_bytes() == before
    else:
        assert backups == []


def test_finished_resume_is_noop(batch):
    _, output, _, _, calls = batch
    before = output.read_bytes()
    run_batch.main(["--resume", "--csv-out", str(output)])
    assert calls == []
    assert output.read_bytes() == before


@pytest.mark.parametrize("corruption", ["duplicate", "prompt", "model", "config"])
def test_incompatible_or_corrupt_results_are_not_modified(batch, corruption):
    path, output, fields, rows, calls = batch
    if corruption == "duplicate":
        rows.append(rows[0])
    elif corruption == "prompt":
        rows[0]["prompt"] = "Different retrieval implementation"
    elif corruption == "model":
        rows[0]["model"] = "different-model"
    else:
        config = json.loads(path.read_text())
        config["temperature"] = 0.7
        path.write_text(json.dumps(config))
    rewrite(output, fields, rows)
    before = output.read_bytes()
    with pytest.raises(ValueError):
        run_batch.main(["--resume", "--config", str(path), "--csv-out", str(output)])
    assert calls == []
    assert output.read_bytes() == before


def test_resume_can_start_after_manifest_only_or_empty_csv(batch):
    _, output, _, _, calls = batch
    output.write_text("")
    run_batch.main(["--resume", "--csv-out", str(output)])
    assert len(calls) == 20
    with output.open(newline="") as source:
        assert len(list(csv.DictReader(source))) == 20


def test_second_writer_is_rejected(batch):
    _, output, _, _, calls = batch
    with output.with_suffix(".csv.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="Another batch"):
            run_batch.main(["--resume", "--csv-out", str(output)])
    assert calls == []
