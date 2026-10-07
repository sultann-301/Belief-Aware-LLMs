"""Read-only graph adapters used by the GraphRAG evaluation baseline."""

from evaluation.graphrag.graph import DomainGraph, GraphSlice, RuleNode
from evaluation.graphrag.loan_adapter import build_loan_graph

__all__ = ["DomainGraph", "GraphSlice", "RuleNode", "build_loan_graph"]
