import unittest

from codeforge.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def test_valid_program_has_tokens_and_no_errors(self):
        r = run_pipeline("int x = 5;")
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
        self.assertEqual(pending, ["ast", "symbols", "tac", "optimized", "assembly"])


if __name__ == "__main__":
    unittest.main()