#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_agent_install.py — Slopsquatting guard (card d859cee2, SabaTech security)

Verifica ANTES de cualquier install generado por agente que:
  POL-1  el registry está en la allowlist oficial (pypi.org | registry.npmjs.org)
  POL-2  el paquete EXISTE en el registry oficial (HEAD; 404 = sospecha de alucinación)
  POL-3  la versión está pineada exacta (== en pip; semver exacto en npm)
  POL-4  FAIL-CLOSED: error de red, timeout, HTTP inesperado o redirect → BLOQUEO
Uso:
  guard_agent_install.py check pypi <paquete> [version]
  guard_agent_install.py check npm  <paquete> [version]
  guard_agent_install.py cmd   -- pip install requests==2.32.3
  guard_agent_install.py cmd   -- npm install express@4.21.2
  guard_agent_install.py demo                          # demo autoverificada (4 casos)
  opciones: --json   (salida machine-readable para CI)
Exit codes: 0=ALLOW · 1=BLOCK (política: no existe / sin pin / registry fuera de allowlist)
            2=BLOCK (fail-closed: registry caído, timeout, redirect, HTTP inesperado)
            5=demo con expectativas incumplidas · 64=uso incorrecto
Sin dependencias externas (stdlib). El guard NUNCA ejecuta el install: solo decide y evidencia.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote, urlparse

ALLOWLIST = {
    "pypi": "https://pypi.org",
    "npm": "https://registry.npmjs.org",
}
TIMEOUT_S = 10
UA = "sabatech-slopsquat-guard/1.0 (card d859cee2)"
SIM_DOWN = False  # solo demo: simula registry caído (SLOPSQUAT_SIM_DOWN=1)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Deshabilita redirects: cualquier 3xx → fail-closed (evita bypass por redirect)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def http_status(url):
    """HEAD sin redirects. Devuelve (status:int|None, error:str|None)."""
    if SIM_DOWN:
        return None, "SIMULATED: registry unreachable (demo fail-closed)"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with OPENER.open(req, timeout=TIMEOUT_S) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # URLError, timeout, DNS, TLS...
        return None, "%s: %s" % (type(e).__name__, e)


def check_exists(eco, pkg, version=None):
    """(verdict, detail). verdict ∈ ALLOW | BLOCK_POLICY | BLOCK_FAILCLOSED"""
    if eco not in ALLOWLIST:
        return "BLOCK_POLICY", "ecosistema '%s' fuera de allowlist (solo: %s)" % (eco, ", ".join(sorted(ALLOWLIST)))
    host = ALLOWLIST[eco].split("//", 1)[1]
    if eco == "pypi":
        pkg_url = quote(pkg.strip(), safe="._-[]")
        url = "%s/pypi/%s/json" % (ALLOWLIST[eco], pkg_url)
        if version:
            url = "%s/pypi/%s/%s/json" % (ALLOWLIST[eco], pkg_url, quote(version, safe="."))
    else:  # npm (soporta @scope/pkg → encode '/' como %2F)
        enc = quote(pkg.strip(), safe="")
        url = "%s/%s" % (ALLOWLIST[eco], enc)
        if version:
            url = "%s/%s/%s" % (ALLOWLIST[eco], enc, quote(version, safe="."))
    if urlparse(url).hostname != host:
        return "BLOCK_POLICY", "host '%s' fuera de allowlist oficial" % urlparse(url).hostname
    status, err = http_status(url)
    if err:
        return "BLOCK_FAILCLOSED", "registry inalcanzable/error → fail-closed [%s]" % err
    if 300 <= (status or 0) < 400:
        return "BLOCK_FAILCLOSED", "redirect HTTP %s → fail-closed (bypass prohibido)" % status
    if status == 404:
        return "BLOCK_POLICY", "NO EXISTE en %s (HTTP 404) → sospecha de paquete alucinado (slopsquatting)" % host
    if status == 200:
        return "ALLOW", "existe en %s (HTTP 200)%s" % (host, " · versión %s verificada" % version if version else "")
    return "BLOCK_FAILCLOSED", "HTTP %s inesperado → fail-closed" % status


PIN_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def parse_pip_spec(spec):
    """'name[extras]==1.2.3' → (name, version|None, pinned:bool). No-pin o rangos → pinned=False."""
    spec = spec.split(";", 1)[0].strip()  # quita environment markers
    m = re.match(r"^([A-Za-z0-9._-]+)(\[[^\]]*\])?(.*)$", spec)
    if not m:
        return spec, None, False
    name, _, rest = m.groups()
    rest = rest.strip()
    if rest.startswith("=="):
        ver = rest[2:].strip()
        return name, ver or None, bool(ver)
    return name, None, False  # bare, >=, ~=, !=, >, <


def parse_npm_spec(spec):
    """'@scope/pkg@1.2.3' | 'pkg@1.2.3' | 'pkg' → (name, version|None, pinned:bool)."""
    spec = spec.strip()
    if spec.startswith("@"):
        body = spec[1:]
        if "@" in body:
            name, ver = body.rsplit("@", 1)
            name = "@" + name
        else:
            name, ver = spec, None
    elif "@" in spec:
        name, ver = spec.rsplit("@", 1)
    else:
        name, ver = spec, None
    ver = (ver or "").strip()
    if ver in ("", "latest", "*") or any(c in ver for c in "^~><"):
        return name, None, False
    return name, ver or None, bool(PIN_RE.match(ver))


def detect_eco(argv):
    """argv[0] del comando de install → (ecosistema|None, resto_argv)."""
    tool = argv[0].lower() if argv else ""
    if tool in ("pip", "pip3", "uv", "uv pip", "pipx"):
        return "pypi", argv[1:]
    if tool in ("npm", "npx", "pnpm", "yarn", "yarnpkg", "bun"):
        return "npm", argv[1:]
    return None, argv


PIP_INDEX_FLAGS = {"-i", "--index-url", "--extra-index-url"}


def cmd_mode(rest, as_json):
    """Evalúa un comando de install completo. Nunca ejecuta: solo ALLOW/BLOCK + evidencia."""
    if not rest:
        return 64, {"error": "cmd vacío tras '--'"}
    eco, args = detect_eco(rest)
    if eco is None:
        return 1, {"verdict": "BLOCK_POLICY", "detail": "tool '%s' no reconocida como install permitido" % (rest[0] if rest else "?")}
    if eco == "pypi" and "install" not in args and "add" not in args:
        return 1, {"verdict": "BLOCK_POLICY", "detail": "comando no es install — fuera de scope del guard"}
    if eco == "npm" and not any(a in args for a in ("install", "i", "add", "exec", "x")) and rest[0].lower() != "npx":
        return 1, {"verdict": "BLOCK_POLICY", "detail": "comando no es install/exec — fuera de scope del guard"}
    # POL-1: registry explícito fuera de allowlist
    for i, a in enumerate(args):
        if a in PIP_INDEX_FLAGS and i + 1 < len(args):
            return 1, {"verdict": "BLOCK_POLICY", "detail": "registry custom '%s' fuera de allowlist (solo pypi.org)" % args[i + 1]}
        if a == "--registry" and i + 1 < len(args) and "registry.npmjs.org" not in args[i + 1]:
            return 1, {"verdict": "BLOCK_POLICY", "detail": "registry custom '%s' fuera de allowlist (solo registry.npmjs.org)" % args[i + 1]}
    specs = [a for a in args if not a.startswith("-") and a not in ("install", "i", "add", "exec", "x", "global")]
    if not specs:
        return 1, {"verdict": "BLOCK_POLICY", "detail": "sin paquetes identificables en el comando"}
    results, worst = [], 0
    for spec in specs:
        name, ver, pinned = (parse_pip_spec if eco == "pypi" else parse_npm_spec)(spec)
        if not pinned:
            results.append({"spec": spec, "verdict": "BLOCK_POLICY", "detail": "sin pin exacto (POL-3): usa %s" % ("pkg==X.Y.Z" if eco == "pypi" else "pkg@X.Y.Z")})
            worst = max(worst, 1)
            continue
        v, d = check_exists(eco, name, ver)
        results.append({"spec": spec, "verdict": v, "detail": d})
        code = {"ALLOW": 0, "BLOCK_POLICY": 1, "BLOCK_FAILCLOSED": 2}[v]
        worst = max(worst, code)
    verdict = "ALLOW" if worst == 0 else ("BLOCK_POLICY" if worst == 1 else "BLOCK_FAILCLOSED")
    if as_json:
        return worst, {"verdict": verdict, "ecosystem": eco, "command": " ".join(rest), "checks": results}
    out = ["[%s] %s  (%s)" % (verdict, " ".join(rest), eco)]
    for r in results:
        out.append("  - %-28s %s — %s" % (r["spec"], r["verdict"], r["detail"]))
    if worst == 0:
        out.append("→ INSTALL AUTORIZADO (ejecuta tú el comando; el guard no ejecuta)")
    else:
        out.append("→ INSTALL ABORTADO por slopsquatting-guard (evidencia arriba)")
    return worst, "\n".join(out)


def demo_mode(as_json):
    """Demo autoverificada: 2 alucinados (BLOCK), 1 real pineado (ALLOW), 1 sin pin (BLOCK), 1 fail-closed (BLOCK)."""
    global SIM_DOWN
    cases = []
    v, d = check_exists("pypi", "pandas-fastnumeric")
    cases.append(("PyPI alucinado → BLOCK", v == "BLOCK_POLICY", "pandas-fastnumeric", v, d))
    v, d = check_exists("npm", "react-global-store-utils")
    cases.append(("npm alucinado → BLOCK", v == "BLOCK_POLICY", "react-global-store-utils", v, d))
    v, d = check_exists("pypi", "requests", "2.32.3")
    cases.append(("PyPI real pineado → ALLOW", v == "ALLOW", "requests==2.32.3", v, d))
    rc, out = cmd_mode(["pip", "install", "requests>=2.0"], as_json)
    cases.append(("real SIN pin → BLOCK (POL-3)", rc == 1, "pip install requests>=2.0", "BLOCK_POLICY", str(out)[:120]))
    SIM_DOWN = True
    v, d = check_exists("pypi", "requests")
    SIM_DOWN = False
    cases.append(("registry caído → BLOCK fail-closed (POL-4, simulado)", v == "BLOCK_FAILCLOSED", "network-down(sim)", v, d))
    ok = all(c[1] for c in cases)
    if as_json:
        return (0 if ok else 5), {"demo": "slopsquatting-guard", "pass": ok, "cases": [{"case": c[0], "pass": c[1], "target": c[2], "verdict": c[3], "detail": c[4]} for c in cases]}
    lines = ["== demo slopsquatting-guard (card d859cee2) — %s ==" % ("PASS" if ok else "FAIL")]
    for name, passed, target, v, d in cases:
        lines.append("  [%s] %s\n        target: %s → %s · %s" % ("PASS" if passed else "FAIL", name, target, v, d))
    lines.append("exit esperado: %d" % (0 if ok else 5))
    return (0 if ok else 5), "\n".join(lines)


def main(argv):
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv:
        print(__doc__)
        return 64
    mode = argv[0]
    if mode == "demo":
        rc, out = demo_mode(as_json)
    elif mode == "check" and len(argv) >= 3:
        eco = argv[1].lower()
        pkg = argv[2]
        ver = argv[3] if len(argv) > 3 else None
        v, d = check_exists(eco, pkg, ver)
        rc = {"ALLOW": 0, "BLOCK_POLICY": 1, "BLOCK_FAILCLOSED": 2}[v]
        out = {"verdict": v, "ecosystem": eco, "package": pkg, "version": ver, "detail": d} if as_json \
            else "[%s] %s%s — %s" % (v, pkg, ("@" + ver if ver and eco == "npm" else ("==" + ver if ver else "")), d)
    elif mode == "cmd" and len(argv) >= 2 and argv[1] == "--":
        rc, out = cmd_mode(argv[2:], as_json)
    else:
        print(__doc__)
        return 64
    print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    import os
    SIM_DOWN = os.environ.get("SLOPSQUAT_SIM_DOWN") == "1"
    sys.exit(main(sys.argv[1:]))
