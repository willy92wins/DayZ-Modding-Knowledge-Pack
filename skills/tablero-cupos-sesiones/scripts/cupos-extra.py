#!/usr/bin/env python3
"""Read Codex, Antigravity and Muse usage. Stdlib only; each source fails soft."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
try:
    MADRID = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    MADRID = None


class UsageError(Exception):
    """A short, safe diagnostic without CLI output or private paths."""


def number(value):
    if isinstance(value, bool) or value is None:
        raise UsageError("dato numerico ausente o invalido")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        raise UsageError("dato numerico invalido") from None
    if not math.isfinite(result):
        raise UsageError("dato numerico no finito")
    return result


def parse_utc(value):
    if not isinstance(value, str):
        raise UsageError("fecha UTC ausente o invalida")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(UTC)
    except ValueError:
        raise UsageError("fecha UTC invalida") from None


def madrid_time(instant):
    utc = instant.astimezone(UTC)
    zone = MADRID
    if zone is None:
        # EU rule: summer time starts/ends at 01:00 UTC on the last Sunday.
        start = datetime(utc.year, 3, 31, 1, tzinfo=UTC)
        start -= timedelta(days=(start.weekday() + 1) % 7)
        end = datetime(utc.year, 10, 31, 1, tzinfo=UTC)
        end -= timedelta(days=(end.weekday() + 1) % 7)
        zone = timezone(timedelta(hours=2 if start <= utc < end else 1))
    return utc.astimezone(zone).strftime("%Y-%m-%d %H:%M")


def epoch_madrid(value, divisor=1):
    return madrid_time(datetime.fromtimestamp(number(value) / divisor, UTC))


def profile_root():
    return Path(os.environ.get("USERPROFILE") or Path.home())


def read_codex(sessions_dir=None):
    root = Path(sessions_dir) if sessions_dir is not None else profile_root() / ".codex" / "sessions"
    candidates = []
    for path in root.rglob("*.jsonl"):
        try:
            candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for mtime, path in sorted(candidates, key=lambda item: item[0], reverse=True):
        last = None
        seen = None
        try:
            with path.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if '"rate_limits"' not in line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue  # A live rollout may end with an incomplete line.
                    if not isinstance(record, dict):
                        continue
                    payload = record.get("payload")
                    if not isinstance(payload, dict):
                        payload = record
                    limits = payload.get("rate_limits")
                    if isinstance(limits, dict) and limits:
                        last, seen = limits, record.get("timestamp")
        except OSError:
            continue
        if last is None:
            continue
        primary = last.get("primary")
        if not isinstance(primary, dict):
            raise UsageError("rate_limits.primary ausente")
        used = number(primary.get("used_percent"))
        resets = number(primary.get("resets_at"))
        credits = last.get("credits")
        credits = credits if isinstance(credits, dict) else {}
        balance = number(credits["balance"]) if credits.get("balance") is not None else None
        has_credits = credits.get("has_credits")
        status = "Cuota disponible"
        if used >= 100:
            if balance is not None and balance > 0:
                status = "NO bloqueado: tira de creditos"
            elif balance is not None or has_credits is False:
                status = "BLOQUEADO hasta reset"
            else:
                raise UsageError("cuota agotada; saldo de creditos desconocido")
        return {
            "used_percent": used,
            "resets_at": resets,
            "reset_madrid": epoch_madrid(resets),
            "credits": {"has_credits": has_credits, "balance": balance},
            "status": status,
            "asOf": madrid_time(parse_utc(seen)) if seen else epoch_madrid(mtime),
        }
    raise UsageError("ningun rollout con rate_limits")


def run_cli(command, *, timeout):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout)
    if result.returncode:
        raise UsageError(f"comando termino con codigo {result.returncode}")
    return result.stdout


def label(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 120 or any(ord(c) < 32 for c in value):
        raise UsageError("etiqueta ausente o invalida")
    return value


def parse_antigravity(output):
    limits = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 4 or not re.fullmatch(r"\d+(?:\.\d+)?%", fields[2]):
            raise UsageError("formato TSV de uso invalido")
        group, name, percent, reset = fields
        remaining = number(percent[:-1])
        if not 0 <= remaining <= 100:
            raise UsageError("porcentaje restante fuera de rango")
        limits.append({"group": label(group), "label": label(name),
                       "remaining_percent": remaining, "resets_at": reset,
                       "reset_madrid": madrid_time(parse_utc(reset))})
    if not limits:
        raise UsageError("sin limites de uso")
    return {"limits": limits}


def load_agy_cache(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
            return None
        if not all(isinstance(line, str) for line in data["lines"]):
            return None
        cached_at = number(data.get("cached_at"))
        epoch_madrid(cached_at)  # Reject epochs outside datetime's range.
        return {**parse_antigravity("\n".join(data["lines"])),
                "stale": True, "cached_at": cached_at}
    except (OSError, ValueError, OverflowError, UsageError):
        return None


def save_agy_cache(path, output, cached_at):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="agy-usage-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"lines": output.splitlines(), "cached_at": cached_at}, stream,
                      ensure_ascii=True, allow_nan=False)
        os.replace(temporary, path)
    except OSError:
        pass  # A fresh reading is still usable if the cache cannot be written.
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def read_antigravity(*, refresh=False):
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) if local else profile_root() / "AppData" / "Local"
    path = root / "tablero-cupos" / "agy-usage.json"
    cached = load_agy_cache(path)
    now = time.time()
    if cached and not refresh and now - cached["cached_at"] <= 86400:
        if epoch_madrid(cached["cached_at"])[:10] == epoch_madrid(now)[:10]:
            return cached
    exe = profile_root() / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
    try:
        output = run_cli([str(exe), "-p", "/usage"], timeout=90)
        result = parse_antigravity(output)
    except (OSError, subprocess.SubprocessError, UsageError):
        if cached:
            return cached
        raise
    cached_at = time.time()
    save_agy_cache(path, output, cached_at)
    return {**result, "stale": False, "cached_at": cached_at}


def read_muse():
    exe = profile_root() / "AppData" / "Local" / "Programs" / "muse" / "muse.cmd"
    output = run_cli([str(exe), "usage", "--json"], timeout=90)
    try:
        data = json.loads(output)
    except ValueError:
        raise UsageError("JSON de uso invalido") from None
    if not isinstance(data, dict):
        raise UsageError("datos de uso no disponibles")
    allowance = data.get("allowance", data)
    if not isinstance(allowance, dict):
        raise UsageError("datos de uso no disponibles")
    result = {"tier": label(allowance.get("tier"))}
    for name in ("window", "weekly"):
        window = allowance.get(name)
        if not isinstance(window, dict):
            raise UsageError(f"ventana {name} ausente")
        result[name] = {"usedPercent": number(window.get("usedPercent")),
                        "resetsAtMs": number(window.get("resetsAtMs")),
                        "reset_madrid": epoch_madrid(window.get("resetsAtMs"), 1000)}
    if allowance.get("asOfMs") is not None:
        result["asOfMs"] = number(allowance["asOfMs"])
        result["asOf"] = epoch_madrid(result["asOfMs"], 1000)
    else:
        result["asOf"] = madrid_time(parse_utc(allowance.get("asOf")))
    return result


def safe_read(reader):
    try:
        return {"ok": True, **reader()}
    except UsageError as error:
        reason = str(error)
    except subprocess.TimeoutExpired:
        reason = "timeout (90s)"
    except FileNotFoundError:
        reason = "comando o archivo no disponible"
    except PermissionError:
        reason = "acceso denegado"
    except Exception:
        reason = "datos no disponibles o invalidos"
    return {"ok": False, "error": reason}


def print_block(name, data):
    if not data["ok"]:
        print(f"{name}: ERROR {data['error']}")
        return
    suffix = ""
    if name == "Antigravity" and data["stale"]:
        suffix = f" STALE (lectura {epoch_madrid(data['cached_at'])[11:]} Madrid)"
    print(f"{name}:{suffix}")
    if name == "Codex":
        balance = data["credits"]["balance"]
        balance_text = f"{balance:.2f}" if balance is not None else "desconocido"
        print(f"  usado {data['used_percent']:g}% | reinicia {data['reset_madrid']} Madrid")
        print(f"  creditos extra: {balance_text}")
        print(f"  {data['status']}")
        print(f"  asOf {data['asOf']} Madrid")
    elif name == "Antigravity":
        for row in data["limits"]:
            print(f"  {row['group']} ? {row['label']}: queda {row['remaining_percent']:g}%"
                  f" ? reinicia {row['reset_madrid']} Madrid")
    else:
        print(f"  tier: {data['tier']}")
        for name in ("window", "weekly"):
            window = data[name]
            print(f"  {name}: usado {window['usedPercent']:g}%"
                  f" | reinicia {window['reset_madrid']} Madrid")
        print(f"  asOf {data['asOf']} Madrid")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="salida estructurada por proveedor")
    parser.add_argument("--refresh-agy", action="store_true", help="forzar lectura de Antigravity")
    args = parser.parse_args(argv)
    result = {"codex": safe_read(read_codex),
              "antigravity": {"stale": False, "cached_at": None,
                              **safe_read(lambda: read_antigravity(refresh=args.refresh_agy))},
              "muse": safe_read(read_muse)}
    if args.json:
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2))
    else:
        for index, (key, name) in enumerate((("codex", "Codex"), ("antigravity", "Antigravity"), ("muse", "Muse"))):
            if index:
                print()
            print_block(name, result[key])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
