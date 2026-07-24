#!/usr/bin/env python3
"""Offline fixtures for drive_ladder.run_ladder (no daemon, no game).

A FakeDaemon feeds synthetic verb payloads through the rung logic and asserts the verdict. These
fixtures prove the R21 (Codex 2026-06-28) hardening DL-001..006 WITHOUT burning an in-game cycle:
  - R3 false-PASS when only the passenger seat is available (DL-001)
  - R4 false-PASS when seated but not owner / not fixture-ready (DL-002)
  - re-run measures the OLD car when the player is already seated (DL-003)
  - R5 false-PASS by gravity/inertia with the engine off (DL-004)
  - R5 ambiguous obstacle/drivetrain -> needs_clear_ground_retest, not a one-shot fix (DL-005)
  - a verb timeout in R5 -> inconclusive, not a model fix (DL-006)

Run:  python test_drive_ladder.py    (exit 0 = all pass)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_ladder  # noqa: E402

# Speed: no real waiting. run_ladder/wait_ready use module-level time.sleep.
drive_ladder.time.sleep = lambda *a, **k: None


class FakeDaemon:
    """`.run(cmd, args, timeout)` -> scripted dict. A script value is a dict (fixed), a list
    (consumed in order, clamped to the last), or a callable(args, call_index)."""

    def __init__(self, scripts: dict):
        self.scripts = scripts
        self.calls: dict = {}

    def run(self, cmd: str, args: dict, timeout: float = 30.0) -> dict:
        n = self.calls.get(cmd, 0)
        self.calls[cmd] = n + 1
        s = self.scripts.get(cmd)
        if callable(s):
            return s(args, n)
        if isinstance(s, list):
            return s[min(n, len(s) - 1)] if s else {"ok": True}
        if s is None:
            return {"ok": True}
        return s


def mkargs(**over):
    base = dict(vehicle="TEST_CAR", rotation=0, journal="", drive_s=0.0, hold_ttl=12.0,
                steer_left_sign=-1.0, port=8765, keyfile="")
    base.update(over)
    return argparse.Namespace(**base)


def raycast_ring(args, n):
    # Always hit; alternate two components so ring_components collects a driver (10) + passenger (11).
    return {"raycast": {"hit": True, "component": 10 if (n % 2 == 0) else 11}}


def getin_responder(driver_available, driver_block, passenger_available=True):
    def resp(args, n):
        comp = args.get("component", -1)
        if comp == -1:
            return {"get_in": {"partial": True, "crew_size": 2, "first_block": "no_component"}}
        if comp == 10:  # driver seat, crew_index 0
            return {"get_in": {"component_crew_index": 0, "available": driver_available,
                               "first_block": driver_block}}
        # passenger seat, crew_index 1
        return {"get_in": {"component_crew_index": 1, "available": passenger_available, "first_block": ""}}
    return resp


def base_scripts(**over):
    s = {
        "query_player_state": {"ok": True, "pos": [100.0, 0.0, 100.0]},
        "world_spawn": {"ok": True, "found": True, "pos": [100.0, 0.0, 100.0]},
        "scene_raycast": raycast_ring,
        "query_get_in_condition": getin_responder(driver_available=True, driver_block=""),
        "vehicle_get_in_client": {"ok": True, "seated": True, "is_owner": True, "vehicle_fixture_ready": True},
        "engine_set": {"ok": True, "engine_on_server": True},
        "vehicle_control": {"ok": True},
        "vehicle_release": {"ok": True},
        # [preflight=not_seated, R5 t0 @spawn, R5 t1 moved+fast, R6 pa, pb, pc]
        "vehicle_telemetry": [
            {"ok": False, "error": "not_seated"},
            {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 40.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [133.0, 0.0, 100.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [135.0, 0.0, 103.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
        ],
    }
    s.update(over)
    return s


def run(scripts, **argover):
    return drive_ladder.run_ladder(FakeDaemon(scripts), mkargs(**argover))


FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILURES.append(f"{name}: {detail}")
    print(f"  [{status}] {name}" + (f" -- {detail}" if (not cond and detail) else ""))


def rung(R, key):
    return R["rungs"].get(key, {})


def test_happy():
    print("scenario: HAPPY (all objective rungs PASS)")
    R = run(base_scripts())
    check("R1 PASS", rung(R, "R1").get("PASS") is True)
    check("R2_collision PASS", rung(R, "R2_collision").get("PASS") is True)
    check("R3 PASS (driver available)", rung(R, "R3").get("PASS") is True)
    check("R4 PASS", rung(R, "R4").get("PASS") is True)
    check("R5 PASS", rung(R, "R5").get("PASS") is True, str(rung(R, "R5")))
    check("objective_PASS True", drive_ladder.run_ladder and R.get("stop") is None)
    # objective_PASS is set in write_verdict; recompute the same way here
    obj = [v.get("PASS") for v in R["rungs"].values() if v.get("PASS") is not None]
    check("objective all True", bool(obj) and all(obj))


def test_r3_passenger_only():
    print("scenario: DL-001 R3 passenger-only (driver unreachable)")
    sc = base_scripts(query_get_in_condition=getin_responder(driver_available=False, driver_block="unreachable",
                                                             passenger_available=True))
    R = run(sc)
    check("R3 NOT PASS", rung(R, "R3").get("PASS") is False, str(rung(R, "R3")))
    ds = rung(R, "R3").get("driver_seat") or {}
    check("driver_seat first_block=unreachable", ds.get("first_block") == "unreachable", str(ds))
    obj = [v.get("PASS") for v in R["rungs"].values() if v.get("PASS") is not None]
    check("objective_PASS False", not (bool(obj) and all(obj)))


def test_r4_seated_no_owner():
    print("scenario: DL-002 R4 seated but not owner")
    sc = base_scripts(vehicle_get_in_client={"ok": True, "seated": True, "is_owner": False, "vehicle_fixture_ready": True})
    R = run(sc)
    check("R4 NOT PASS", rung(R, "R4").get("PASS") is False, str(rung(R, "R4")))
    check("stop == R4", R.get("stop") == "R4", str(R.get("stop")))
    check("R5 not run", "R5" not in R["rungs"])


def test_r4_no_fixture():
    print("scenario: DL-002 R4 seated+owner but fixture not ready")
    sc = base_scripts(vehicle_get_in_client={"ok": True, "seated": True, "is_owner": True, "vehicle_fixture_ready": False})
    R = run(sc)
    check("R4 NOT PASS", rung(R, "R4").get("PASS") is False, str(rung(R, "R4")))
    check("stop == R4", R.get("stop") == "R4")


def test_rerun_already_in_vehicle():
    print("scenario: DL-003 re-run, player already seated")
    sc = base_scripts(vehicle_telemetry=[
        {"ok": True, "pos_real": [50.0, 0.0, 50.0], "speedo_max": 0.0, "engine_on_server": False, "is_owner": True},
    ])
    R = run(sc)
    check("stop == preflight", R.get("stop") == "preflight", str(R.get("stop")))
    check("preflight NOT PASS", rung(R, "preflight").get("PASS") is False)
    check("R1 not run", "R1" not in R["rungs"])


def test_r5_engine_off_moving():
    print("scenario: DL-004 R5 moves with engine OFF (gravity/inertia)")
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": False, "is_owner": True},
        {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 40.0, "gear": 1, "engine_on_server": False, "is_owner": True},
    ])
    R = run(sc)
    check("R5 NOT PASS (engine off)", rung(R, "R5").get("PASS") is False, str(rung(R, "R5")))
    fixtext = " ".join(f["fix"] for f in R["fixes"] if f["rung"] == "R5")
    check("R5 fix cites engine, not drivetrain", "engine" in fixtext.lower(), fixtext)


def test_r5_blocked_retest():
    print("scenario: DL-005 R5 engine+owner but no motion -> needs_clear_ground_retest")
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
        {"ok": True, "pos_real": [100.1, 0.0, 100.0], "speedo_max": 0.2, "gear": 1, "engine_on_server": True, "is_owner": True},
    ])
    R = run(sc)
    check("R5 NOT PASS", rung(R, "R5").get("PASS") is False)
    check("R5 verdict needs_clear_ground_retest", rung(R, "R5").get("verdict") == "needs_clear_ground_retest", str(rung(R, "R5")))


def test_r5_timeout():
    print("scenario: DL-006 a verb times out in R5 -> inconclusive")
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
        {"_timeout": True},
    ])
    R = run(sc)
    check("R5 NOT PASS", rung(R, "R5").get("PASS") is False)
    check("R5 inconclusive", rung(R, "R5").get("inconclusive") is True, str(rung(R, "R5")))


def test_r1_found_failclosed():
    print("scenario: DL-010 world_spawn omits `found` -> R1 fail-closed")
    sc = base_scripts(world_spawn={"ok": True, "pos": [100.0, 0.0, 100.0]})  # no 'found'
    R = run(sc)
    check("R1 NOT PASS (found absent)", rung(R, "R1").get("PASS") is False, str(rung(R, "R1")))
    check("stop == R1", R.get("stop") == "R1")


def main() -> int:
    for t in (test_happy, test_r3_passenger_only, test_r4_seated_no_owner, test_r4_no_fixture,
              test_rerun_already_in_vehicle, test_r5_engine_off_moving, test_r5_blocked_retest,
              test_r5_timeout, test_r1_found_failclosed):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("ALL FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
