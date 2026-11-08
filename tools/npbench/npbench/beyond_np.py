"""Beyond-NP: exact #SAT counter for small formulas and toy QBF checker for closed prenex CNF.

Both tools are research-grade, not competitive. They return UNKNOWN when the budget is exhausted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

from .cnf import Cnf


@dataclass
class CountResult:
    """Result of exact model counting."""
    count: Optional[int]
    status: str  # "exact", "unknown"
    nodes_visited: int
    note: str


class NodeBudgetExhausted(Exception):
    """Raised when the node budget is exceeded during search."""
    pass


class ModelCounter:
    """
    DPLL-based exact model counter with component caching.

    - Splits the formula into independent components (variables that don't share clauses)
    - Caches counts for sub-formulas to avoid recomputation
    - Respects a node budget; raises NodeBudgetExhausted when exceeded
    """

    def __init__(self, formula: Cnf, node_budget: int = 100_000):
        self.formula = formula
        self.node_budget = node_budget
        self.nodes_visited = 0
        self._cache: Dict[Tuple[int, ...], int] = {}

    def _check_budget(self) -> None:
        self.nodes_visited += 1
        if self.nodes_visited > self.node_budget:
            raise NodeBudgetExhausted(f"node budget {self.node_budget} exceeded")

    def _split_components(self, clauses: List[Tuple[int, ...]]) -> List[List[Tuple[int, ...]]]:
        """Split clauses into connected components via shared variables."""
        if not clauses:
            return []

        # Build variable-to-clauses map
        var_to_clauses: Dict[int, Set[int]] = {}
        for ci, clause in enumerate(clauses):
            for lit in clause:
                var = abs(lit)
                var_to_clauses.setdefault(var, set()).add(ci)

        # Union-find for clause connectivity
        parent = list(range(len(clauses)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        # Connect clauses sharing variables
        for var, cl_set in var_to_clauses.items():
            cl_list = list(cl_set)
            for i in range(1, len(cl_list)):
                union(cl_list[0], cl_list[i])

        # Group clauses by component
        comps: Dict[int, List[Tuple[int, ...]]] = {}
        for ci, clause in enumerate(clauses):
            root = find(ci)
            comps.setdefault(root, []).append(clause)

        return list(comps.values())

    def _count_component(self, clauses: List[Tuple[int, ...]], num_vars: int) -> int:
        """Count models for a single connected component using DPLL with caching."""
        # Create cache key from sorted clauses
        key = tuple(sorted(clauses))
        if key in self._cache:
            return self._cache[key]

        self._check_budget()

        # Base cases
        if not clauses:
            return 1 << num_vars

        # Check for empty clause (UNSAT)
        if any(not c for c in clauses):
            return 0

        # Unit propagation
        up_result = self._unit_propagate(clauses)
        if up_result is None:
            return 0  # Conflict found
        simplified, assigned_vars = up_result
        if not simplified:
            return 1 << (num_vars - len(assigned_vars))

        # Choose variable (smallest variable heuristic) from remaining variables
        vars_in_clauses = set()
        for clause in simplified:
            for lit in clause:
                vars_in_clauses.add(abs(lit))

        # The remaining variables are those in clauses minus those already assigned
        remaining_vars = vars_in_clauses
        if not remaining_vars:
            return 1 << (num_vars - len(assigned_vars))

        var = min(remaining_vars)

        # Branch: var = True and var = False
        pos_clauses = self._assign(simplified, var, True)
        neg_clauses = self._assign(simplified, var, False)

        count_pos = self._count_component(pos_clauses, num_vars - 1)
        count_neg = self._count_component(neg_clauses, num_vars - 1)

        result = count_pos + count_neg
        self._cache[key] = result
        return result

    def _unit_propagate(self, clauses: List[Tuple[int, ...]]) -> Optional[Tuple[List[Tuple[int, ...]], Set[int]]]:
        """Apply unit propagation. Returns (simplified_clauses, assigned_vars) or None on conflict.
        assigned_vars is the set of variables that were assigned by unit propagation."""
        clauses = [list(c) for c in clauses]
        changed = True
        assigned_vars: Set[int] = set()

        while changed:
            changed = False
            # Find unit clauses
            unit_lits = {c[0] for c in clauses if len(c) == 1}
            if not unit_lits:
                break

            # Check for conflicts (both x and -x are units)
            for lit in unit_lits:
                if -lit in unit_lits:
                    return None

            # Apply unit assignments
            new_clauses = []
            for clause in clauses:
                new_clause = []
                clause_satisfied = False
                for lit in clause:
                    if lit in unit_lits:
                        # Clause satisfied
                        clause_satisfied = True
                        break
                    elif -lit in unit_lits:
                        # Literal falsified, remove it
                        continue
                    else:
                        new_clause.append(lit)
                if not clause_satisfied:
                    new_clauses.append(tuple(new_clause))

            # Track assigned variables
            for lit in unit_lits:
                assigned_vars.add(abs(lit))

            # Check for empty clause
            if any(not c for c in new_clauses):
                return None

            clauses = new_clauses
            changed = True

        return [c for c in clauses if c], assigned_vars

    def _assign(self, clauses: List[Tuple[int, ...]], var: int, value: bool) -> List[Tuple[int, ...]]:
        """Assign var=value and simplify clauses."""
        result = []
        lit = var if value else -var
        falsified = -lit

        for clause in clauses:
            if lit in clause:
                continue  # Clause satisfied
            new_clause = tuple(l for l in clause if l != falsified)
            if not new_clause:
                # Empty clause -> conflict
                return [()]  # Single empty clause signals UNSAT
            result.append(new_clause)

        return result

    def count(self) -> CountResult:
        """Count models, returning exact count or UNKNOWN on budget exhaustion."""
        try:
            # Handle special case: no clauses but variables exist
            if not self.formula.clauses:
                if self.formula.num_vars > 0:
                    return CountResult(
                        count=1 << self.formula.num_vars,
                        status="exact",
                        nodes_visited=0,
                        note=f"no constraints, all {self.formula.num_vars} variables free"
                    )
                else:
                    return CountResult(
                        count=1,
                        status="exact",
                        nodes_visited=0,
                        note="empty formula with no variables"
                    )

            # Split into components
            components = self._split_components(self.formula.clauses)
            total = 1

            # Track which variables appear in clauses
            all_clause_vars = set()
            for comp in components:
                comp_vars = {abs(lit) for clause in comp for lit in clause}
                all_clause_vars.update(comp_vars)
                comp_count = self._count_component(comp, len(comp_vars))
                total *= comp_count

            # Account for completely free variables (not in any clause)
            free_vars = self.formula.num_vars - len(all_clause_vars)
            if free_vars > 0:
                total *= 1 << free_vars

            return CountResult(
                count=total,
                status="exact",
                nodes_visited=self.nodes_visited,
                note=f"exact count for {self.formula.num_vars} variables"
            )
        except NodeBudgetExhausted as e:
            return CountResult(
                count=None,
                status="unknown",
                nodes_visited=self.nodes_visited,
                note=str(e)
            )


def count_models(formula: Cnf, node_budget: int = 100_000) -> CountResult:
    """Count models of a CNF formula with a node budget."""
    counter = ModelCounter(formula, node_budget)
    return counter.count()


# ============================================================================
# Toy QBF Checker for closed prenex CNF
# ============================================================================

@dataclass
class QBFResult:
    """Result of QBF checking."""
    status: str  # "SAT", "UNSAT", "unknown", "malformed"
    nodes_visited: int
    note: str


def _parse_qbf_dimacs(text: str) -> Tuple[List[List[int]], List[str]]:
    """
    Parse a QDIMACS-like format with quantifier prefixes.
    Format: lines starting with 'a' (forall) or 'e' (exists), then 'p cnf ...'
    Returns (clauses, quantifier_sequence) where quantifier_sequence is e.g. ['a', 'e', 'e', 'a']
    """
    lines = text.strip().split('\n')
    quantifiers: List[str] = []
    clauses: List[List[int]] = []
    header_found = False

    for line in lines:
        line = line.strip()
        if not line or line.startswith('c'):
            continue
        if line.startswith(('a ', 'e ')):
            parts = line.split()
            qtype = parts[0]  # 'a' or 'e'
            vars_in_scope = [int(x) for x in parts[1:] if x != '0']
            for _ in vars_in_scope:
                quantifiers.append(qtype)
        elif line.startswith('p cnf'):
            header_found = True
        else:
            # Clause line
            lits = [int(x) for x in line.split() if x != '0']
            if lits:
                clauses.append(lits)

    if not header_found:
        raise ValueError("no p cnf header found")
    return clauses, quantifiers


def check_qbf_closed(clauses: List[List[int]], quantifiers: List[str], node_budget: int = 50_000) -> QBFResult:
    """
    Check a closed prenex QBF by exhaustive assignment walk.
    Returns SAT/UNSAT/unknown (budget exhausted) or malformed.
    """
    if not quantifiers:
        raise ValueError("no quantifiers provided")
    if len(quantifiers) != len(set(abs(lit) for clause in clauses for lit in clause)):
        raise ValueError("quantifier count mismatch with variables")

    n_vars = len(quantifiers)
    nodes_visited = 0

    def check_budget() -> bool:
        nonlocal nodes_visited
        nodes_visited += 1
        return nodes_visited > node_budget

    # Recursive evaluation of QBF
    def evaluate(idx: int, assignment: Dict[int, bool]) -> Optional[bool]:
        """Returns True (SAT), False (UNSAT), or None (budget exhausted)."""
        if check_budget():
            return None

        if idx == n_vars:
            # Check if all clauses satisfied
            for clause in clauses:
                clause_sat = False
                for lit in clause:
                    var = abs(lit)
                    val = assignment[var]
                    if (lit > 0 and val) or (lit < 0 and not val):
                        clause_sat = True
                        break
                if not clause_sat:
                    return False
            return True

        var = idx + 1
        qtype = quantifiers[idx]

        if qtype == 'e':  # exists: need at least one True
            for val in (True, False):
                assignment[var] = val
                res = evaluate(idx + 1, assignment)
                if res is None:
                    return None
                if res:
                    return True
            return False
        elif qtype == 'a':  # forall: need all True
            for val in (True, False):
                assignment[var] = val
                res = evaluate(idx + 1, assignment)
                if res is None:
                    return None
                if not res:
                    return False
            return True
        else:
            raise ValueError(f"invalid quantifier {qtype}")

    result = evaluate(0, {})
    if result is None:
        return QBFResult(status="unknown", nodes_visited=nodes_visited, note=f"node budget {node_budget} exhausted")
    return QBFResult(
        status="SAT" if result else "UNSAT",
        nodes_visited=nodes_visited,
        note="exhaustive evaluation"
    )


def check_qbf_from_text(text: str, node_budget: int = 50_000) -> QBFResult:
    """Parse QDIMACS text and check the QBF."""
    try:
        clauses, quantifiers = _parse_qbf_dimacs(text)
    except Exception as e:
        return QBFResult(status="malformed", nodes_visited=0, note=str(e))
    try:
        return check_qbf_closed(clauses, quantifiers, node_budget)
    except ValueError as e:
        return QBFResult(status="malformed", nodes_visited=0, note=str(e))


# ============================================================================
# Integration with runner
# ============================================================================

def run_beyond_np_instance(spec: Dict[str, Any], formula: Cnf, solver: str, *,
                            budget_s: float, seed: int = 0, node_budget: int = 100_000) -> Dict[str, Any]:
    """
    Run beyond-NP solver on an instance.
    Solver: 'count' for #SAT, 'qbf' for QBF (requires spec with quantifiers)
    """
    import time
    start = time.time()

    record: Dict[str, Any] = {
        "id": spec.get("id", "unknown"),
        "solver": solver,
        "budget_s": budget_s,
        "elapsed_s": 0.0,
        "status": "UNKNOWN",
        "certification": "NONE",
        "note": "",
    }

    try:
        if solver == "count":
            result = count_models(formula, node_budget)
            record["status"] = "SAT" if result.status == "exact" else "UNKNOWN"
            record["note"] = f"count={result.count}, nodes={result.nodes_visited}, {result.note}"
            record["model_count"] = result.count
            record["nodes_visited"] = result.nodes_visited
        elif solver == "qbf":
            # For QBF, the spec must contain quantifier info
            if "quantifiers" not in spec:
                record["status"] = "error"
                record["note"] = "QBF spec missing quantifiers"
            else:
                clauses = [list(c) for c in formula.clauses]
                qbf_result = check_qbf_closed(clauses, spec["quantifiers"], node_budget)
                record["status"] = qbf_result.status
                record["note"] = f"nodes={qbf_result.nodes_visited}, {qbf_result.note}"
                record["nodes_visited"] = qbf_result.nodes_visited
        else:
            record["status"] = "error"
            record["note"] = f"unknown solver {solver}"
    except Exception as e:
        record["status"] = "error"
        record["note"] = str(e)

    record["elapsed_s"] = time.time() - start
    return record