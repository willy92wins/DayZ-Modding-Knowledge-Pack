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

AGY_TSV = ("Gemini Models\t5h Limit Remaining\t50%\t2026-11-05T18:00:00Z\n"
           "Gemini Models\tWeekly Limit Remaining\t76%\t2026-11-11T14:56:58Z\n")


class UsageContracts(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.cache_path = Path(folder) / "tablero-cupos" / "agy-usage.json"
        self.enterContext(patch.dict(os.environ, {"LOCALAPPDATA": folder}))
        self.now = usage.parse_utc("2026-11-05T14:00:00Z").timestamp()
        self.clock = self.enterContext(patch("time.time", return_value=self.now))

    def seed_agy_cache(self, cached_at=None):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps({
            "lines": AGY_TSV.splitlines(),
            "cached_at": self.now if cached_at is None else cached_at,
        }), encoding="utf-8")

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

    def test_agy_missing_cache_then_reuses_raw_tsv(self):
        completed = subprocess.CompletedProcess([], 0, AGY_TSV, "")
        with patch.object(usage.subprocess, "run", return_value=completed) as run:
            fresh = usage.read_antigravity()
            cached = usage.read_antigravity()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-2:], ["-p", "/usage"])
        self.assertFalse(fresh["stale"])
        self.assertTrue(cached["stale"])
        self.assertEqual(fresh["cached_at"], self.now)
        self.assertEqual(cached["cached_at"], self.now)
        self.assertEqual(cached["limits"], fresh["limits"])
        self.assertEqual(json.loads(self.cache_path.read_text(encoding="utf-8")), {
            "lines": AGY_TSV.splitlines(), "cached_at": self.now,
        })
        with contextlib.redirect_stdout(io.StringIO()) as output:
            usage.print_block("Antigravity", {"ok": True, **cached})
        self.assertIn("STALE (lectura 15:00 Madrid)", output.getvalue())

    def test_agy_today_cache_does_not_call_subprocess(self):
        self.seed_agy_cache(self.now - 60)
        before = self.cache_path.read_bytes()
        with patch.object(usage.subprocess, "run") as run:
            result = usage.read_antigravity()
        run.assert_not_called()
        self.assertTrue(result["stale"])
        self.assertEqual(self.cache_path.read_bytes(), before)

    def test_agy_new_madrid_day_refreshes_before_24h(self):
        for now, previous in (("2026-11-05T23:05:00Z", "2026-11-05T22:55:00Z"),
                              ("2026-07-05T22:05:00Z", "2026-07-05T21:55:00Z")):
            with self.subTest(now=now):
                self.clock.return_value = usage.parse_utc(now).timestamp()
                self.seed_agy_cache(usage.parse_utc(previous).timestamp())
                with patch.object(usage.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 0, AGY_TSV, "")) as run:
                    result = usage.read_antigravity()
                run.assert_called_once()
                self.assertFalse(result["stale"])

    def test_agy_same_madrid_day_reuses_across_utc_midnight(self):
        self.clock.return_value = usage.parse_utc("2026-11-06T00:05:00Z").timestamp()
        self.seed_agy_cache(usage.parse_utc("2026-11-05T23:55:00Z").timestamp())
        with patch.object(usage.subprocess, "run") as run:
            result = usage.read_antigravity()
        run.assert_not_called()
        self.assertTrue(result["stale"])

    def test_agy_24h_boundary_on_25_hour_madrid_day(self):
        cached_at = usage.parse_utc("2026-10-24T22:05:00Z").timestamp()
        for age, calls in ((86400, 0), (86401, 1)):
            with self.subTest(age=age):
                self.clock.return_value = cached_at + age
                self.seed_agy_cache(cached_at)
                with patch.object(usage.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 0, AGY_TSV, "")) as run:
                    result = usage.read_antigravity()
                self.assertEqual(run.call_count, calls)
                self.assertEqual(result["stale"], not calls)

    def test_agy_force_refresh_bypasses_today_cache(self):
        self.seed_agy_cache(self.now - 60)
        with patch.object(usage.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, AGY_TSV, "")) as run:
            result = usage.read_antigravity(refresh=True)
        run.assert_called_once()
        self.assertFalse(result["stale"])
        self.assertEqual(result["cached_at"], self.now)

    def test_agy_failed_refresh_preserves_good_cache(self):
        failures = (subprocess.CompletedProcess([], 2, "", "private diagnostic"),
                    subprocess.TimeoutExpired("private diagnostic", 90),
                    FileNotFoundError("private diagnostic"), PermissionError("private diagnostic"),
                    subprocess.CompletedProcess([], 0, "", ""),
                    subprocess.CompletedProcess([], 0, "invalid TSV", ""))
        for failure in failures:
            for force in (False, True):
                with self.subTest(failure=failure, force=force):
                    stamp = self.now - (60 if force else 2 * 86400)
                    self.seed_agy_cache(stamp)
                    before = self.cache_path.read_bytes()
                    kwargs = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
                    with patch.object(usage.subprocess, "run", **kwargs) as run:
                        result = usage.read_antigravity(refresh=force)
                    run.assert_called_once()
                    self.assertTrue(result["stale"])
                    self.assertEqual(result["cached_at"], stamp)
                    self.assertEqual(result["limits"][0]["remaining_percent"], 50)
                    self.assertEqual(self.cache_path.read_bytes(), before)

    def test_agy_failure_without_cache_does_not_create_one(self):
        for completed in (subprocess.CompletedProcess([], 2, "", "private diagnostic"),
                          subprocess.CompletedProcess([], 0, "invalid TSV", "")):
            with self.subTest(completed=completed), \
                 patch.object(usage.subprocess, "run", return_value=completed):
                result = usage.safe_read(usage.read_antigravity)
            self.assertFalse(result["ok"])
            self.assertFalse(self.cache_path.exists())

    def test_agy_invalid_cache_is_refetched(self):
        for text in ("{partial", "[]", '{"lines":[],"cached_at":1}',
                     '{"lines":[1],"cached_at":1}',
                     json.dumps({"lines": AGY_TSV.splitlines(), "cached_at": "bad"}),
                     json.dumps({"lines": AGY_TSV.splitlines(), "cached_at": 1e100})):
            with self.subTest(text=text):
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(text, encoding="utf-8")
                with patch.object(usage.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 0, AGY_TSV, "")) as run:
                    result = usage.read_antigravity()
                run.assert_called_once()
                self.assertFalse(result["stale"])

    def test_agy_cache_write_failure_keeps_fresh_reading_and_old_cache(self):
        self.seed_agy_cache(self.now - 60)
        before = self.cache_path.read_bytes()
        with patch.object(usage.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, AGY_TSV, "")), \
             patch.object(usage.os, "replace", side_effect=PermissionError("private diagnostic")):
            result = usage.read_antigravity(refresh=True)
        self.assertFalse(result["stale"])
        self.assertEqual(self.cache_path.read_bytes(), before)
        self.assertEqual(list(self.cache_path.parent.iterdir()), [self.cache_path])

    def test_agy_json_metadata_and_refresh_flag(self):
        self.seed_agy_cache(self.now - 60)
        with patch.object(usage, "read_codex", return_value={}), \
             patch.object(usage, "read_muse", return_value={}), \
             patch.object(usage.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, AGY_TSV, "")) as run:
            for args, stale in ((["--json", "--refresh-agy"], False), (["--json"], True)):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(usage.main(args), 0)
                data = json.loads(output.getvalue())["antigravity"]
                self.assertTrue(data["ok"])
                self.assertEqual(data["stale"], stale)
                self.assertEqual(data["cached_at"], self.now)
        run.assert_called_once()

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
        self.assertFalse(result["antigravity"]["stale"])
        self.assertIsNone(result["antigravity"]["cached_at"])
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
