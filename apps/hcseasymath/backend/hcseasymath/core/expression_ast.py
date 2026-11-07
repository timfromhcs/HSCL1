"""Safe expression parser (decision D4).

User text is never handed to ``sympify``/``parse_expr`` (both use ``eval``). It is
parsed with :mod:`ast` in ``eval`` mode and walked by an allow-list visitor that
builds SymPy objects with explicit constructors. There is no name lookup in any
namespace, no attribute access, and no call except to a fixed function table.

Limits are checked while walking, before any expensive SymPy operation: a power
whose exponent is a number larger than ``MAX_EXPONENT`` is refused *before* the
power is formed, so ``9**9**9`` is a ``resource_limit`` error, not a hang.
"""

from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass

import sympy as sp

__all__ = ["ExpressionError", "Limits", "DEFAULT_LIMITS", "parse"]


class ExpressionError(ValueError):
    """The input is not an acceptable expression. ``code`` is machine readable."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Limits:
    max_chars: int = 500
    max_nodes: int = 200
    max_depth: int = 40
    max_int_digits: int = 30
    max_exponent: int = 10_000
    #: Upper bound on the size of a numeric power, estimated before it is formed.
    max_result_bits: int = 20_000


DEFAULT_LIMITS = Limits()

_SYMBOL = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,15}\Z")
_FUNCTIONS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
}
_CONSTANTS = {"pi": sp.pi, "e": sp.E}


def _invalid(message: str) -> ExpressionError:
    return ExpressionError("invalid_input", message)


def _limit(message: str) -> ExpressionError:
    return ExpressionError("resource_limit", message)


class _Builder:
    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self.nodes = 0

    def visit(self, node: ast.AST, depth: int = 0) -> sp.Basic:
        self.nodes += 1
        if self.nodes > self.limits.max_nodes:
            raise _limit(f"expression has more than {self.limits.max_nodes} nodes")
        if depth > self.limits.max_depth:
            raise _limit(f"expression is nested deeper than {self.limits.max_depth}")

        if isinstance(node, ast.Expression):
            return self.visit(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            return self.constant(node)
        if isinstance(node, ast.Name):
            return self.name(node)
        if isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand, depth + 1)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return operand
            raise _invalid("only unary + and - are allowed")
        if isinstance(node, ast.BinOp):
            return self.binop(node, depth)
        if isinstance(node, ast.Call):
            return self.call(node, depth)
        raise _invalid(f"{type(node).__name__} is not allowed in an expression")

    def constant(self, node: ast.Constant) -> sp.Basic:
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _invalid("only numbers are allowed as literals")
        if isinstance(value, int):
            if len(str(abs(value))) > self.limits.max_int_digits:
                raise _limit(f"integer literal has more than {self.limits.max_int_digits} digits")
            return sp.Integer(value)
        if value != value or value in (float("inf"), float("-inf")):
            raise _invalid("non-finite numbers are not allowed")
        # repr() is the shortest decimal that round-trips, i.e. what the user typed.
        return sp.Rational(repr(value))

    def name(self, node: ast.Name) -> sp.Basic:
        ident = node.id
        if ident in _FUNCTIONS:
            raise _invalid(f"'{ident}' is a function; write {ident}(...)")
        if ident in _CONSTANTS:
            return _CONSTANTS[ident]
        if not _SYMBOL.match(ident) or not ident.isascii():
            raise _invalid(f"'{ident}' is not a valid symbol name")
        if ident.startswith("__"):
            raise _invalid("names starting with '__' are not allowed")
        return sp.Symbol(ident)

    def binop(self, node: ast.BinOp, depth: int) -> sp.Basic:
        op = node.op
        if isinstance(op, ast.Pow):
            exponent = self.visit(node.right, depth + 1)
            if exponent.is_Number and abs(exponent) > self.limits.max_exponent:
                raise _limit(f"exponent larger than {self.limits.max_exponent}")
            base = self.visit(node.left, depth + 1)
            self.check_power_size(base, exponent)
            return sp.Pow(base, exponent)
        left = self.visit(node.left, depth + 1)
        right = self.visit(node.right, depth + 1)
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            if right == 0:
                raise _invalid("division by zero")
            return left / right
        if isinstance(op, ast.BitXor):
            raise _invalid("use ** for powers, not ^")
        raise _invalid(f"operator {type(op).__name__} is not allowed")

    def check_power_size(self, base: sp.Basic, exponent: sp.Basic) -> None:
        """Refuse numeric powers whose result would be huge, before computing them.

        An integer power ``p/q ** n`` has about ``n * max(bits(p), bits(q))`` bits.
        Products need no check: the AST is a tree, so a product is bounded by the
        sum of its leaves, which the node and literal limits already cap.
        """
        if not (exponent.is_Integer and base.is_Rational):
            return
        n = abs(int(exponent))
        if n <= 1:
            return
        width = max(abs(int(base.p)).bit_length(), int(base.q).bit_length())
        if n * width > self.limits.max_result_bits:
            raise _limit(
                f"numeric power would need about {n * width} bits "
                f"(limit {self.limits.max_result_bits})"
            )

    def call(self, node: ast.Call, depth: int) -> sp.Basic:
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise _invalid("only sin, cos, tan, exp, log and sqrt may be called")
        if node.keywords or len(node.args) != 1 or isinstance(node.args[0], ast.Starred):
            raise _invalid(f"{node.func.id} takes exactly one positional argument")
        return _FUNCTIONS[node.func.id](self.visit(node.args[0], depth + 1))


def parse(text: str, limits: Limits = DEFAULT_LIMITS) -> sp.Expr:
    """Parse ``text`` into a SymPy expression or raise :class:`ExpressionError`."""
    if not isinstance(text, str):
        raise _invalid("expression must be a string")
    if len(text) > limits.max_chars:
        raise _limit(f"expression is longer than {limits.max_chars} characters")
    if not text.strip():
        raise _invalid("expression is empty")
    if not text.isascii() or not text.isprintable():
        raise _invalid("only printable ASCII characters are allowed")
    try:
        with warnings.catch_warnings():
            # Noise such as "\." raises SyntaxWarning for a string literal we reject anyway.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise _invalid(f"cannot parse the expression: {exc.__class__.__name__}") from None
    try:
        result = _Builder(limits).visit(tree)
    except RecursionError:
        raise _limit("expression is nested too deeply") from None
    return result
