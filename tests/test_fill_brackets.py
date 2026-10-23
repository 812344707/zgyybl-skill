"""Fictional text only; verify character preservation and CLI failure behavior."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fill_brackets.py"
SPEC = importlib.util.spec_from_file_location("fill_brackets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BracketCompletionTests(unittest.TestCase):
    def test_ordered_occurrences_remain_distinct(self):
        self.assertEqual(
            MODULE.fill_brackets("左：[]；右：[]。", ["3天", "1天"]),
            "左：[3天]；右：[1天]。",
        )

    def test_missing_clinical_data_is_not_a_normal_finding(self):
        self.assertEqual(
            MODULE.fill_brackets("过敏史：[过敏史]。查体：[]。", [None, "  "]),
            "过敏史：[待补充]。查体：[待补充]。",
        )

    def test_original_text_is_frozen_including_formatting(self):
        self.assertEqual(
            MODULE.fill_brackets(
                "2026/10/22\t9:05\r\n1. BP[]mmHg  \r\n\r\nTHA拟行。\n",
                ["120/80"],
            ),
            "2026/10/22\t9:05\r\n1. BP[120/80]mmHg  \r\n\r\nTHA拟行。\n",
        )

    def test_literal_ranges_and_citations_survive_bracket_removal(self):
        self.assertEqual(
            MODULE.fill_brackets(
                "疼痛[]；原量表[0,10]；原引用[2]。",
                ["3天", {"preserve": True}, {"preserve": True}],
                keep_brackets=False,
            ),
            "疼痛3天；原量表[0,10]；原引用[2]。",
        )

    def test_no_placeholders_returns_original(self):
        self.assertEqual(MODULE.fill_brackets("原文\r\n", []), "原文\r\n")
        self.assertEqual(MODULE.fill_brackets("", []), "")

    def test_count_mismatch_is_rejected(self):
        for fills in ([], ["一", "二"]):
            with self.subTest(fills=fills), self.assertRaises(ValueError):
                MODULE.fill_brackets("[]", fills)

    def test_ambiguous_brackets_are_rejected(self):
        for template in ("未闭合[", "未打开]", "[嵌套[]]"):
            with self.subTest(template=template), self.assertRaises(ValueError):
                MODULE.fill_brackets(template, [])

    def test_invalid_values_are_rejected(self):
        for value in (120, False, [], {"preserve": 1}, {"preserve": True, "x": 1}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.fill_brackets("[]", [value])
        with self.assertRaises(ValueError):
            MODULE.fill_brackets("[]", ["有效"], keep_brackets="false")

    def run_cli(self, payload):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_outputs_exact_bytes_without_appended_newline(self):
        result = self.run_cli({"template": "  虚构病例：[]\r\n\t", "fills": ["右膝疼痛"]})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "  虚构病例：[右膝疼痛]\r\n\t".encode("utf-8"))
        self.assertEqual(result.stderr, b"")

    def test_cli_fails_without_partial_or_explanatory_stdout(self):
        payloads = (
            {"template": "[]和[]", "fills": ["唯一值"]},
            {"template": "[]", "fills": ["值"], "unknown": True},
            {"template": "[]"},
            [],
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.run_cli(payload)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main()
