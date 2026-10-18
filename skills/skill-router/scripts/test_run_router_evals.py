import io
import unittest
from contextlib import redirect_stdout

from run_router_evals import evaluate, normalize, parse, report

CASES = [{"id": 1, "prompt": "fixed it", "expected_exit": "bug-retro"},
         {"id": 2, "prompt": "fuzzy build", "expected_exit": "risk-first-build → agentic-loop"}]


class ParseTest(unittest.TestCase):
    def test_takes_last_exit_line_and_normalizes(self):
        self.assertEqual(parse("thinking\nEXIT: `debugging`.\n"), "debugging")
        self.assertEqual(parse("EXIT: none\nEXIT: chain a -> b"), "a → b")
        self.assertEqual(parse("no answer"), "?")

    def test_normalize_matches_arrow_styles(self):
        self.assertEqual(normalize("a->b"), normalize("a → b"))


class EvaluateTest(unittest.TestCase):
    def run_report(self, answers, runs=1):
        def fake(system, prompt):
            self.assertIn("ROUTER", system)
            return answers[prompt].pop(0)
        out = io.StringIO()
        with redirect_stdout(out):
            code = report(evaluate(CASES, "## Route", fake, runs=runs, jobs=1))
        return code, out.getvalue()

    def test_all_hits_pass(self):
        code, out = self.run_report({"fixed it": ["EXIT: bug-retro"],
                                     "fuzzy build": ["EXIT: risk-first-build -> agentic-loop"]})
        self.assertEqual(code, 0)
        self.assertIn("2/2", out)

    def test_shadowed_case_is_reported_with_what_won(self):
        code, out = self.run_report({"fixed it": ["EXIT: none"],
                                     "fuzzy build": ["EXIT: risk-first-build → agentic-loop"]})
        self.assertEqual(code, 1)
        self.assertIn("MISS   1 0/1  want bug-retro  got none", out)

    def test_also_ok_alternative_is_accepted(self):
        global CASES
        saved, CASES[1] = CASES[1], dict(CASES[1], also_ok=["agentic-loop"])
        try:
            code, _ = self.run_report({"fixed it": ["EXIT: bug-retro"],
                                       "fuzzy build": ["EXIT: agentic-loop"]})
        finally:
            CASES[1] = saved
        self.assertEqual(code, 0)

    def test_flaky_case_counts_as_miss(self):
        code, out = self.run_report({"fixed it": ["EXIT: bug-retro", "EXIT: none"],
                                     "fuzzy build": ["EXIT: risk-first-build → agentic-loop"] * 2},
                                    runs=2)
        self.assertEqual(code, 1)
        self.assertIn("1/2", out)


if __name__ == "__main__":
    unittest.main()
