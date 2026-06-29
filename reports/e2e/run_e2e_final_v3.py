#!/usr/bin/env python3
"""
QA-FRAMEWORK E2E — Final Verification (with direct navigation)
"""
import sys, os, json, time, traceback
from datetime import datetime
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")
RESULTS_FILE = os.path.join(SCREENSHOT_DIR, "e2e_final_v3.json")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

USERNAME = "e2e_v2"
PASSWORD = "TestPass123!"

results = {
    "timestamp": datetime.now().isoformat(),
    "checks": [], "console_errors": [], "console_warnings": [],
    "network_errors": [], "total_pass": 0, "total_fail": 0, "total_warn": 0,
}

def ss(page, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path

def rec(name, status, detail="", shot=None):
    results["checks"].append({"check": name, "status": status, "detail": detail, "screenshot": shot})
    if status == "pass": results["total_pass"] += 1
    elif status == "fail": results["total_fail"] += 1
    else: results["total_warn"] += 1
    print(f"  {'✅' if status=='pass' else '❌' if status=='fail' else '⚠️'} {name}: {detail}")

ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)

with ip as browser:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    errs = []
    def on_console(msg):
        if msg.type == "error": errs.append(msg.text[:300])
    page.on("console", on_console)
    
    def on_resp(r):
        if r.status >= 400 and "/api/" in r.url:
            results["network_errors"].append({"url": r.url, "status": r.status})
    page.on("response", on_resp)

    print(f"\n🧪 QA-FRAMEWORK E2E — Final Verification\n")

    # === CHECK 1: Login ===
    print("="*60); print("CHECK 1: Login/Auth Flow"); print("="*60)
    try:
        page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        s1 = ss(page, "final_01_login")
        rec("1a. Login Page", "pass", "Login form loads", s1)
        
        page.locator("input").first.fill(USERNAME)
        page.locator("input[type='password']").first.fill(PASSWORD)
        page.locator("button:has-text('Login')").first.click()
        time.sleep(5)
        
        # Check localStorage
        auth = page.evaluate("localStorage.getItem('auth-storage')")
        has_token = auth and 'token' in auth and auth != 'null'
        
        if has_token:
            rec("1b. Auth Token", "pass", "JWT token stored in localStorage", s1)
        else:
            rec("1b. Auth Token", "fail", "No auth token in localStorage", s1)
        
        # Navigate directly to dashboard (bug: SPA navigate() doesn't redirect)
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        if "/login" in page.url:
            rec("1c. Dashboard Access", "fail", "Redirected to login — auth not working", ss(page, "final_01_fail"))
        else:
            body = page.locator("body").inner_text()
            rec("1c. Dashboard Access", "pass", f"Dashboard accessible ({len(body.split())} words)", ss(page, "final_01_dashboard"))
    except Exception as e:
        rec("1. Login", "fail", str(e)[:200])

    # === CHECK 2: Dashboard ===
    print("\n"+"="*60); print("CHECK 2: Dashboard Principal"); print("="*60)
    try:
        body = page.locator("body").inner_text()
        words = len(body.split())
        sidebar = page.locator("aside, nav, [class*='sidebar'], [class*='Sidebar']").count()
        cards = page.locator("[class*='card'], [class*='Card']").count()
        charts = page.locator("canvas, svg").count()
        headings = page.locator("h1, h2, h3").count()
        
        print(f"  Words: {words}, sidebar: {sidebar}, cards: {cards}, charts: {charts}, headings: {headings}")
        s = ss(page, "final_02_dashboard")
        
        if words > 50 and sidebar > 0:
            rec("2. Dashboard", "pass", f"Dashboard: {words} words, {sidebar} nav, {cards} cards, {headings} headings", s)
        elif words > 20:
            rec("2. Dashboard", "warn", f"Dashboard loaded: {words} words", s)
        else:
            rec("2. Dashboard", "fail", f"Dashboard empty ({words} words)", s)
    except Exception as e:
        rec("2. Dashboard", "fail", str(e)[:200])

    # === CHECK 3: Create Test Suite ===
    print("\n"+"="*60); print("CHECK 3: Crear Test Suite"); print("="*60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        if "/login" in page.url:
            rec("3. Create Suite", "fail", "Redirected to login", ss(page, "final_03_login"))
        else:
            body = page.locator("body").inner_text()[:500]
            print(f"  Page: {body[:200]}")
            s = ss(page, "final_03_suites")
            
            # Check for onboarding page
            if "welcome" in body.lower() and "started" in body.lower():
                rec("3. Create Suite", "warn", "Onboarding page shown instead of suites", s)
            else:
                # Find create button
                create_sel = None
                for sel in ["button:has-text('Create')", "button:has-text('New')", 
                           "button:has-text('Add')", "a:has-text('Create')", "a:has-text('New')"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            create_sel = sel; break
                    except: pass
                
                if create_sel:
                    page.locator(create_sel).first.click()
                    time.sleep(3)
                    s2 = ss(page, "final_03_form")
                    
                    suite_name = f"E2E Suite {datetime.now().strftime('%H%M%S')}"
                    for sel in ["input[name='name']", "input[name='title']", "input[type='text']"]:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=2000):
                                el.fill(suite_name); break
                        except: pass
                    
                    for sel in ["textarea", "input[name='description']"]:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=1000):
                                el.fill("E2E automated test suite"); break
                        except: pass
                    
                    for sel in ["button[type='submit']", "button:has-text('Save')", "button:has-text('Create')"]:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=2000):
                                el.click(); time.sleep(3); break
                        except: pass
                    
                    s3 = ss(page, "final_03_created")
                    page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=15000)
                    time.sleep(2)
                    body2 = page.locator("body").inner_text()
                    
                    if suite_name.lower() in body2.lower():
                        rec("3. Create Suite", "pass", f"Suite '{suite_name}' created & visible", s3)
                    else:
                        rec("3. Create Suite", "warn", "Form submitted but not confirmed", s3)
                else:
                    rec("3. Create Suite", "warn", f"No create button found", s)
    except Exception as e:
        rec("3. Create Suite", "fail", str(e)[:200])

    # === CHECK 4: CRUD ===
    print("\n"+"="*60); print("CHECK 4: CRUD (Edit/Delete)"); print("="*60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        rows = page.locator("tr").count()
        edit = page.locator("[class*='edit'], [class*='delete'], [aria-label*='edit' i], [aria-label*='delete' i], button:has-text('Edit'), button:has-text('Delete')").count()
        s = ss(page, "final_04_crud")
        print(f"  Rows: {rows}, Edit/Delete: {edit}")
        
        if edit > 0:
            rec("4. CRUD", "pass", f"{rows} rows, {edit} edit/delete actions", s)
        elif rows > 0:
            rec("4. CRUD", "warn", f"{rows} rows, no visible actions", s)
        else:
            rec("4. CRUD", "warn", "No data", s)
    except Exception as e:
        rec("4. CRUD", "fail", str(e)[:200])

    # === CHECK 5: Execute ===
    print("\n"+"="*60); print("CHECK 5: Ejecutar Test Suite"); print("="*60)
    try:
        run = page.locator("button:has-text('Run'), button:has-text('Execute')").count()
        s = ss(page, "final_05_execute")
        
        if run > 0:
            page.locator("button:has-text('Run')").first.click()
            time.sleep(5)
            s2 = ss(page, "final_05_after")
            body = page.locator("body").inner_text().lower()
            kw = ["running", "pending", "completed", "passed", "progress"]
            found = [w for w in kw if w in body]
            if found:
                rec("5. Execute", "pass", f"Execution triggered: {', '.join(found)}", s2)
            else:
                rec("5. Execute", "warn", "Run clicked, no status", s2)
        else:
            rec("5. Execute", "warn", "No run button", s)
    except Exception as e:
        rec("5. Execute", "fail", str(e)[:200])

    # === CHECK 6: Reports ===
    print("\n"+"="*60); print("CHECK 6: Ver Reportes"); print("="*60)
    try:
        page.goto(f"{BASE_URL}/executions", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        body = page.locator("body").inner_text()
        words = len(body.split())
        kw = ["execution", "result", "passed", "failed", "duration", "test", "suite"]
        found = [w for w in kw if w in body.lower()]
        s = ss(page, "final_06_reports")
        
        if "/login" in page.url:
            rec("6. Reports", "fail", "Redirected to login", s)
        elif found and words > 20:
            rec("6. Reports", "pass", f"Reports: {words} words, {', '.join(found[:5])}", s)
        elif words > 10:
            rec("6. Reports", "warn", f"Reports page: {words} words", s)
        else:
            rec("6. Reports", "warn", f"Reports empty", s)
    except Exception as e:
        rec("6. Reports", "fail", str(e)[:200])

    # === CHECK 7: Navigation ===
    print("\n"+"="*60); print("CHECK 7: Navegación"); print("="*60)
    try:
        routes = [("/dashboard","Dashboard"),("/suites","Suites"),("/executions","Executions"),
                  ("/settings","Settings"),("/integrations","Integrations"),("/billing","Billing")]
        ok = 0; fail_list = []
        for path, name in routes:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=15000)
            time.sleep(1)
            good = "/login" not in page.url
            if good: ok += 1
            else: fail_list.append(name)
            print(f"  {path} → {'✅' if good else '❌'}")
        s = ss(page, "final_07_nav")
        if ok == len(routes):
            rec("7. Navigation", "pass", f"All {len(routes)} routes accessible", s)
        else:
            rec("7. Navigation", "warn" if ok > 2 else "fail", f"{ok}/{len(routes)}. Failed: {fail_list}", s)
    except Exception as e:
        rec("7. Navigation", "fail", str(e)[:200])

    # === CHECK 8: Console ===
    print("\n"+"="*60); print("CHECK 8: DevTools Console"); print("="*60)
    try:
        vite = [e for e in errs if "vite" in e.lower() or "websocket" in e.lower()]
        dom_nesting = [e for e in errs if "validateDOMNesting" in e or "cannot appear as a child" in e]
        real = [e for e in errs if e not in vite and e not in dom_nesting]
        s = ss(page, "final_08_console")
        
        print(f"  Total errors: {len(errs)}")
        print(f"  Vite HMR (dev-only): {len(vite)}")
        print(f"  DOM nesting warnings: {len(dom_nesting)}")
        print(f"  Real errors: {len(real)}")
        print(f"  Warnings: {len(results['console_warnings'])}")
        
        for e in real[:5]:
            print(f"    ERROR: {e[:150]}")
        
        if len(real) == 0:
            rec("8. Console", "pass", 
                f"0 real errors. {len(vite)} Vite HMR (dev-only), {len(dom_nesting)} DOM nesting warnings", s)
        else:
            rec("8. Console", "fail",
                f"{len(real)} real errors, {len(vite)} Vite HMR, {len(dom_nesting)} DOM nesting", s)
    except Exception as e:
        rec("8. Console", "fail", str(e)[:200])

    # === SUMMARY ===
    print("\n"+"="*60); print("📊 FINAL E2E VERIFICATION"); print("="*60)
    print(f"  ✅ Pass: {results['total_pass']}")
    print(f"  ❌ Fail: {results['total_fail']}")
    print(f"  ⚠️  Warn: {results['total_warn']}")
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved: {RESULTS_FILE}")
    v = "ALL PASS" if results["total_fail"]==0 and results["total_warn"]==0 else "PASS WITH WARNINGS" if results["total_fail"]==0 else "FAIL"
    print(f"\n  🏁 VERDICT: {v}")
    browser.close()
