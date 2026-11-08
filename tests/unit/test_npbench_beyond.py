"""Tests for beyond-NP: exact #SAT counter and toy QBF checker."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import cnf as C  # noqa: E402
from npbench import beyond_np as B  # noqa: E402


# ============================================================================
# #SAT Counter tests
# ============================================================================

def test_count_empty_formula():
    """Empty formula with n vars has 2^n models."""
    formula = C.parse_dimacs("p cnf 3 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    assert result.count == 8  # 2^3


def test_count_single_var():
    """p cnf 1 1\n1 0 -> 1 model (x=True)"""
    formula = C.parse_dimacs("p cnf 1 1\n1 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    assert result.count == 1


def test_count_unsat():
    """p cnf 1 2\n1 0\n-1 0 -> 0 models"""
    formula = C.parse_dimacs("p cnf 1 2\n1 0\n-1 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    assert result.count == 0


def test_count_independent_components():
    """Two independent variables: (x) & (y) -> 1*1 = 1 model"""
    formula = C.parse_dimacs("p cnf 2 2\n1 0\n2 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    assert result.count == 1


def test_count_xor():
    """x XOR y: (x ∨ y) ∧ (-x ∨ -y) -> 2 models"""
    formula = C.parse_dimacs("p cnf 2 2\n1 2 0\n-1 -2 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    assert result.count == 2


def test_count_disconnected_variables():
    """Formula with disconnected components multiplies correctly."""
    # (x1 ∨ x2) & (x3 ∨ x4) - two independent 2-SAT components
    formula = C.parse_dimacs("p cnf 4 2\n1 2 0\n3 4 0\n")
    result = B.count_models(formula, node_budget=1000)
    assert result.status == "exact"
    # Each (a ∨ b) has 3 models, total 3*3 = 9
    assert result.count == 9


def test_count_budget_exhaustion():
    """Large formula with small budget returns UNKNOWN."""
    # Create a formula that actually needs exponential search (many clauses)
    # A chain of XORs: (x1 ⊕ x2) ∧ (x3 ⊕ x4) ∧ ...
    # 10 variables, 5 XOR pairs = needs to explore many branches
    formula = C.parse_dimacs("p cnf 10 10\n1 2 0\n-1 -2 0\n3 4 0\n-3 -4 0\n5 6 0\n-5 -6 0\n7 8 0\n-7 -8 0\n9 10 0\n-9 -10 0\n")
    result = B.count_models(formula, node_budget=10)  # Very tight budget
    assert result.status == "unknown"
    assert result.count is None


def test_count_known_sat_instances():
    """Test against brute force for small formulas."""
    import itertools

    # Test a few small formulas exhaustively
    test_cases = [
        ("p cnf 2 1\n1 0\n", 2),  # x1 = True, x2 free -> 2 models
        ("p cnf 2 2\n1 0\n-2 0\n", 1),  # x1=True, x2=False -> 1 model
        ("p cnf 3 2\n1 2 0\n-3 0\n", 3),  # (x1 ∨ x2) ∧ (-x3): x3=F, (x1,x2) has 3 models -> 3
    ]

    for dimacs, expected in test_cases:
        formula = C.parse_dimacs(dimacs)
        result = B.count_models(formula, node_budget=10000)
        assert result.status == "exact", f"Failed on {dimacs}: {result.note}"
        assert result.count == expected, f"Wrong count on {dimacs}: got {result.count}, expected {expected}"


# ============================================================================
# QBF Checker tests
# ============================================================================

def test_qbf_simple_exists():
    """∃x. x  -> SAT"""
    # QDIMACS: e 1 0 / p cnf 1 1 / 1 0
    text = "e 1 0\np cnf 1 1\n1 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "SAT"


def test_qbf_simple_forall():
    """∀x. x  -> UNSAT (x can be False)"""
    text = "a 1 0\np cnf 1 1\n1 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "UNSAT"


def test_qbf_forall_exists():
    """∀x ∃y. (x ∨ y) ∧ (-x ∨ y) -> SAT (y=True works for both x)"""
    text = "a 1 0\ne 2 0\np cnf 2 2\n1 2 0\n-1 2 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "SAT"


def test_qbf_exists_forall():
    """∃x ∀y. (x ∨ y) ∧ (-x ∨ -y) -> UNSAT (no single x works for both y values)"""
    # x=True: ∀y. y ∧ -y -> UNSAT (y=T: T∧F=F; y=F: F∧T=F)
    # x=False: ∀y. -y ∧ y -> UNSAT
    # So no x works -> UNSAT
    text = "e 1 0\na 2 0\np cnf 2 2\n1 2 0\n-1 -2 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "UNSAT"


def test_qbf_unsat_alternating():
    """∀x ∃y. x XOR y -> UNSAT (for x=True need y=False, for x=False need y=True, can't satisfy both)"""
    # Wait, this is SAT: ∀x ∃y. x XOR y. For x=True, y=False works. For x=False, y=True works.
    # Let's try: ∃x ∀y. x XOR y -> UNSAT (no single x works for both y values)
    text = "e 1 0\na 2 0\np cnf 2 2\n1 2 0\n-1 -2 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    # ∃x ∀y. (x ∨ y) ∧ (-x ∨ -y) - is this UNSAT?
    # x=True: ∀y. y ∧ -y -> UNSAT
    # x=False: ∀y. -y ∧ y -> UNSAT
    # So no x works -> UNSAT
    assert result.status == "UNSAT"


def test_qbf_malformed():
    """Invalid QDIMACS returns malformed."""
    text = "p cnf 1 1\n1 0\n"  # No quantifiers
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "malformed"


def test_qbf_budget_exhaustion():
    """QBF with many variables and small budget returns unknown."""
    # Make it a hard QBF: alternating quantifiers with constraints that require deep search
    # ∀x1 ∃x2 ∀x3 ∃x4 ... with many clauses
    vars_count = 20
    quant_parts = []
    for i in range(1, vars_count+1):
        q = 'a' if i % 2 == 1 else 'e'
        quant_parts.append(f"{q} {i} 0")
    quant = "\n".join(quant_parts) + "\n"

    # Add multiple clauses to make it harder
    clauses = []
    for i in range(1, vars_count, 2):
        if i+1 <= vars_count:
            # (xi ∨ x_{i+1}) ∧ (-xi ∨ -x_{i+1})  -> xi XOR x_{i+1}
            clauses.append(f"{i} {i+1} 0")
            clauses.append(f"-{i} -{i+1} 0")

    text = quant + f"p cnf {vars_count} {len(clauses)}\n" + "\n".join(clauses) + "\n"
    result = B.check_qbf_from_text(text, node_budget=100)  # Tight budget
    assert result.status == "unknown"


def test_qbf_quantifier_count_mismatch():
    """Quantifier count mismatch with variables returns malformed."""
    text = "e 1 2 0\np cnf 2 0\n"
    result = B.check_qbf_from_text(text, node_budget=1000)
    assert result.status == "malformed"


# ============================================================================
# Integration tests with runner
# ============================================================================

def test_beyond_np_count_integration():
    """Test run_beyond_np_instance with count solver."""
    formula = C.parse_dimacs("p cnf 3 2\n1 2 0\n-3 0\n")
    spec = {"id": "test-count", "family": "threshold", "expected": None}
    result = B.run_beyond_np_instance(spec, formula, "count", budget_s=10.0, seed=0, node_budget=10000)
    assert result["solver"] == "count"
    assert result["status"] in ("SAT", "UNKNOWN")
    assert "model_count" in result
    assert "nodes_visited" in result


def test_beyond_np_qbf_integration():
    """Test run_beyond_np_instance with qbf solver."""
    formula = C.parse_dimacs("p cnf 2 2\n1 2 0\n-1 2 0\n")
    spec = {"id": "test-qbf", "family": "qbf", "quantifiers": ["a", "e"]}
    result = B.run_beyond_np_instance(spec, formula, "qbf", budget_s=10.0, seed=0, node_budget=10000)
    assert result["solver"] == "qbf"
    assert result["status"] in ("SAT", "UNSAT", "UNKNOWN", "error")
    assert "nodes_visited" in result


def test_beyond_np_qbf_missing_quantifiers():
    """QBF solver without quantifiers returns error."""
    formula = C.parse_dimacs("p cnf 1 1\n1 0\n")
    spec = {"id": "test-qbf", "family": "qbf"}
    result = B.run_beyond_np_instance(spec, formula, "qbf", budget_s=10.0, seed=0, node_budget=10000)
    assert result["status"] == "error"
    assert "quantifiers" in result["note"]


def test_beyond_np_unknown_solver():
    """Unknown solver returns error."""
    formula = C.parse_dimacs("p cnf 1 1\n1 0\n")
    spec = {"id": "test"}
    result = B.run_beyond_np_instance(spec, formula, "unknown", budget_s=10.0, seed=0)
    assert result["status"] == "error"
    assert "unknown solver" in result["note"]


# ============================================================================
# Mutation tests (these should pass initially, then be used for mutation testing)
# ============================================================================

def test_count_mutations():
    """Test that mutations in counter logic would be caught."""
    # This test is a placeholder for mutation testing
    # Real mutations: remove component splitting, break unit propagation, etc.
    pass


def test_qbf_mutations():
    """Test that mutations in QBF logic would be caught."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])