"""Phase 2: Syntax analysis (parsing) and AST construction.

This is a hand-written *recursive-descent* parser: there is one method for
each rule of the grammar (see docs/grammar.md), and the methods call each
other the same way the grammar rules refer to each other.

Operator precedence is built into the order of the expression methods:
the rule for the LOWEST-precedence operator calls the rule for the next
higher one, and so on down to the primary expressions (numbers, names,
parentheses). A higher-precedence operator therefore ends up deeper in the
tree, which is why 2 + 3 * 4 is grouped as 2 + (3 * 4).

When a syntax error is found, the parser records it and then "synchronizes":
it skips tokens until a likely statement boundary, so that several errors can
be reported in one run instead of only the first.
"""

from .ast_nodes import (
    Assign, BinaryOp, Block, Call, ExprStmt, Function, If, IntLiteral,
    Param, Printf, Program, Return, UnaryOp, Var, VarDecl, While,
)
from .errors import CompileError
from .tokens import TokenType as T

# Tokens that can start a statement; used to find a safe place to resume.
_STATEMENT_START = (T.INT, T.IF, T.WHILE, T.RETURN, T.PRINTF, T.LBRACE, T.RBRACE)


class ParseError(Exception):
    """Raised to unwind to the nearest recovery point. The error itself is
    already stored in Parser.errors, so this carries no message."""


def _describe(token):
    return "end of input" if token.type == T.EOF else f"'{token.lexeme}'"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens     # the list always ends with an EOF token
        self.pos = 0
        self.errors = []

    # ---------- token helpers ----------

    def _peek(self, offset=0):
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def _at_end(self):
        return self._peek().type == T.EOF

    def _check(self, *types):
        return self._peek().type in types

    def _advance(self):
        token = self._peek()
        if not self._at_end():
            self.pos += 1
        return token

    def _match(self, *types):
        """Consume the next token if it has one of the given types."""
        return self._advance() if self._check(*types) else None

    def _expect(self, ttype, what):
        """Consume a token of the given type, or report a syntax error."""
        if self._check(ttype):
            return self._advance()
        raise self._fail_after_previous(f"expected {what}")

    # ---------- error reporting ----------

    def _record(self, message, line, column):
        # Skip a second error at the same spot (a typical knock-on effect).
        if self.errors and (self.errors[-1].line, self.errors[-1].column) == (line, column):
            return
        self.errors.append(CompileError("syntax", message, line, column))

    def _fail_here(self, message):
        """Error located at the token we are looking at."""
        tok = self._peek()
        self._record(f"{message}, but found {_describe(tok)}", tok.line, tok.column)
        return ParseError()

    def _fail_after_previous(self, message):
        """Error located just after the previous token.

        For a missing ';' or ')' this points at the end of the line where it
        was forgotten, which is where a programmer expects the error to be.
        """
        if self.pos == 0:
            return self._fail_here(message)
        prev = self.tokens[self.pos - 1]
        tok = self._peek()
        self._record(f"{message}, but found {_describe(tok)}", prev.line, prev.column + len(prev.lexeme))
        return ParseError()

    def _synchronize(self):
        """Skip tokens until a likely statement boundary (error recovery)."""
        while not self._at_end():
            if self.pos > 0 and self.tokens[self.pos - 1].type == T.SEMICOLON:
                return
            if self._check(*_STATEMENT_START):
                return
            self._advance()

    def _synchronize_to_next_function(self):
        """Skip tokens until something that looks like 'int name(' again."""
        while not self._at_end():
            if (self._check(T.INT) and self._peek(1).type == T.IDENTIFIER
                    and self._peek(2).type == T.LPAREN):
                return
            self._advance()

    # ---------- program and functions ----------

    def parse(self):
        """program -> function+ EOF.  Returns (Program, errors)."""
        functions = []
        try:
            if self._at_end():
                self._record("the program is empty: expected at least one function", 1, 1)
            while not self._at_end():
                start = self.pos
                try:
                    functions.append(self._function())
                except ParseError:
                    self._synchronize_to_next_function()
                    if self.pos == start:      # guarantee progress, never loop forever
                        self._advance()
        except RecursionError:
            tok = self._peek()
            self._record("the program is nested too deeply to parse", tok.line, tok.column)
        return Program(functions), self.errors

    def _function(self):
        # function -> "int" IDENT "(" [ params ] ")" block
        if not self._check(T.INT):
            raise self._fail_here("expected a function definition starting with 'int'")
        self._advance()
        name = self._expect(T.IDENTIFIER, "a function name after 'int'")
        self._expect(T.LPAREN, "'(' after the function name")
        params = self._params()
        self._expect(T.RPAREN, "')' after the parameters")
        body = self._block()
        return Function(name.lexeme, params, body, name.line, name.column)

    def _params(self):
        # params -> "int" IDENT ( "," "int" IDENT )*
        params = []
        if self._check(T.RPAREN):
            return params
        while True:
            self._expect(T.INT, "'int' before the parameter name")
            name = self._expect(T.IDENTIFIER, "a parameter name")
            params.append(Param(name.lexeme, name.line, name.column))
            if not self._match(T.COMMA):
                break
        return params

    # ---------- statements ----------

    def _block(self):
        # block -> "{" statement* "}"
        lbrace = self._expect(T.LBRACE, "'{' to start the block")
        statements = []
        while not self._check(T.RBRACE) and not self._at_end():
            start = self.pos
            try:
                statements.append(self._statement())
            except ParseError:
                self._synchronize()
                if self.pos == start:          # guarantee progress
                    self._advance()
        self._expect(T.RBRACE, "'}' to close the block")
        return Block(statements, lbrace.line, lbrace.column)

    def _statement(self):
        tok = self._peek()
        if tok.type == T.LBRACE:
            return self._block()
        if tok.type == T.INT:
            return self._declaration()
        if tok.type == T.IF:
            return self._if()
        if tok.type == T.WHILE:
            return self._while()
        if tok.type == T.RETURN:
            return self._return()
        if tok.type == T.PRINTF:
            return self._printf()
        if tok.type == T.IDENTIFIER:
            return self._assignment_or_call()
        raise self._fail_here("expected a statement")

    def _declaration(self):
        # declaration -> "int" IDENT [ "=" expression ] ";"
        self._advance()                        # the 'int'
        name = self._expect(T.IDENTIFIER, "a variable name after 'int'")
        init = self._expression() if self._match(T.ASSIGN) else None
        self._expect(T.SEMICOLON, "';' after the declaration")
        return VarDecl(name.lexeme, init, name.line, name.column)

    def _if(self):
        # ifStmt -> "if" "(" expression ")" statement [ "else" statement ]
        kw = self._advance()
        self._expect(T.LPAREN, "'(' after 'if'")
        condition = self._expression()
        self._expect(T.RPAREN, "')' after the condition")
        then_branch = self._statement()
        # An 'else' always belongs to the nearest 'if' (the "dangling else" rule),
        # which happens naturally because we look for it right here.
        else_branch = self._statement() if self._match(T.ELSE) else None
        return If(condition, then_branch, else_branch, kw.line, kw.column)

    def _while(self):
        # whileStmt -> "while" "(" expression ")" statement
        kw = self._advance()
        self._expect(T.LPAREN, "'(' after 'while'")
        condition = self._expression()
        self._expect(T.RPAREN, "')' after the condition")
        body = self._statement()
        return While(condition, body, kw.line, kw.column)

    def _return(self):
        # returnStmt -> "return" expression ";"
        kw = self._advance()
        value = self._expression()
        self._expect(T.SEMICOLON, "';' after the return value")
        return Return(value, kw.line, kw.column)

    def _printf(self):
        # printfStmt -> "printf" "(" STRING { "," expression } ")" ";"
        kw = self._advance()
        self._expect(T.LPAREN, "'(' after 'printf'")
        fmt = self._expect(T.STRING, "a format string")
        args = []
        while self._match(T.COMMA):
            args.append(self._expression())
        self._expect(T.RPAREN, "')' after the printf arguments")
        self._expect(T.SEMICOLON, "';' after printf(...)")
        return Printf(fmt.value, args, kw.line, kw.column)

    def _assignment_or_call(self):
        # Both start with an identifier; the NEXT token tells them apart.
        name = self._advance()
        if self._match(T.ASSIGN):
            value = self._expression()
            self._expect(T.SEMICOLON, "';' after the assignment")
            return Assign(name.lexeme, value, name.line, name.column)
        if self._check(T.LPAREN):
            call = self._finish_call(name)
            self._expect(T.SEMICOLON, "';' after the function call")
            return ExprStmt(call, name.line, name.column)
        raise self._fail_after_previous(f"expected '=' or '(' after '{name.lexeme}'")

    # ---------- expressions (lowest precedence first) ----------

    def _expression(self):
        return self._logic_or()

    def _binary(self, operand, operators):
        """Parse  operand (op operand)*  and group it to the LEFT.

        Using a loop instead of a left-recursive rule is what makes
        10 - 4 - 3 mean (10 - 4) - 3 and avoids infinite recursion.
        """
        left = operand()
        while self._check(*operators):
            op = self._advance()
            right = operand()
            left = BinaryOp(op.lexeme, left, right, op.line, op.column)
        return left

    def _logic_or(self):      # lowest precedence
        return self._binary(self._logic_and, (T.OR,))

    def _logic_and(self):
        return self._binary(self._equality, (T.AND,))

    def _equality(self):
        return self._binary(self._relational, (T.EQ, T.NEQ))

    def _relational(self):
        return self._binary(self._additive, (T.LT, T.LE, T.GT, T.GE))

    def _additive(self):
        return self._binary(self._term, (T.PLUS, T.MINUS))

    def _term(self):
        return self._binary(self._unary, (T.STAR, T.SLASH, T.PERCENT))

    def _unary(self):
        # unary -> ( "-" | "!" ) unary | primary     (right-recursive: --x, !!x)
        if self._check(T.MINUS, T.NOT):
            op = self._advance()
            return UnaryOp(op.lexeme, self._unary(), op.line, op.column)
        return self._primary()

    def _primary(self):    # highest precedence
        tok = self._peek()
        if tok.type == T.INT_CONST:
            self._advance()
            return IntLiteral(tok.value, tok.line, tok.column)
        if tok.type == T.IDENTIFIER:
            self._advance()
            if self._check(T.LPAREN):
                return self._finish_call(tok)
            return Var(tok.lexeme, tok.line, tok.column)
        if tok.type == T.LPAREN:
            self._advance()
            inner = self._expression()
            self._expect(T.RPAREN, "')' to close the parenthesis")
            return inner          # parentheses only affect grouping; no node needed
        raise self._fail_here("expected an expression")

    def _finish_call(self, name):
        # call -> IDENT "(" [ expression ( "," expression )* ] ")"
        self._advance()                        # the '('
        args = []
        if not self._check(T.RPAREN):
            args.append(self._expression())
            while self._match(T.COMMA):
                args.append(self._expression())
        self._expect(T.RPAREN, "')' after the arguments")
        return Call(name.lexeme, args, name.line, name.column)


def parse(tokens):
    """Convenience wrapper: returns (Program, errors)."""
    return Parser(tokens).parse()
