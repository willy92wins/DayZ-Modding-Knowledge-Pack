"""Usage contracts and failure isolation; no installed CLI or account required."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cupos-extra.py"
SPEC = importlib.util.spec_from_file_location("cupos_extra", SCRIPT)
usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usage)


class UsageContracts(unittest.TestCase):
    def test_codex_newest_mtime_last_record_and_credit_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            nested = root / "2026" / "11"
            nested.mkdir(parents=True)
            stale = root / "rollout-old.jsonl"
            newest = nested / "rollout-new.jsonl"
            empty = root / "rollout-no-quota.jsonl"
            def event(percent, balance):
                return json.dumps({"payload": {"rate_limits": {
                    "primary": {"used_percent": percent, "resets_at": 1794238498},
                    "credits": {"has_credits": balance > 0, "balance": str(balance)},
                }}}) + "\n"
            stale.write_text(event(10, 0), encoding="utf-8")
            newest.write_text(event(30, 0) + "{partial\n" + event(100, 42.5), encoding="utf-8")
            empty.write_text('{"payload":{"rate_limits":null}}\n', encoding="utf-8")
            for path, stamp in ((stale, 1), (newest, 2), (empty, 3)):
                os.utime(path, (stamp, stamp))
            result = usage.read_codex(root)
            self.assertEqual(result["used_percent"], 100)
            self.assertEqual(result["credits"], {"has_credits": True, "balance": 42.5})
            self.assertEqual(result["status"], "NO bloqueado: tira de creditos")
            newest.write_text(event(100, 0), encoding="utf-8")
            self.assertEqual(usage.read_codex(root)["status"], "BLOQUEADO hasta reset")

    def test_codex_missing_quota_is_not_a_zero_percent_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(usage.UsageError):
                usage.read_codex(Path(folder))

    def test_codex_stops_on_newest_quota_even_if_primary_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / "old.jsonl"
            new = root / "new.jsonl"
            old.write_text(json.dumps({"payload": {"rate_limits": {
                "primary": {"used_percent": 10, "resets_at": 1794238498}}}}), encoding="utf-8")
            new.write_text('{"payload":{"rate_limits":{"primary":null}}}', encoding="utf-8")
            os.utime(old, (1, 1))
            os.utime(new, (2, 2))
            with self.assertRaises(usage.UsageError):
                usage.read_codex(root)

    def test_antigravity_remaining_and_utc_to_madrid(self):
        stdout = ("Gemini Models\tWeekly Limit Remaining\t88%\t2026-11-11T14:56:58Z\n"
                  "Gemini 4 Argon\tWeekly Limit\t0%\t2026-07-07T14:12:16Z\n")
        with patch.object(usage, "run_cli", return_value=stdout) as run:
            rows = usage.read_antigravity()["limits"]
        self.assertEqual(run.call_args.args[0][-2:], ["-p", "/usage"])
        self.assertEqual(run.call_args.kwargs["timeout"], 90)
        self.assertEqual(rows[0]["remaining_percent"], 88)
        self.assertEqual(rows[0]["reset_madrid"], "2026-11-11 15:56")
        self.assertEqual(rows[1]["remaining_percent"], 0)
        self.assertEqual(rows[1]["reset_madrid"], "2026-07-07 16:12")

    def test_antigravity_rejects_unrecognised_or_empty_data(self):
        for data in ("", "diagnostic only", "g\tl\t101%\t2026-11-05T00:00:00Z"):
            with self.subTest(data=data), patch.object(usage, "run_cli", return_value=data):
                with self.assertRaises(usage.UsageError):
                    usage.read_antigravity()

    def test_muse_real_allowance_envelope(self):
        payload = {"schemaVersion": 1, "allowance": {
            "tier": "pro", "window": {"usedPercent": 12, "resetsAtMs": 1793880000000},
            "weekly": {"usedPercent": 34, "resetsAtMs": 1793966400000},
            "asOfMs": 1793876400000, "source": "test"}, "reason": None, "hint": None}
        with patch.object(usage, "run_cli", return_value=json.dumps(payload)) as run:
            result = usage.read_muse()
        self.assertEqual(run.call_args.args[0][-2:], ["usage", "--json"])
        self.assertEqual(result["tier"], "pro")
        self.assertEqual(result["window"]["usedPercent"], 12)
        self.assertEqual(result["weekly"]["usedPercent"], 34)
        self.assertEqual(result["window"]["reset_madrid"], "2026-11-05 13:00")
        self.assertEqual(result["weekly"]["reset_madrid"], "2026-11-06 13:00")
        self.assertEqual(result["asOf"], "2026-11-05 12:00")

    def test_muse_unknown_allowance_or_nonfinite_percent_fails(self):
        for payload in ({"allowance": None}, {"allowance": {
            "tier": "pro", "window": {"usedPercent": float("nan"), "resetsAtMs": 1}}}):
            with self.subTest(payload=payload), patch.object(usage, "run_cli", return_value=json.dumps(payload)):
                with self.assertRaises(usage.UsageError):
                    usage.read_muse()

    def test_eu_dst_fallback_boundaries(self):
        expected = {
            "2026-03-29T00:59:00Z": "2026-03-29 01:59",
            "2026-03-29T01:00:00Z": "2026-03-29 03:00",
            "2026-10-25T00:59:00Z": "2026-10-25 02:59",
            "2026-10-25T01:00:00Z": "2026-10-25 02:00",
        }
        with patch.object(usage, "MADRID", None):
            for utc, madrid in expected.items():
                with self.subTest(utc=utc):
                    self.assertEqual(usage.madrid_time(usage.parse_utc(utc)), madrid)

    def test_cli_errors_do_not_echo_stderr(self):
        completed = subprocess.CompletedProcess([], 2, "private diagnostic", "private diagnostic")
        with patch.object(usage.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(usage.UsageError, "codigo 2"):
                usage.run_cli(["example"], timeout=90)

    def test_json_failure_isolation_and_exit_zero(self):
        with patch.object(usage, "read_codex", side_effect=FileNotFoundError("private diagnostic")), \
             patch.object(usage, "read_antigravity", side_effect=subprocess.TimeoutExpired("private diagnostic", 90)), \
             patch.object(usage, "read_muse", return_value={"tier": "pro"}), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = usage.main(["--json"])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertFalse(result["codex"]["ok"])
        self.assertFalse(result["antigravity"]["ok"])
        self.assertTrue(result["muse"]["ok"])
        self.assertNotIn("private diagnostic", output.getvalue())

    def test_text_errors_have_all_three_blocks_and_exit_zero(self):
        with patch.object(usage, "read_codex", side_effect=ValueError("private diagnostic")), \
             patch.object(usage, "read_antigravity", side_effect=ValueError("private diagnostic")), \
             patch.object(usage, "read_muse", side_effect=ValueError("private diagnostic")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = usage.main([])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertEqual(text.count(": ERROR "), 3)
        for name in ("Codex", "Antigravity", "Muse"):
            self.assertIn(name + ": ERROR ", text)
        self.assertNotIn("private diagnostic", text)


if __name__ == "__main__":
    unittest.main()
