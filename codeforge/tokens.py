"""Token definitions for the supported subset of C."""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Keywords
    INT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    PRINTF = auto()

    # Names and literals
    IDENTIFIER = auto()
    INT_CONST = auto()
    STRING = auto()

    # Arithmetic operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    # Assignment
    ASSIGN = auto()

    # Relational operators
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    SEMICOLON = auto()
    COMMA = auto()

    # End of input
    EOF = auto()


# Reserved words: if the scanner reads one of these, it is NOT an identifier.
KEYWORDS = {
    "int": TokenType.INT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "return": TokenType.RETURN,
    "printf": TokenType.PRINTF,
}

# Operators made of two characters. Checked BEFORE single-character ones
# so that "<=" is read as one token instead of "<" followed by "=".
TWO_CHAR_OPERATORS = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LE,
    ">=": TokenType.GE,
    "&&": TokenType.AND,
    "||": TokenType.OR,
}

SINGLE_CHAR_TOKENS = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "=": TokenType.ASSIGN,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "!": TokenType.NOT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,
}


@dataclass(frozen=True)
class Token:
    """One token: its category, the matched text, and where it was found."""

    type: TokenType
    lexeme: str      # the exact text from the source, e.g. "while" or "42"
    line: int
    column: int
    value: object = None   # decoded value: int for INT_CONST, str for STRING

    def __str__(self):
        return f"{self.line}:{self.column:<3} {self.type.name:<11} {self.lexeme!r}"
