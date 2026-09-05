import pytest

from evaluation.run_batch import ConfigError, load_config, validate_config


def test_thesis_batch_configs_are_valid():
    validate_config(load_config("evaluation/configs/thesis_dual_agent_batch.json"))
    validate_config(load_config("evaluation/configs/thesis_standard_batch.json"))


def test_invalid_batch_config_reports_actionable_errors():
    config = load_config(None)
    config["domains"] = ["missing_domain"]
    config["runs_per_config"] = 0
    config["ollama"] = {"bad_key": 1}

    with pytest.raises(ConfigError) as exc_info:
        validate_config(config)

    message = str(exc_info.value)
    assert "'runs_per_config' must be a positive integer" in message
    assert "'ollama' contains unknown key(s): bad_key" in message
    assert "'domains' contains unknown domain(s): missing_domain" in message


def test_sequential_batch_config_requires_phase1_domains():
    config = load_config(None)
    config["mode"] = "sequential"

    with pytest.raises(ConfigError, match="'phase1_domains' must contain at least one value"):
        validate_config(config)
