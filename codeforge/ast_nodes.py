"""Abstract Syntax Tree (AST) node definitions.

The parser builds a tree of these objects. The tree keeps only the meaning of
the program: parentheses and semicolons are not stored, because the shape of
the tree already shows how the expressions are grouped.

Every node remembers the line and column of the token it came from, so later
phases (semantic analysis) can point at the exact place when they report an error.
"""

from dataclasses import dataclass, fields
from typing import Optional


class Node:
    """Base class for every AST node."""

    category = "node"      # colour group used by the interface

    def label(self):
        return type(self).__name__


# ---------- program structure ----------

@dataclass
class Program(Node):
    functions: list
    line: int = 1
    column: int = 1
    category = "program"

    def label(self):
        return "Program"


@dataclass
class Param(Node):
    name: str
    line: int = 0
    column: int = 0
    category = "declaration"

    def label(self):
        return f"param {self.name}"


@dataclass
class Function(Node):
    name: str
    params: list
    body: "Block"
    line: int = 0
    column: int = 0
    category = "declaration"

    def label(self):
        return f"function {self.name}"


# ---------- statements ----------

@dataclass
class Block(Node):
    statements: list
    line: int = 0
    column: int = 0
    category = "statement"


@dataclass
class VarDecl(Node):
    name: str
    init: Optional[Node] = None
    line: int = 0
    column: int = 0
    category = "declaration"

    def label(self):
        return f"declare {self.name}"


@dataclass
class Assign(Node):
    name: str
    value: Node
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return f"assign {self.name}"


@dataclass
class If(Node):
    condition: Node
    then_branch: Node
    else_branch: Optional[Node] = None
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return "if"


@dataclass
class While(Node):
    condition: Node
    body: Node
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return "while"


@dataclass
class Return(Node):
    value: Node
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return "return"


@dataclass
class Printf(Node):
    format: str
    args: list
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return f"printf {self.format!r}"


@dataclass
class ExprStmt(Node):
    """An expression used as a statement, e.g. a function call: foo(1);"""
    expr: Node
    line: int = 0
    column: int = 0
    category = "statement"

    def label(self):
        return "expression statement"


# ---------- expressions ----------

@dataclass
class IntLiteral(Node):
    value: int
    line: int = 0
    column: int = 0
    category = "literal"

    def label(self):
        return str(self.value)


@dataclass
class Var(Node):
    name: str
    line: int = 0
    column: int = 0
    category = "name"

    def label(self):
        return self.name


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node
    line: int = 0
    column: int = 0
    category = "expression"

    def label(self):
        return f"unary {self.op}"


@dataclass
class BinaryOp(Node):
    op: str
    left: Node
    right: Node
    line: int = 0
    column: int = 0
    category = "expression"

    def label(self):
        return self.op


@dataclass
class Call(Node):
    name: str
    args: list
    line: int = 0
    column: int = 0
    category = "expression"

    def label(self):
        return f"call {self.name}"


# ---------- turning a tree into plain data for the interface ----------

_ROLE_NAMES = {"then_branch": "then", "else_branch": "else"}


def to_tree(node, role=None):
    """Convert an AST node into nested dicts (easy to send as JSON)."""
    children = []
    for f in fields(node):
        if f.name in ("line", "column"):
            continue
        value = getattr(node, f.name)
        if isinstance(value, Node):
            children.append(to_tree(value, _ROLE_NAMES.get(f.name, f.name)))
        elif isinstance(value, list):
            children.extend(to_tree(item) for item in value if isinstance(item, Node))
    return {
        "label": node.label(),
        "role": role,
        "category": node.category,
        "line": node.line,
        "column": node.column,
        "children": children,
    }


def count_nodes(tree):
    return 1 + sum(count_nodes(c) for c in tree["children"])
