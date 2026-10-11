import unittest

from codeforge.lexer import tokenize
from codeforge.tokens import TokenType as T


def types(source):
    toks, errs = tokenize(source)
    return [t.type for t in toks], errs


class LexerTests(unittest.TestCase):
    def test_declaration(self):
        got, errs = types("int x = 5;")
        self.assertEqual(got, [T.INT, T.IDENTIFIER, T.ASSIGN, T.INT_CONST, T.SEMICOLON, T.EOF])
        self.assertEqual(errs, [])

    def test_keywords_vs_identifiers(self):
        got, _ = types("while whiles if iffy")
        self.assertEqual(got, [T.WHILE, T.IDENTIFIER, T.IF, T.IDENTIFIER, T.EOF])

    def test_two_char_operators(self):
        got, _ = types("== != <= >= < > =")
        self.assertEqual(got, [T.EQ, T.NEQ, T.LE, T.GE, T.LT, T.GT, T.ASSIGN, T.EOF])

    def test_arithmetic_and_parentheses(self):
        got, _ = types("(a + b) * c / d % e - f")
        self.assertEqual(got, [
            T.LPAREN, T.IDENTIFIER, T.PLUS, T.IDENTIFIER, T.RPAREN, T.STAR,
            T.IDENTIFIER, T.SLASH, T.IDENTIFIER, T.PERCENT, T.IDENTIFIER,
            T.MINUS, T.IDENTIFIER, T.EOF])

    def test_integer_value(self):
        toks, _ = tokenize("42")
        self.assertEqual(toks[0].value, 42)

    def test_comments_are_skipped(self):
        got, errs = types("a // line\n/* block\n comment */ b")
        self.assertEqual(got, [T.IDENTIFIER, T.IDENTIFIER, T.EOF])
        self.assertEqual(errs, [])

    def test_string_with_escape(self):
        toks, errs = tokenize('printf("hi %d\\n", x);')
        self.assertEqual(errs, [])
        string_tok = [t for t in toks if t.type == T.STRING][0]
        self.assertEqual(string_tok.value, "hi %d\n")

    def test_line_and_column_tracking(self):
        toks, _ = tokenize("int a;\n  int b;")
        second_int = [t for t in toks if t.type == T.INT][1]
        self.assertEqual((second_int.line, second_int.column), (2, 3))

    def test_invalid_character(self):
        got, errs = types("int a = 3 @ 4;")
        self.assertEqual(len(errs), 1)
        self.assertIn("unexpected character '@'", errs[0].message)
        self.assertEqual(errs[0].phase, "lexical")
        self.assertEqual((errs[0].line, errs[0].column), (1, 11))
        # scanning continues after the error
        self.assertIn(T.SEMICOLON, got)

    def test_multiple_errors_reported(self):
        _, errs = types("int a = 1 $ 2 # 3;")
        self.assertEqual(len(errs), 2)

    def test_unterminated_string(self):
        _, errs = types('printf("oops);')
        self.assertEqual(len(errs), 1)
        self.assertIn("unterminated string", errs[0].message)

    def test_unterminated_comment(self):
        _, errs = types("int a; /* never closed")
        self.assertEqual(len(errs), 1)
        self.assertIn("unterminated comment", errs[0].message)

    def test_bad_number(self):
        _, errs = types("int a = 12abc;")
        self.assertEqual(len(errs), 1)
        self.assertIn("12abc", errs[0].message)

    def test_empty_input(self):
        got, errs = types("")
        self.assertEqual(got, [T.EOF])
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()