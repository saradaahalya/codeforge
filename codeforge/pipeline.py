"""The compiler pipeline: runs every finished phase and describes the results.

The web interface (and later a command-line tool) only talks to this file.
To add a new phase (parser, semantic analyzer, ...), do two things:
  1. write a small function like _tokens_phase() that returns a phase dict
  2. call it from run_pipeline() and remove that phase from PENDING_PHASES

Every phase result is a dict with the same shape, so the interface can
display any phase without special-casing it:
    id      -- short name used for the tab ("tokens", "ast", ...)
    title   -- text shown on the tab
    status  -- "done", "skipped" (an earlier phase found errors) or
               "pending" (not implemented yet)
    kind    -- how to display it: "table", "tree" or "text"
    data    -- the content (depends on kind)
    message -- only for "skipped": why the phase did not run
"""

from .ast_nodes import count_nodes, to_tree
from .lexer import tokenize
from .parser import parse
from .tokens import TokenType as T

# Which colour group each token type belongs to (used by the interface).
_CATEGORY = {}
for _t in (T.INT, T.IF, T.ELSE, T.WHILE, T.RETURN, T.PRINTF):
    _CATEGORY[_t] = "keyword"
_CATEGORY[T.IDENTIFIER] = "identifier"
_CATEGORY[T.INT_CONST] = "number"
_CATEGORY[T.STRING] = "string"
for _t in (T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.ASSIGN,
           T.EQ, T.NEQ, T.LT, T.LE, T.GT, T.GE, T.AND, T.OR, T.NOT):
    _CATEGORY[_t] = "operator"
for _t in (T.LPAREN, T.RPAREN, T.LBRACE, T.RBRACE, T.SEMICOLON, T.COMMA):
    _CATEGORY[_t] = "delimiter"
_CATEGORY[T.EOF] = "eof"

# Phases we have not built yet. They still appear as tabs, marked "coming soon".
PENDING_PHASES = [
    ("symbols", "Symbol table"),
    ("tac", "Three-address code"),
    ("optimized", "Optimized code"),
    ("assembly", "Assembly"),
]


def _tokens_phase(source):
    tokens, errors = tokenize(source)
    rows = [
        {
            "line": t.line,
            "column": t.column,
            "type": t.type.name,
            "lexeme": t.lexeme,
            "category": _CATEGORY[t.type],
        }
        for t in tokens
    ]
    phase = {
        "id": "tokens",
        "title": "Tokens",
        "status": "done",
        "kind": "table",
        "summary": f"{len(tokens) - 1} tokens",   # EOF is not counted
        "data": rows,
    }
    return phase, errors


def _skipped(phase_id, title, reason):
    return {"id": phase_id, "title": title, "status": "skipped",
            "kind": "text", "data": "", "message": reason}


def _ast_phase(tokens):
    program, errors = parse(tokens)
    if errors:
        return _skipped("ast", "Syntax tree (AST)",
                        "No tree was built because the program has syntax errors."), errors
    tree = to_tree(program)
    return {
        "id": "ast",
        "title": "Syntax tree (AST)",
        "status": "done",
        "kind": "tree",
        "summary": f"{count_nodes(tree)} nodes",
        "data": tree,
    }, errors


def run_pipeline(source):
    """Compile `source` as far as the finished phases allow."""
    errors = []
    phases = []

    # Phase 1: lexical analysis
    tokens_phase, lex_errors = _tokens_phase(source)
    phases.append(tokens_phase)
    errors.extend(lex_errors)

    # Phase 2: syntax analysis. Only run it on a clean token stream, because
    # a skipped bad character would cause confusing follow-up syntax errors.
    if lex_errors:
        phases.append(_skipped("ast", "Syntax tree (AST)",
                               "Skipped: fix the lexical errors first."))
    else:
        tokens, _ = tokenize(source)
        ast_phase, syntax_errors = _ast_phase(tokens)
        phases.append(ast_phase)
        errors.extend(syntax_errors)

    for phase_id, title in PENDING_PHASES:
        phases.append({"id": phase_id, "title": title, "status": "pending",
                       "kind": "text", "data": ""})

    return {
        "ok": not errors,
        "errors": [
            {"phase": e.phase, "message": e.message, "line": e.line, "column": e.column}
            for e in errors
        ],
        "phases": phases,
    }
