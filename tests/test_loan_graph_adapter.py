"""Tests for the first, read-only loan GraphRAG adapter."""

from __future__ import annotations

import pytest

from evaluation.graphrag.loan_adapter import build_loan_graph


def test_adapter_reads_all_existing_loan_rules_and_facts() -> None:
    graph = build_loan_graph()

    assert graph.domain == "loan"
    assert len(graph.rules) == 10
    assert len(graph.facts) == 13
    assert {rule.output for rule in graph.rules} == {
        "loan.adjusted_income",
        "loan.credit_score_effective",
        "loan.high_risk_flag",
        "loan.applicant_prequalified",
        "loan.rate_tier",
        "loan.max_amount",
        "loan.application_status",
        "loan.requires_insurance",
        "loan.review_queue",
        "loan.base_interest_rate",
    }


def test_application_status_slice_contains_only_its_upstream_graph() -> None:
    graph = build_loan_graph()

    graph_slice = graph.subgraph_for(["loan.application_status"])

    assert [rule.output for rule in graph_slice.rules] == [
        "loan.adjusted_income",
        "loan.credit_score_effective",
        "loan.applicant_prequalified",
        "loan.max_amount",
        "loan.application_status",
    ]
    assert "loan.high_risk_flag" not in {
        rule.output for rule in graph_slice.rules
    }
    assert set(graph_slice.facts) == {
        "applicant.income",
        "applicant.dependents",
        "applicant.credit_score",
        "applicant.co_signer",
        "applicant.debt_ratio",
        "applicant.employment_status",
        "applicant.bankruptcy_history",
        "applicant.employment_duration_months",
        "loan.min_income",
        "loan.min_credit",
        "loan.max_debt_ratio",
        "applicant.has_collateral",
        "applicant.loan_amount_requested",
    }


def test_rule_nodes_have_readable_text_but_no_executable_function() -> None:
    graph = build_loan_graph()
    rule = graph.rule_for("loan.application_status")

    assert rule is not None
    assert "loan.application_status =" in rule.text
    assert rule.inputs == (
        "loan.applicant_prequalified",
        "applicant.loan_amount_requested",
        "loan.max_amount",
    )
    assert not hasattr(rule, "derive_fn")


def test_graph_and_slice_mappings_are_read_only() -> None:
    graph = build_loan_graph()
    graph_slice = graph.subgraph_for(["loan.adjusted_income"])

    with pytest.raises(TypeError):
        graph.facts["applicant.income"] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        graph_slice.facts["applicant.income"] = 1  # type: ignore[index]


def test_adapter_copies_caller_owned_facts() -> None:
    facts = {"applicant.income": 6000, "applicant.dependents": 2}
    graph = build_loan_graph(facts)

    facts["applicant.income"] = 1

    assert graph.facts["applicant.income"] == 6000


def test_traversal_does_not_create_derived_values() -> None:
    graph = build_loan_graph()

    graph_slice = graph.subgraph_for(["loan.adjusted_income"])

    assert graph_slice.facts == {
        "applicant.income": 6000,
        "applicant.dependents": 2,
    }
    assert "loan.adjusted_income" not in graph_slice.facts


def test_unknown_attribute_returns_an_empty_slice() -> None:
    graph = build_loan_graph()

    graph_slice = graph.subgraph_for(["loan.does_not_exist"])

    assert graph_slice.rules == ()
    assert dict(graph_slice.facts) == {}
