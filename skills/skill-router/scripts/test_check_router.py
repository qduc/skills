import json
import tempfile
import unittest
from pathlib import Path

from check_router import check

EXITS = "Exits: `none` and `gap`. "
NONE_CASE = {"id": 0, "expected_exit": "none"}


def make(root: Path, skills: list[str], router_body: str, evals=None) -> None:
    for s in skills:
        (root / s).mkdir()
        (root / s / "SKILL.md").write_text("---\nname: x\n---\n")
    router = root / "skill-router"
    (router / "evals").mkdir(parents=True)
    (router / "SKILL.md").write_text(EXITS + router_body)
    cases = [NONE_CASE] + (evals or [])
    (router / "evals" / "evals.json").write_text(json.dumps({"evals": cases}))


class CheckRouterTest(unittest.TestCase):
    def run_check(self, skills, body, evals=None):
        with tempfile.TemporaryDirectory() as d:
            make(Path(d), skills, body, evals)
            return check(Path(d))

    def test_passes_when_every_skill_is_named(self):
        self.assertEqual(self.run_check(["debugging", "testing"], "Use `debugging` or `testing`."), [])

    def test_fails_on_skill_missing_from_router(self):
        self.assertEqual(self.run_check(["debugging", "profiling"], "Use `debugging`."),
                         ["missing from router: profiling"])

    def test_fails_on_router_naming_unknown_skill(self):
        self.assertEqual(self.run_check(["debugging"], "Use `debugging` or `old-skill`."),
                         ["router names unknown skill: old-skill"])

    def test_ignores_paths_and_directories_without_skill_md(self):
        with tempfile.TemporaryDirectory() as d:
            make(Path(d), ["debugging"], "Run `scripts/check_router.py`; use `debugging`.")
            (Path(d) / "notes").mkdir()
            self.assertEqual(check(Path(d)), [])

    def test_fails_when_builtin_exit_is_undefined(self):
        with tempfile.TemporaryDirectory() as d:
            make(Path(d), ["debugging"], "Use `debugging`.")
            md = Path(d) / "skill-router" / "SKILL.md"
            md.write_text(md.read_text().replace("`gap`", "gap"))
            self.assertEqual(check(Path(d)), ["router does not define exit: gap"])

    def test_accepts_chain_and_builtin_eval_exits(self):
        evals = [{"id": 1, "expected_exit": "debugging → testing"},
                 {"id": 2, "expected_exit": "gap"}]
        self.assertEqual(self.run_check(["debugging", "testing"], "`debugging` `testing`", evals), [])

    def test_fails_on_eval_exit_that_is_not_real(self):
        evals = [{"id": 1, "expected_exit": "debuging"},
                 {"id": 2, "expected_exit": "debugging → testing → debugging"}]
        self.assertEqual(self.run_check(["debugging", "testing"], "`debugging` `testing`", evals),
                         ["eval 1: invalid expected_exit: 'debuging'",
                          "eval 2: invalid expected_exit: 'debugging → testing → debugging'"])

    def test_fails_when_fast_exit_is_untested(self):
        with tempfile.TemporaryDirectory() as d:
            make(Path(d), ["debugging"], "`debugging`")
            ev = Path(d) / "skill-router" / "evals" / "evals.json"
            ev.write_text(json.dumps({"evals": [{"id": 1, "expected_exit": "debugging"}]}))
            self.assertEqual(check(Path(d)), ["evals have no `none` case"])

    def test_fails_when_route_row_exit_has_no_eval(self):
        body = ("\n## Route\n\n| The step needs to... | Exit |\n| --- | --- |\n"
                "| Explain a failure | `debugging` | `testing` is not this |\n"
                "| Prove behavior | `testing` (then `debugging`) |\n\n## After\n`debugging`")
        self.assertEqual(self.run_check(["debugging", "testing"], body,
                                        [{"id": 1, "expected_exit": "debugging"}]),
                         ["route exit has no eval: testing"])

    def test_chain_eval_covers_its_first_skill(self):
        body = "\n## Route\n\n| Situation | Exit |\n| --- | --- |\n| Fuzzy | `debugging` → `testing` |\n"
        self.assertEqual(self.run_check(["debugging", "testing"], body,
                                        [{"id": 1, "expected_exit": "debugging → testing"}]), [])

    def test_fails_on_also_ok_exit_that_is_not_real(self):
        evals = [{"id": 1, "expected_exit": "debugging", "also_ok": ["debuging"]}]
        self.assertEqual(self.run_check(["debugging"], "`debugging`", evals),
                         ["eval 1: invalid also_ok: 'debuging'"])

    def test_repository_router_is_current(self):
        self.assertEqual(check(Path(__file__).resolve().parents[2]), [])


if __name__ == "__main__":
    unittest.main()
