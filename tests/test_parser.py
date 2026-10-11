import random
import unittest

from codeforge import ast_nodes as A
from codeforge.lexer import tokenize
from codeforge.parser import parse


def parse_source(source):
    tokens, lex_errors = tokenize(source)
    assert not lex_errors, lex_errors
    return parse(tokens)


def body_of_main(source):
    program, errors = parse_source(source)
    assert errors == [], errors
    return program.functions[0].body.statements


def expr(source_expr):
    """Parse an expression by wrapping it in 'return ...;' and show it as prefix text."""
    stmts = body_of_main("int main() { return " + source_expr + "; }")
    return show(stmts[0].value)


def show(node):
    """Compact prefix notation, e.g. (+ 2 (* 3 4)); makes grouping visible."""
    if isinstance(node, A.IntLiteral):
        return str(node.value)
    if isinstance(node, A.Var):
        return node.name
    if isinstance(node, A.UnaryOp):
        return f"({node.op} {show(node.operand)})"
    if isinstance(node, A.BinaryOp):
        return f"({node.op} {show(node.left)} {show(node.right)})"
    if isinstance(node, A.Call):
        return "(call " + " ".join([node.name] + [show(a) for a in node.args]) + ")"
    raise AssertionError(type(node))


class PrecedenceTests(unittest.TestCase):
    def test_multiplication_binds_tighter_than_addition(self):
        self.assertEqual(expr("2 + 3 * 4"), "(+ 2 (* 3 4))")

    def test_parentheses_override_precedence(self):
        self.assertEqual(expr("(2 + 3) * 4"), "(* (+ 2 3) 4)")

    def test_subtraction_is_left_associative(self):
        self.assertEqual(expr("10 - 4 - 3"), "(- (- 10 4) 3)")

    def test_division_is_left_associative(self):
        self.assertEqual(expr("100 / 10 / 5"), "(/ (/ 100 10) 5)")

    def test_unary_minus_binds_tighter_than_multiplication(self):
        self.assertEqual(expr("-x * 2"), "(* (- x) 2)")

    def test_double_unary(self):
        self.assertEqual(expr("- -x"), "(- (- x))")
        self.assertEqual(expr("!!a"), "(! (! a))")

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(expr("a || b && c"), "(|| a (&& b c))")

    def test_relational_binds_tighter_than_equality(self):
        self.assertEqual(expr("a == b < c"), "(== a (< b c))")

    def test_arithmetic_binds_tighter_than_relational(self):
        self.assertEqual(expr("a + 1 < b * 2"), "(< (+ a 1) (* b 2))")

    def test_not_applies_to_the_parenthesized_group(self):
        self.assertEqual(expr("!(a && b) || c"), "(|| (! (&& a b)) c)")

    def test_function_call_in_expression(self):
        self.assertEqual(expr("f(1, g(2)) + 3"), "(+ (call f 1 (call g 2)) 3)")


class StatementTests(unittest.TestCase):
    def test_declarations(self):
        stmts = body_of_main("int main() { int a; int b = 5; return 0; }")
        self.assertIsInstance(stmts[0], A.VarDecl)
        self.assertIsNone(stmts[0].init)
        self.assertEqual(show(stmts[1].init), "5")

    def test_assignment(self):
        stmts = body_of_main("int main() { x = x + 1; return 0; }")
        self.assertIsInstance(stmts[0], A.Assign)
        self.assertEqual(show(stmts[0].value), "(+ x 1)")

    def test_if_else(self):
        stmts = body_of_main("int main() { if (a < b) { x = 1; } else { x = 2; } return 0; }")
        node = stmts[0]
        self.assertIsInstance(node, A.If)
        self.assertIsNotNone(node.else_branch)

    def test_dangling_else_belongs_to_nearest_if(self):
        stmts = body_of_main("int main() { if (a) if (b) x = 1; else x = 2; return 0; }")
        outer = stmts[0]
        self.assertIsNone(outer.else_branch)
        self.assertIsNotNone(outer.then_branch.else_branch)

    def test_while(self):
        stmts = body_of_main("int main() { while (n > 0) { n = n - 1; } return 0; }")
        self.assertIsInstance(stmts[0], A.While)
        self.assertEqual(show(stmts[0].condition), "(> n 0)")

    def test_printf_with_arguments(self):
        stmts = body_of_main('int main() { printf("%d %d\\n", a, b + 1); return 0; }')
        self.assertIsInstance(stmts[0], A.Printf)
        self.assertEqual(stmts[0].format, "%d %d\n")
        self.assertEqual([show(a) for a in stmts[0].args], ["a", "(+ b 1)"])

    def test_call_statement(self):
        stmts = body_of_main("int main() { foo(1, 2); return 0; }")
        self.assertIsInstance(stmts[0], A.ExprStmt)
        self.assertIsInstance(stmts[0].expr, A.Call)

    def test_nested_block(self):
        stmts = body_of_main("int main() { { int a = 1; } return 0; }")
        self.assertIsInstance(stmts[0], A.Block)


class FunctionTests(unittest.TestCase):
    def test_multiple_functions_with_parameters(self):
        program, errors = parse_source(
            "int add(int a, int b) { return a + b; }\n"
            "int main() { return add(1, 2); }")
        self.assertEqual(errors, [])
        self.assertEqual([f.name for f in program.functions], ["add", "main"])
        self.assertEqual([p.name for p in program.functions[0].params], ["a", "b"])

    def test_ast_nodes_remember_their_position(self):
        program, _ = parse_source("int main() {\n    return 1 + 2;\n}")
        ret = program.functions[0].body.statements[0]
        self.assertEqual((ret.line, ret.column), (2, 5))
        plus = ret.value
        self.assertEqual((plus.line, plus.column), (2, 14))

    def test_to_tree_shape(self):
        program, _ = parse_source("int main() { return 2 + 3 * 4; }")
        tree = A.to_tree(program)
        ret = tree["children"][0]["children"][0]["children"][0]
        self.assertEqual(ret["label"], "return")
        plus = ret["children"][0]
        self.assertEqual(plus["label"], "+")
        self.assertEqual([c["label"] for c in plus["children"]], ["2", "*"])
        self.assertEqual(plus["children"][0]["role"], "left")


class SyntaxErrorTests(unittest.TestCase):
    def errors(self, source):
        _, errs = parse_source(source)
        return errs

    def test_missing_semicolon_points_at_end_of_previous_line(self):
        errs = self.errors("int main() {\n    int x = 5\n    return x;\n}")
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0].phase, "syntax")
        self.assertEqual((errs[0].line, errs[0].column), (2, 14))
        self.assertIn("expected ';'", errs[0].message)

    def test_missing_closing_parenthesis(self):
        errs = self.errors("int main() { int y = (1 + 2; return y; }")
        self.assertEqual(len(errs), 1)
        self.assertIn("expected ')'", errs[0].message)

    def test_missing_expression(self):
        errs = self.errors("int main() { x = ; return 0; }")
        self.assertEqual(len(errs), 1)
        self.assertIn("expected an expression", errs[0].message)

    def test_several_errors_in_one_run(self):
        errs = self.errors("int main() {\n int a = 1\n int b = (2;\n x = ;\n return 0;\n}")
        self.assertEqual([e.line for e in errs], [2, 3, 4])

    def test_recovery_still_checks_later_functions(self):
        errs = self.errors("int f() { int a = ; return 0; }\nint g() { int b = 2 return b; }")
        self.assertEqual(len(errs), 2)

    def test_missing_closing_brace(self):
        errs = self.errors("int main() { return 0;")
        self.assertEqual(len(errs), 1)
        self.assertIn("expected '}'", errs[0].message)
        self.assertIn("end of input", errs[0].message)

    def test_stray_text_at_top_level(self):
        errs = self.errors("x = 5;\nint main() { return 0; }")
        self.assertEqual(len(errs), 1)
        self.assertIn("function definition", errs[0].message)

    def test_empty_program(self):
        errs = self.errors("")
        self.assertEqual(len(errs), 1)
        self.assertIn("empty", errs[0].message)

    def test_declaration_with_two_names_is_rejected(self):
        errs = self.errors("int main() { int a, b; return 0; }")
        self.assertEqual(len(errs), 1)
        self.assertIn("expected ';'", errs[0].message)

    def test_else_without_if(self):
        errs = self.errors("int main() { else { } return 0; }")
        self.assertTrue(errs)

    def test_very_deep_nesting_does_not_crash(self):
        src = "int main() { return " + "(" * 2000 + "1" + ")" * 2000 + "; }"
        _, errs = parse_source(src)       # must return, not raise RecursionError
        self.assertTrue(errs)


class RobustnessTests(unittest.TestCase):
    def test_garbage_input_always_terminates(self):
        """Random token soup must never hang or crash the parser."""
        pieces = ["int", "x", "main", "(", ")", "{", "}", ";", "=", "+", "1", "if",
                  "else", "while", "return", "printf", ",", '"s"', "!", "&&", "||", "-", "*"]
        rng = random.Random(42)
        for _ in range(500):
            source = " ".join(rng.choice(pieces) for _ in range(rng.randint(1, 40)))
            tokens, _ = tokenize(source)
            program, errs = parse(tokens)
            self.assertIsNotNone(program)


if __name__ == "__main__":
    unittest.main()
