"""Error type shared by every compiler phase."""


class CompileError:
    """One problem found in the source program.

    phase   -- which compiler phase found it ("lexical", "syntax", "semantic")
    message -- human-readable description
    line    -- 1-based line number in the source file
    column  -- 1-based column number in the source file
    """

    def __init__(self, phase, message, line, column):
        self.phase = phase
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        return f"{self.phase} error at line {self.line}, column {self.column}: {self.message}"

    def __repr__(self):
        return f"CompileError({self})"