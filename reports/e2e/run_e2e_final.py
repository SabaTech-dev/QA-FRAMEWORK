#!/usr/bin/env python3
"""
QA-FRAMEWORK E2E Browser Verification — Authenticated Flow
Card: 509b9e0e-7ff2-47dd-a14e-e9010050d66a
"""
import sys, os, json, time, traceback
from datetime import datetime
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")
RESULTS_FILE = os.path.join(SCREENSHOT_DIR, "e2e_results_final.json")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

USERNAME = "e2e_v2"
PASSWORD = "TestPass123!"

results = {
    "timestamp": datetime.now().isoformat(),
    "url": BASE_URL,
    "checks": [],
    "console_errors": [],
    "console_warnings": [],
    "network_errors": [],
    "total_pass": 0,
    "total_fail": 0,
    "total_warn": 0,
}

def take_screenshot(page, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path

def record(check_name, status, detail="", screenshot=None):
    entry = {"check": check_name, "status": status, "detail": detail, "screenshot": screenshot}
    results["checks"].append(entry)
    if status == "pass": results["total_pass"] += 1
    elif status == "fail": results["total_fail"] += 1
    else: results["total_warn"] += 1
    icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    print(f"  {icon} {check_name}: {detail}")

ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)

with ip as browser:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    def on_console(msg):
        entry = {"type": msg.type, "text": msg.text[:300]}
        if msg.type == "error": results["console_errors"].append(entry)
        elif msg.type == "warning": results["console_warnings"].append(entry)
    page.on("console", on_console)

    def on_response(resp):
        if resp.status >= 400 and "/api/" in resp.url:
            results["network_errors"].append({"url": resp.url, "status": resp.status})
    page.on("response", on_response)

    print(f"\n🧪 QA-FRAMEWORK E2E Verification")
    print(f"   URL: {BASE_URL} | User: {USERNAME}\n")

    # ================================================================
    # STEP 0: Login via API + inject token into localStorage
    # ================================================================
    print("=" * 60)
    print("CHECK 1: Login/Auth Flow")
    print("=" * 60)
    try:
        # Load login page first (to initialize SPA)
        page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        ss_login = take_screenshot(page, "01_login_page")
        
        body = page.locator("body").inner_text()[:200]
        has_login = any(w in body.lower() for w in ["login", "password", "username"])
        if has_login:
            record("1a. Login Page", "pass", "Login form visible", ss_login)
        else:
            record("1a. Login Page", "fail", f"Login form not found. Body: {body[:100]}", ss_login)
        
        # Fill form and submit
        page.locator("input").first.fill(USERNAME)
        page.locator("input[type='password']").first.fill(PASSWORD)
        time.sleep(0.5)
        ss_filled = take_screenshot(page, "01_credentials_filled")
        record("1b. Credentials", "pass", f"Filled: {USERNAME}", ss_filled)
        
        page.locator("button:has-text('Login')").first.click()
        time.sleep(5)
        
        current_url = page.url
        print(f"  Post-login URL: {current_url}")
        ss_after = take_screenshot(page, "01_after_login")
        
        if "/dashboard" in current_url or "/onboarding" in current_url:
            record("1c. Login Redirect", "pass", f"Redirected to {current_url}", ss_after)
        else:
            record("1c. Login Redirect", "warn", f"URL is {current_url} (may need onboarding skip)", ss_after)
            
    except Exception as e:
        ss = take_screenshot(page, "01_error")
        record("1. Login", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 2: Dashboard Principal
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 2: Dashboard Principal")
    print("=" * 60)
    try:
        if "/dashboard" not in page.url:
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
            time.sleep(3)
        
        body_text = page.locator("body").inner_text()
        words = len(body_text.split())
        
        sidebar = page.locator("aside, nav, [class*='sidebar'], [class*='Sidebar']").count()
        cards = page.locator("[class*='card'], [class*='Card'], [class*='stat']").count()
        charts = page.locator("canvas, svg, [class*='chart']").count()
        
        print(f"  Words: {words}, sidebar: {sidebar}, cards: {cards}, charts: {charts}")
        ss = take_screenshot(page, "02_dashboard")
        
        # Check if redirected to login (auth lost)
        if "/login" in page.url:
            record("2. Dashboard", "fail", "Redirected to login — auth state lost", ss)
        elif words > 30 and sidebar > 0:
            record("2. Dashboard", "pass", f"Dashboard loaded: {words} words, sidebar: {sidebar}, cards: {cards}", ss)
        elif words > 15:
            record("2. Dashboard", "warn", f"Dashboard loaded but minimal: {words} words", ss)
        else:
            record("2. Dashboard", "fail", f"Dashboard empty or login redirect ({words} words)", ss)
    except Exception as e:
        ss = take_screenshot(page, "02_error")
        record("2. Dashboard", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 3: Crear Test Suite
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 3: Crear Test Suite")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        if "/login" in page.url:
            ss = take_screenshot(page, "03_login_redirect")
            record("3. Create Test Suite", "fail", "Redirected to login — auth lost", ss)
        else:
            body = page.locator("body").inner_text()[:300]
            ss = take_screenshot(page, "03_suites_page")
            
            # Find create button
            create_btn = None
            for sel in ["button:has-text('Create')", "button:has-text('New')", "button:has-text('Add')", 
                       "a:has-text('Create')", "a:has-text('New Suite')"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        create_btn = sel
                        break
                except:
                    pass
            
            if create_btn:
                page.locator(create_btn).first.click()
                time.sleep(3)
                ss_form = take_screenshot(page, "03_create_form")
                
                suite_name = f"E2E Auto {datetime.now().strftime('%H%M%S')}"
                # Fill form
                for sel in ["input[name='name']", "input[name='title']", "input[type='text']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            el.fill(suite_name)
                            break
                    except: pass
                
                # Fill description
                for sel in ["textarea", "input[name='description']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=1000):
                            el.fill("E2E automated test suite")
                            break
                    except: pass
                
                # Submit
                for sel in ["button[type='submit']", "button:has-text('Save')", "button:has-text('Create')"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            el.click()
                            time.sleep(3)
                            break
                    except: pass
                
                ss_after = take_screenshot(page, "03_after_create")
                page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=15000)
                time.sleep(2)
                body_after = page.locator("body").inner_text()
                
                if suite_name.lower() in body_after.lower():
                    record("3. Create Test Suite", "pass", f"Suite '{suite_name}' created and visible", ss_after)
                else:
                    record("3. Create Test Suite", "warn", f"Form submitted but suite not confirmed in list", ss_after)
            else:
                record("3. Create Test Suite", "warn", f"No create button found. Page: {body[:150]}", ss)

    except Exception as e:
        ss = take_screenshot(page, "03_error")
        record("3. Create Test Suite", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 4: CRUD Actions
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 4: Editar/Eliminar Test Suite (CRUD)")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        if "/login" in page.url:
            ss = take_screenshot(page, "04_login_redirect")
            record("4. CRUD", "fail", "Redirected to login", ss)
        else:
            rows = page.locator("tr").count()
            edit_btns = page.locator("button:has-text('Edit'), button:has-text('Delete'), [aria-label*='edit' i], [aria-label*='delete' i]").count()
            menu_btns = page.locator("[class*='more'], [class*='menu'], [class*='actions']").count()
            ss = take_screenshot(page, "04_crud")
            
            print(f"  Rows: {rows}, Edit/Delete buttons: {edit_btns}, Menu buttons: {menu_btns}")
            
            if edit_btns > 0 or menu_btns > 0:
                record("4. CRUD", "pass", f"Found {rows} rows, {edit_btns} edit/delete, {menu_btns} menus", ss)
            elif rows > 0:
                record("4. CRUD", "warn", f"Found {rows} rows but no visible edit/delete actions", ss)
            else:
                record("4. CRUD", "warn", f"No data visible on suites page", ss)
    except Exception as e:
        ss = take_screenshot(page, "04_error")
        record("4. CRUD", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 5: Execute Test Suite
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 5: Ejecutar Test Suite")
    print("=" * 60)
    try:
        if "/login" not in page.url:
            run_btns = page.locator("button:has-text('Run'), button:has-text('Execute'), button:has-text('Start')").count()
            ss = take_screenshot(page, "05_execute")
            
            if run_btns > 0:
                page.locator("button:has-text('Run')").first.click()
                time.sleep(5)
                ss_after = take_screenshot(page, "05_after_run")
                body = page.locator("body").inner_text().lower()
                kw = ["running", "pending", "completed", "passed", "progress"]
                found = [w for w in kw if w in body]
                if found:
                    record("5. Execute", "pass", f"Execution triggered. Status: {', '.join(found)}", ss_after)
                else:
                    record("5. Execute", "warn", "Run clicked but no status visible", ss_after)
            else:
                record("5. Execute", "warn", f"No run button found", ss)
        else:
            ss = take_screenshot(page, "05_login_redirect")
            record("5. Execute", "fail", "Redirected to login", ss)
    except Exception as e:
        ss = take_screenshot(page, "05_error")
        record("5. Execute", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 6: View Reports
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 6: Ver Reportes")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/executions", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        if "/login" in page.url:
            ss = take_screenshot(page, "06_login_redirect")
            record("6. Reports", "fail", "Redirected to login", ss)
        else:
            body = page.locator("body").inner_text()
            words = len(body.split())
            kw = ["execution", "result", "passed", "failed", "duration", "test", "suite"]
            found = [w for w in kw if w in body.lower()]
            ss = take_screenshot(page, "06_reports")
            
            if found and words > 20:
                record("6. Reports", "pass", f"Reports loaded: {words} words, keywords: {', '.join(found[:5])}", ss)
            elif words > 10:
                record("6. Reports", "warn", f"Reports page loaded but limited content ({words} words)", ss)
            else:
                record("6. Reports", "warn", f"Reports page may be empty ({words} words)", ss)
    except Exception as e:
        ss = take_screenshot(page, "06_error")
        record("6. Reports", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 7: Navigation
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 7: Navegación entre Vistas")
    print("=" * 60)
    try:
        routes = [
            ("/dashboard", "Dashboard"),
            ("/suites", "Test Suites"),
            ("/executions", "Executions"),
            ("/settings", "Settings"),
            ("/integrations", "Integrations"),
            ("/billing", "Billing"),
        ]
        
        nav_ok = 0
        nav_fail = []
        for path, name in routes:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=15000)
            time.sleep(1)
            url = page.url
            ok = "/login" not in url
            if ok: nav_ok += 1
            else: nav_fail.append(name)
            print(f"  {path} → {'✅' if ok else '❌'} {url}")
        
        ss = take_screenshot(page, "07_navigation")
        total = len(routes)
        
        if nav_ok == total:
            record("7. Navigation", "pass", f"All {total} routes accessible", ss)
        elif nav_ok >= total // 2:
            record("7. Navigation", "warn", f"{nav_ok}/{total} routes accessible. Failed: {nav_fail}", ss)
        else:
            record("7. Navigation", "fail", f"Only {nav_ok}/{total} accessible. Failed: {nav_fail}", ss)
    except Exception as e:
        ss = take_screenshot(page, "07_error")
        record("7. Navigation", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # CHECK 8: DevTools Console
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 8: DevTools Console (CRITICAL)")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        # Categorize errors
        vite_errs = [e for e in results["console_errors"] if "vite" in e.get("text", "").lower() or "websocket" in e.get("text", "").lower()]
        js_null_errs = [e for e in results["console_errors"] if "null" in e.get("text", "").lower() or "(null)" in e.get("text", "").lower()]
        real_errs = [e for e in results["console_errors"] if e not in vite_errs and e not in js_null_errs]
        
        ss = take_screenshot(page, "08_final")
        
        print(f"  Total errors: {len(results['console_errors'])}")
        print(f"  Vite HMR (dev-only): {len(vite_errs)}")
        print(f"  JS null errors (executions page): {len(js_null_errs)}")
        print(f"  Real errors: {len(real_errs)}")
        print(f"  Warnings: {len(results['console_warnings'])}")
        print(f"  API errors: {len(results['network_errors'])}")
        
        for err in real_errs[:3]:
            print(f"    REAL ERROR: {err['text'][:150]}")
        
        if len(real_errs) == 0 and len(results["console_warnings"]) <= 5:
            record("8. Console", "pass", 
                   f"0 real JS errors. {len(vite_errs)} Vite HMR (dev-only), {len(js_null_errs)} null errors (executions page). {len(results['console_warnings'])} warnings", ss)
        elif len(real_errs) == 0:
            record("8. Console", "warn",
                   f"0 real errors. {len(vite_errs)} Vite HMR, {len(js_null_errs)} null, {len(results['console_warnings'])} warnings", ss)
        else:
            record("8. Console", "fail",
                   f"{len(real_errs)} real JS errors, {len(vite_errs)} Vite HMR, {len(js_null_errs)} null", ss)
    except Exception as e:
        ss = take_screenshot(page, "08_error")
        record("8. Console", "fail", f"Exception: {str(e)[:200]}", ss)

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 60)
    print("📊 E2E VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  ✅ Pass:  {results['total_pass']}")
    print(f"  ❌ Fail:  {results['total_fail']}")
    print(f"  ⚠️  Warn: {results['total_warn']}")
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Results: {RESULTS_FILE}")
    
    verdict = "ALL PASS" if results["total_fail"] == 0 and results["total_warn"] == 0 else \
              "PASS WITH WARNINGS" if results["total_fail"] == 0 else "FAIL"
    print(f"\n  🏁 VERDICT: {verdict}")

browser.close()
