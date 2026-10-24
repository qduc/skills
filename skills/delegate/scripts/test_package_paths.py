import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


class CoordinatorPackageTests(unittest.TestCase):
    def test_relative_markdown_links_stay_inside_package(self):
        missing = []
        escaped = []
        for document in PACKAGE.rglob("*.md"):
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                candidate = (document.parent / target.split("#", 1)[0]).resolve()
                try:
                    candidate.relative_to(PACKAGE.resolve())
                except ValueError:
                    escaped.append(f"{document}: {target}")
                else:
                    if not candidate.exists():
                        missing.append(f"{document}: {target}")
        self.assertEqual(escaped, [])
        self.assertEqual(missing, [])

if __name__ == "__main__":
    unittest.main()
