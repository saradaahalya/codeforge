import unittest

from codeforge.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def test_valid_program_has_tokens_and_no_errors(self):
        r = run_pipeline("int main() { int x = 5; return x; }")
        self.assertTrue(r["ok"])
        self.assertEqual(r["errors"], [])
        tokens = r["phases"][0]
        self.assertEqual(tokens["id"], "tokens")
        self.assertEqual(tokens["status"], "done")
        self.assertEqual(tokens["data"][0]["type"], "INT")
        self.assertEqual(tokens["data"][0]["category"], "keyword")

    def test_errors_are_reported_as_plain_dicts(self):
        r = run_pipeline("int a = 3 @ 4;")
        self.assertFalse(r["ok"])
        self.assertEqual(r["errors"][0]["phase"], "lexical")
        self.assertEqual(r["errors"][0]["line"], 1)

    def test_unfinished_phases_are_listed_as_pending(self):
        r = run_pipeline("")
        pending = [p["id"] for p in r["phases"] if p["status"] == "pending"]
        self.assertEqual(pending, ["symbols", "tac", "optimized", "assembly"])

    def test_ast_phase_is_built_for_a_valid_program(self):
        r = run_pipeline("int main() { return 2 + 3 * 4; }")
        self.assertTrue(r["ok"])
        ast = [p for p in r["phases"] if p["id"] == "ast"][0]
        self.assertEqual(ast["status"], "done")
        self.assertEqual(ast["kind"], "tree")
        self.assertEqual(ast["data"]["label"], "Program")

    def test_ast_is_skipped_after_lexical_errors(self):
        r = run_pipeline("int main() { return 1 @ 2; }")
        ast = [p for p in r["phases"] if p["id"] == "ast"][0]
        self.assertEqual(ast["status"], "skipped")
        self.assertEqual([e["phase"] for e in r["errors"]], ["lexical"])

    def test_syntax_errors_are_reported_and_ast_is_skipped(self):
        r = run_pipeline("int main() { int x = 5 return x; }")
        self.assertFalse(r["ok"])
        self.assertEqual(r["errors"][0]["phase"], "syntax")
        ast = [p for p in r["phases"] if p["id"] == "ast"][0]
        self.assertEqual(ast["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
