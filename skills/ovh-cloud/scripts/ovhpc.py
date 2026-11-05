#!/usr/bin/env python3
"""ovhpc — OVHcloud Public Cloud on/off CLI with a credit budget guard. No deps.

Credentials (never printed): OVH_APPKEY, OVH_AppSecret, OVH_ConsumerKey from the
process env, falling back to HKCU\\Environment on Windows. OVH_ENDPOINT optional
(default https://eu.api.ovh.com/1.0).

Config: ~/.ovh-cloud/config.json (created by `init`). Log: ~/.ovh-cloud/guard.log

Commands:
  init --project ID [--region GRA11 --name devbox --flavor b3-16 --image "Windows Server 2022 Standard (Desktop)"]
  status                 instance state, IP, budget
  budget                 credit and month usage detail
  create                 first creation (hourly billing only), waits for ACTIVE
  up                     unshelve/start (refuses below the credit floor), waits for ACTIVE
  down                   shelve (stops compute billing), waits for SHELVED_OFFLOADED
  vnc                    print a one-time noVNC console URL
  guard                  unattended check for a scheduled task (see SKILL.md)
  install-guard [--minutes 15] / uninstall-guard
  new-token              request the main credential (GET /*, write on this project only),
                         store it in HKCU OVH_ConsumerKey, print the validation URL
  vm-token               request a credential that can only read+shelve this instance,
                         write the in-VM agent bundle to ~/.ovh-cloud/vm-agent/
  api METHOD /path [json-body] [--v2]
In Git Bash export MSYS_NO_PATHCONV=1, or "/me" becomes a Windows path.
"""
import datetime as dt
import hashlib, json, os, shutil, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

HOME = Path.home() / ".ovh-cloud"
CFG = HOME / "config.json"
LOG = HOME / "guard.log"
HERE = Path(__file__).resolve().parent
DEFAULTS = {
    "region": "GRA11",
    "name": "devbox",
    "flavor": "b3-16",
    "image": "Windows Server 2022 Standard (Desktop)",
    "floor_eur": 5.0,      # guard shelves and `up` refuses below this estimated remaining credit
    "vat_factor": 1.21,    # conservative: assume credit also pays VAT on usage (UNVERIFIED)
    "instance_id": None,
}
SHELVED = {"SHELVED", "SHELVED_OFFLOADED"}
OFF = {"SHUTOFF", "STOPPED", "SUSPENDED", "PAUSED"}  # all billed at full rate


# ---------------------------------------------------------------- low level
def _env(name):
    v = os.environ.get(name)
    if v:
        return v
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return None
    return None


def creds():
    names = ("OVH_APPKEY", "OVH_AppSecret", "OVH_ConsumerKey")
    vals = [_env(n) for n in names]
    if not all(vals):
        die(f"missing env vars: {[n for n, v in zip(names, vals) if not v]}")
    return vals


def base(v2=False):
    b = (_env("OVH_ENDPOINT") or "https://eu.api.ovh.com/1.0").rstrip("/")
    return b.replace("/1.0", "/v2") if v2 else b


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status, self.body = status, body


def call(method, path, body=None, v2=False, ok404=False):
    if not path.startswith("/"):
        die(f"path must start with '/': {path!r} (Git Bash? set MSYS_NO_PATHCONV=1)")
    ak, as_, ck = creds()
    url = base(v2) + path
    data = "" if body is None else (body if isinstance(body, str) else json.dumps(body))
    ts = urllib.request.urlopen(base() + "/auth/time", timeout=20).read().decode().strip()
    sig = "$1$" + hashlib.sha1("+".join([as_, ck, method, url, data, ts]).encode()).hexdigest()
    req = urllib.request.Request(url, data=data.encode() if data else None, method=method)
    for k, v in {"X-Ovh-Application": ak, "X-Ovh-Consumer": ck, "X-Ovh-Timestamp": ts,
                 "X-Ovh-Signature": sig, "Content-Type": "application/json"}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        if ok404 and e.code == 404:
            return None
        try:
            raw = json.loads(raw)
        except ValueError:
            pass
        raise ApiError(e.code, raw)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def log(msg):
    HOME.mkdir(exist_ok=True)
    line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def load_cfg():
    if not CFG.exists():
        die("no config: run `ovhpc.py init --project <id>` (list ids: api GET /cloud/project)")
    c = dict(DEFAULTS)
    c.update(json.loads(CFG.read_text(encoding="utf-8")))
    return c


def save_cfg(c):
    HOME.mkdir(exist_ok=True)
    CFG.write_text(json.dumps(c, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- domain
def P(c):
    return f"/cloud/project/{c['project']}"


def find_instance(c):
    """Return the instance dict or None. Resolves by id, then by name+region."""
    if c.get("instance_id"):
        inst = call("GET", f"{P(c)}/instance/{c['instance_id']}", ok404=True)
        if inst:
            return inst
    for i in call("GET", f"{P(c)}/instance?region={c['region']}") or []:
        if i["name"] == c["name"]:
            if c.get("instance_id") != i["id"]:
                c["instance_id"] = i["id"]
                save_cfg(c)
            return i
    return None


def ipv4(inst):
    for a in inst.get("ipAddresses") or []:
        if a.get("version") == 4 and a.get("type") == "public":
            return a["ip"]
    return None


def budget(c):
    now = dt.datetime.now(dt.timezone.utc)
    nxt = (now.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    credits = []
    for cid in call("GET", f"{P(c)}/credit") or []:
        cr = call("GET", f"{P(c)}/credit/{cid}")
        to = (cr.get("validity") or {}).get("to")
        to_dt = dt.datetime.fromisoformat(to) if to else None
        credits.append({
            "id": cid, "desc": cr.get("description"), "voucher": cr.get("voucher"),
            "available": float(cr["available_credit"]["value"]),
            "used": float(cr["used_credit"]["value"]),
            "valid_to": to, "valid_now": to_dt is None or to_dt > now,
            "valid_at_next_bill": to_dt is None or to_dt > nxt,
        })
    usage = call("GET", f"{P(c)}/usage/current", ok404=True)
    used = float(((usage or {}).get("totalPrice") or {}).get("value") or 0.0)
    charged = used * float(c["vat_factor"])
    cons = sum(x["available"] for x in credits if x["valid_now"] and x["valid_at_next_bill"]) - charged
    opt = sum(x["available"] for x in credits if x["valid_now"]) - charged
    return {
        "credits": credits, "month_usage_ex_vat": round(used, 4),
        "usage_last_update": (usage or {}).get("lastUpdate"),
        "remaining_conservative": round(cons, 2), "remaining_optimistic": round(opt, 2),
        "next_bill": nxt.date().isoformat(), "floor_eur": c["floor_eur"],
    }


def wait_status(c, want, timeout_s, bad=("ERROR",)):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        inst = find_instance(c)
        st = inst["status"] if inst else "GONE"
        if st != last:
            print(f"  {int(time.time() - t0):>4}s  {st}", flush=True)
            last = st
        if st in want:
            return inst
        if st in bad:
            die(f"instance entered {st}; inspect it in the panel or with `api GET {P(c)}/instance/{c.get('instance_id')}`")
        time.sleep(10)
    die(f"timeout after {timeout_s}s waiting for {want}; last status {last}")


def resolve_ids(c):
    flv = [f for f in call("GET", f"{P(c)}/flavor?region={c['region']}") if f["name"] == c["flavor"]]
    if not flv:
        die(f"flavor {c['flavor']} not in {c['region']}")
    imgs = [i for i in call("GET", f"{P(c)}/image?region={c['region']}") if i["name"] == c["image"]]
    if not imgs:
        die(f"image {c['image']!r} not in {c['region']}")
    return flv[0]["id"], imgs[0]["id"]


# ---------------------------------------------------------------- commands
def cmd_init(args):
    c = dict(DEFAULTS)
    if CFG.exists():
        c.update(json.loads(CFG.read_text(encoding="utf-8")))
    it = iter(args)
    for a in it:
        if a.startswith("--"):
            k = a[2:].replace("-", "_")
            v = next(it)
            c[k] = float(v) if k in ("floor_eur", "vat_factor") else v
    if not c.get("project"):
        die("--project required (api GET /cloud/project)")
    save_cfg(c)
    print(json.dumps(c, indent=2))


def token_days_left():
    exp = (call("GET", "/auth/currentCredential") or {}).get("expiration")
    if not exp:
        return None
    return (dt.datetime.fromisoformat(exp) - dt.datetime.now(dt.timezone.utc)).days


def show_status(c, inst, b):
    days = token_days_left()
    if days is not None:
        print(f"token     expires in {days} days" + ("  <-- renew: ovhpc.py new-token" if days < 7 else ""))
    if inst:
        print(f"instance  {inst['name']}  {inst['status']}  {c['flavor']}@{inst['region']}  ip={ipv4(inst)}  "
              f"monthlyBilling={'ON' if inst.get('monthlyBilling') else 'off'}")
    else:
        print("instance  (none)")
    print(f"budget    remaining≈{b['remaining_conservative']} € (conservative) / {b['remaining_optimistic']} € "
          f"(optimistic)  month usage {b['month_usage_ex_vat']} € ex-VAT  floor {b['floor_eur']} €")


def cmd_status(_):
    c = load_cfg()
    show_status(c, find_instance(c), budget(c))


def cmd_budget(_):
    print(json.dumps(budget(load_cfg()), indent=2, ensure_ascii=False))


def cmd_create(_):
    c = load_cfg()
    if find_instance(c):
        die(f"instance {c['name']} already exists in {c['region']}; use up/down")
    b = budget(c)
    if b["remaining_optimistic"] < c["floor_eur"]:
        die(f"credit below floor ({b['remaining_optimistic']} €)", 2)
    flavor_id, image_id = resolve_ids(c)
    body = {"name": c["name"], "region": c["region"], "flavorId": flavor_id, "imageId": image_id,
            "monthlyBilling": False}
    inst = call("POST", f"{P(c)}/instance", body)
    c["instance_id"] = inst["id"]
    save_cfg(c)
    log(f"create {c['name']} {c['flavor']} {c['region']} id={inst['id']}")
    inst = wait_status(c, {"ACTIVE"}, 1800)
    print(f"ACTIVE  ip={ipv4(inst)}")
    if "windows" in c["image"].lower():
        print("Windows first boot: run `ovhpc.py vnc`, open the URL, set language + Administrator password.")


def cmd_up(_):
    c = load_cfg()
    inst = find_instance(c) or die("no instance; run create")
    b = budget(c)
    if b["remaining_conservative"] < c["floor_eur"]:
        die(f"remaining credit ≈{b['remaining_conservative']} € < floor {c['floor_eur']} €: refusing to start", 2)
    st = inst["status"]
    if st in SHELVED:
        call("POST", f"{P(c)}/instance/{inst['id']}/unshelve")
        log(f"unshelve {c['name']}")
    elif st in OFF:
        call("POST", f"{P(c)}/instance/{inst['id']}/start")
        log(f"start {c['name']} (was {st})")
    elif st != "ACTIVE":
        print(f"status {st}: waiting")
    inst = wait_status(c, {"ACTIVE"}, 1800)
    print(f"ACTIVE  ip={ipv4(inst)}   RDP: mstsc /v:{ipv4(inst)}")
    show_status(c, inst, b)


def cmd_down(_):
    c = load_cfg()
    inst = find_instance(c) or die("no instance")
    if inst["status"] in SHELVED:
        print(f"already {inst['status']}")
        return
    call("POST", f"{P(c)}/instance/{inst['id']}/shelve")
    log(f"shelve {c['name']} (was {inst['status']})")
    wait_status(c, {"SHELVED_OFFLOADED"}, 2400)
    print("shelved: compute billing stopped; snapshot storage + IP keep billing (cents/month)")


def cmd_vnc(_):
    c = load_cfg()
    inst = find_instance(c) or die("no instance")
    r = call("POST", f"{P(c)}/instance/{inst['id']}/vnc")
    print(r["url"])


def cmd_guard(_):
    """Unattended. Shelves when the instance is off-but-billed or the credit floor is hit."""
    c = load_cfg()
    try:
        inst = find_instance(c)
        if not inst:
            return
        st = inst["status"]
        if st in OFF:
            call("POST", f"{P(c)}/instance/{inst['id']}/shelve")
            log(f"guard: {st} is billed at full rate -> shelve")
            return
        if st == "ERROR":
            log("guard: instance in ERROR, needs a human")
            sys.exit(3)
        days = token_days_left()
        if days is not None and days < 7 and dt.datetime.now().hour == 9 and dt.datetime.now().minute < 15:
            log(f"guard: WARNING API token expires in {days} days -> ovhpc.py new-token")
        if st == "ACTIVE":
            b = budget(c)
            if b["remaining_conservative"] < c["floor_eur"]:
                call("POST", f"{P(c)}/instance/{inst['id']}/shelve")
                log(f"guard: remaining ≈{b['remaining_conservative']} € < floor -> shelve")
                return
            if inst.get("monthlyBilling"):
                log("guard: WARNING monthlyBilling is ON (irreversible, bills full months)")
    except Exception as e:  # keep the scheduled task alive, but leave a trace
        log(f"guard: error {e}")
        sys.exit(1)


def cmd_install_guard(args):
    minutes = args[args.index("--minutes") + 1] if "--minutes" in args else "15"
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    exe = pyw if pyw.exists() else py
    tr = f'"{exe}" -I "{Path(__file__).resolve()}" guard'
    r = subprocess.run(["schtasks", "/Create", "/SC", "MINUTE", "/MO", str(minutes), "/TN", "OVH-Guard",
                        "/TR", tr, "/F"], capture_output=True, text=True)
    print(r.stdout or r.stderr)
    sys.exit(r.returncode)


def cmd_uninstall_guard(_):
    r = subprocess.run(["schtasks", "/Delete", "/TN", "OVH-Guard", "/F"], capture_output=True, text=True)
    print(r.stdout or r.stderr)


def cmd_vm_token(_):
    c = load_cfg()
    inst = find_instance(c) or die("no instance")
    ak, as_, _ck = creds()
    p = f"{P(c)}/instance/{inst['id']}"
    rules = [{"method": "GET", "path": p}, {"method": "POST", "path": p + "/shelve"}]
    req = urllib.request.Request(base() + "/auth/credential", method="POST",
                                 data=json.dumps({"accessRules": rules}).encode())
    req.add_header("X-Ovh-Application", ak)
    req.add_header("Content-Type", "application/json")
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    out = HOME / "vm-agent"
    out.mkdir(parents=True, exist_ok=True)
    for f in (HERE / "vm-agent").iterdir():
        shutil.copy2(f, out / f.name)
    (out / "config.json").write_text(json.dumps({
        "endpoint": base(), "ak": ak, "as": as_, "ck": r["consumerKey"],
        "project": c["project"], "instance": inst["id"], "idle_minutes": 45,
        "dayz_rx_kb_per_min": 300,
    }, indent=2), encoding="utf-8")
    print(f"bundle: {out}  (contains secrets: copy to the VM, do not share)")
    print("rules:", [(x["method"], x["path"]) for x in rules])
    print("validate (log in to OVH, choose 'unlimited'):", r["validationUrl"])


def cmd_new_token(_):
    """Request the main credential (read all + manage this project) and store it in
    HKCU\\Environment\\OVH_ConsumerKey without printing it. User must open validationUrl."""
    c = load_cfg()
    ak = _env("OVH_APPKEY") or die("OVH_APPKEY missing")
    rules = [{"method": "GET", "path": "/*"}] + [
        {"method": m, "path": f"{P(c)}/*"} for m in ("POST", "PUT", "DELETE")]
    req = urllib.request.Request(base() + "/auth/credential", method="POST",
                                 data=json.dumps({"accessRules": rules}).encode())
    req.add_header("X-Ovh-Application", ak)
    req.add_header("Content-Type", "application/json")
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if sys.platform != "win32":
        die("store consumerKey manually: non-Windows host")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "OVH_ConsumerKey", 0, winreg.REG_SZ, r["consumerKey"])
    print("stored OVH_ConsumerKey (not shown); rules:", [(x["method"], x["path"]) for x in rules])
    print("validate (log in, choose 'Unlimited' so the guard does not die):", r["validationUrl"])


def cmd_api(args):
    v2 = "--v2" in args
    args = [a for a in args if a != "--v2"]
    if len(args) < 2:
        die("usage: api METHOD /path [json]")
    try:
        out = call(args[0].upper(), args[1], args[2] if len(args) > 2 else None, v2)
    except ApiError as e:
        print(json.dumps(e.body, indent=2, ensure_ascii=False) if not isinstance(e.body, str) else e.body)
        sys.exit(1)
    print(json.dumps(out, indent=2, ensure_ascii=False))


CMDS = {"init": cmd_init, "status": cmd_status, "budget": cmd_budget, "create": cmd_create,
        "up": cmd_up, "down": cmd_down, "vnc": cmd_vnc, "guard": cmd_guard,
        "install-guard": cmd_install_guard, "uninstall-guard": cmd_uninstall_guard,
        "vm-token": cmd_vm_token, "new-token": cmd_new_token, "api": cmd_api}

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        sys.exit(1)
    try:
        CMDS[sys.argv[1]](sys.argv[2:])
    except ApiError as e:
        die(str(e))
