import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from envcheck import compare, exit_code, parse_env  # noqa: E402

EXAMPLE = "DB_URL=\nAPI_KEY=\nSECRET=\n"


class EnvCheckTests(unittest.TestCase):
    def test_parse_handles_quotes_comments_and_export(self):
        values, dupes, invalid = parse_env(
            '# comment\nexport A="x y"\nB=val # note\nC=\n'
        )
        self.assertEqual(values, {"A": "x y", "B": "val", "C": ""})
        self.assertEqual(dupes, [])
        self.assertEqual(invalid, [])

    def test_missing_extra_empty(self):
        report = compare("DB_URL=postgres://x\nSECRET=\nOLD=1\n", EXAMPLE)
        self.assertEqual(report["missing"], ["API_KEY"])
        self.assertEqual(report["extra"], ["OLD"])
        self.assertEqual(report["empty"], ["SECRET"])

    def test_duplicates_and_invalid(self):
        report = compare("DB_URL=1\nDB_URL=2\nthis is bad\nAPI_KEY=a\nSECRET=s\n", EXAMPLE)
        self.assertEqual(report["duplicates"], ["DB_URL"])
        self.assertEqual(report["invalid"], [3])

    def test_exit_codes(self):
        clean = compare("DB_URL=1\nAPI_KEY=2\nSECRET=3\n", EXAMPLE)
        self.assertEqual(exit_code(clean, strict=True), 0)
        missing = compare("DB_URL=1\n", EXAMPLE)
        self.assertEqual(exit_code(missing, strict=False), 1)
        extra = compare("DB_URL=1\nAPI_KEY=2\nSECRET=3\nEXTRA=4\n", EXAMPLE)
        self.assertEqual(exit_code(extra, strict=False), 0)
        self.assertEqual(exit_code(extra, strict=True), 1)


if __name__ == "__main__":
    unittest.main()
