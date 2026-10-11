"""Phase 1: Lexical analysis.

The lexer reads the source text one character at a time and groups the
characters into tokens (keywords, identifiers, numbers, operators, ...).
Whitespace and comments are skipped. Characters that do not belong to the
language are reported as lexical errors, and scanning continues so that
several errors can be shown in one run.
"""

import sys

from .errors import CompileError
from .tokens import (
    KEYWORDS,
    SINGLE_CHAR_TOKENS,
    TWO_CHAR_OPERATORS,
    Token,
    TokenType,
)

ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "0": "\0"}


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0          # index of the next unread character
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

    # ---------- small helpers ----------

    def _peek(self, offset=0):
        """Look at a character without consuming it ('' at end of input)."""
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ""

    def _advance(self):
        """Consume one character and keep line/column up to date."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _error(self, message, line, column):
        self.errors.append(CompileError("lexical", message, line, column))

    def _add(self, ttype, lexeme, line, column, value=None):
        self.tokens.append(Token(ttype, lexeme, line, column, value))

    # ---------- skipping whitespace and comments ----------

    def _skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":      # // line comment
                while self.pos < len(self.source) and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":      # /* block comment */
                start_line, start_col = self.line, self.column
                self._advance()
                self._advance()
                closed = False
                while self.pos < len(self.source):
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    self._error("unterminated comment", start_line, start_col)
            else:
                break

    # ---------- scanning each kind of token ----------

    def _scan_word(self):
        """Identifier or keyword: a letter/underscore, then letters/digits/underscores."""
        line, col = self.line, self.column
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[start:self.pos]
        self._add(KEYWORDS.get(text, TokenType.IDENTIFIER), text, line, col)

    def _scan_number(self):
        line, col = self.line, self.column
        start = self.pos
        while self._peek().isdigit():
            self._advance()
        # A number directly followed by a letter, such as 12abc, is invalid.
        if self._peek().isalpha() or self._peek() == "_":
            while self._peek().isalnum() or self._peek() == "_":
                self._advance()
            text = self.source[start:self.pos]
            self._error(f"invalid number or identifier '{text}'", line, col)
            return
        text = self.source[start:self.pos]
        self._add(TokenType.INT_CONST, text, line, col, int(text))

    def _scan_string(self):
        line, col = self.line, self.column
        start = self.pos
        self._advance()                      # opening quote
        chars = []
        while True:
            ch = self._peek()
            if ch == "" or ch == "\n":
                self._error("unterminated string literal", line, col)
                return
            if ch == '"':
                self._advance()              # closing quote
                break
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in ESCAPES:
                    chars.append(ESCAPES[esc])
                    self._advance()
                else:
                    self._error(f"unknown escape sequence '\\{esc}'", self.line, self.column - 1)
                    if esc not in ("", "\n"):
                        self._advance()
            else:
                chars.append(self._advance())
        self._add(TokenType.STRING, self.source[start:self.pos], line, col, "".join(chars))

    def _scan_operator_or_delimiter(self):
        line, col = self.line, self.column
        two = self._peek() + self._peek(1)
        if two in TWO_CHAR_OPERATORS:                 # try the longest match first
            self._advance()
            self._advance()
            self._add(TWO_CHAR_OPERATORS[two], two, line, col)
            return
        ch = self._peek()
        if ch in SINGLE_CHAR_TOKENS:
            self._advance()
            self._add(SINGLE_CHAR_TOKENS[ch], ch, line, col)
            return
        self._advance()
        hint = f" (did you mean '{ch * 2}'?)" if ch in "&|" else ""
        self._error(f"unexpected character {ch!r}{hint}", line, col)

    # ---------- main loop ----------

    def tokenize(self):
        """Scan the whole source. Returns the token list (ending with EOF)."""
        while True:
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                break
            ch = self._peek()
            if ch.isalpha() or ch == "_":
                self._scan_word()
            elif ch.isdigit():
                self._scan_number()
            elif ch == '"':
                self._scan_string()
            else:
                self._scan_operator_or_delimiter()
        self._add(TokenType.EOF, "", self.line, self.column)
        return self.tokens


def tokenize(source):
    """Convenience wrapper: returns (tokens, errors)."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    return tokens, lexer.errors


if __name__ == "__main__":
    # Usage: python -m codeforge.lexer examples/sample1.c
    if len(sys.argv) != 2:
        print("usage: python -m codeforge.lexer <file.c>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        toks, errs = tokenize(f.read())
    for t in toks:
        print(t)
    for e in errs:
        print(e)
    sys.exit(1 if errs else 0)
