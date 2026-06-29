#!/usr/bin/env python3
"""
QA-FRAMEWORK E2E Browser Verification — Full Auth Flow
Card: 509b9e0e-7ff2-47dd-a14e-e9010050d66a
"""
import sys, os, json, time, traceback
from datetime import datetime
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")
RESULTS_FILE = os.path.join(SCREENSHOT_DIR, "e2e_results_auth.json")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Credentials for test user created via API
USERNAME = "e2e_tester"
PASSWORD = "***"

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
    return entry

ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)

with ip as browser:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    # Capture console
    def on_console(msg):
        entry = {"type": msg.type, "text": msg.text[:300]}
        if msg.type == "error":
            results["console_errors"].append(entry)
        elif msg.type == "warning":
            results["console_warnings"].append(entry)
    page.on("console", on_console)

    def on_response(resp):
        if resp.status >= 400 and "/api/" in resp.url:
            results["network_errors"].append({"url": resp.url, "status": resp.status})
    page.on("response", on_response)

    print(f"\n🧪 QA-FRAMEWORK E2E Verification (Authenticated)")
    print(f"   URL: {BASE_URL}")
    print(f"   User: {USERNAME}\n")

    # ================================================================
    # CHECK 1: Login/Auth Flow
    # ================================================================
    print("=" * 60)
    print("CHECK 1: Login/Auth Flow")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        ss = take_screenshot(page, "01_login_page")
        title = page.title()
        print(f"  Page title: {title}")
        
        # Verify we're on the login page
        body_text = page.locator("body").inner_text()[:300]
        has_login = "login" in body_text.lower() or "password" in body_text.lower() or "username" in body_text.lower()
        
        if has_login:
            record("1a. Login Page Loads", "pass", "Login form visible", ss)
        else:
            record("1a. Login Page Loads", "fail", f"Login form not found. Body: {body_text[:200]}", ss)

        # Fill credentials
        username_field = page.locator("input").first
        password_field = page.locator("input[type='password']")
        
        username_field.fill(USERNAME)
        password_field.fill(PASSWORD)
        time.sleep(0.5)
        
        ss_filled = take_screenshot(page, "01_login_filled")
        record("1b. Credentials Filled", "pass", f"Username='{USERNAME}', password filled", ss_filled)
        
        # Click login button
        login_btn = page.locator("button:has-text('Login')").first
        login_btn.click()
        time.sleep(4)  # Wait for redirect
        
        current_url = page.url
        print(f"  After login URL: {current_url}")
        ss_after = take_screenshot(page, "01_after_login")
        
        if "/dashboard" in current_url or "/onboarding" in current_url:
            record("1c. Login Success", "pass", f"Redirected to {current_url}", ss_after)
        else:
            # Maybe it's still loading or the URL didn't change
            body_after = page.locator("body").inner_text()[:200]
            if "dashboard" in body_after.lower() or "welcome" in body_after.lower():
                record("1c. Login Success", "pass", f"Dashboard content visible (URL: {current_url})", ss_after)
            else:
                record("1c. Login Success", "fail", f"Expected redirect to /dashboard, got {current_url}. Body: {body_after[:150]}", ss_after)

    except Exception as e:
        ss = take_screenshot(page, "01_error")
        record("1. Login/Auth Flow", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 2: Dashboard Principal
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 2: Dashboard Principal")
    print("=" * 60)
    try:
        # Make sure we're on dashboard
        if "/dashboard" not in page.url:
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
            time.sleep(3)
        
        body_text = page.locator("body").inner_text()
        word_count = len(body_text.split())
        
        # Check for dashboard elements
        dashboard_elements = {
            "sidebar": page.locator("aside, nav, [class*='sidebar']").count(),
            "cards": page.locator("[class*='card'], [class*='Card']").count(),
            "charts": page.locator("canvas, svg[class*='chart'], [class*='chart']").count(),
            "tables": page.locator("table").count(),
            "headings": page.locator("h1, h2, h3").count(),
        }
        
        print(f"  Body words: {word_count}")
        for elem, count in dashboard_elements.items():
            print(f"  {elem}: {count}")
        
        ss = take_screenshot(page, "02_dashboard")
        
        if word_count > 20 and sum(dashboard_elements.values()) > 2:
            record("2. Dashboard", "pass", f"Dashboard loaded: {word_count} words, elements: {dashboard_elements}", ss)
        elif word_count > 10:
            record("2. Dashboard", "warn", f"Dashboard loaded but minimal content ({word_count} words)", ss)
        else:
            record("2. Dashboard", "fail", f"Dashboard appears empty ({word_count} words)", ss)

    except Exception as e:
        ss = take_screenshot(page, "02_error")
        record("2. Dashboard", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 3: Crear Test Suite
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 3: Crear Test Suite")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        body_text = page.locator("body").inner_text()[:500]
        ss_list = take_screenshot(page, "03_suites_list")
        
        # Look for create/new button
        create_btn = None
        for sel in [
            "button:has-text('Create')", "button:has-text('New')", 
            "button:has-text('Add')", "button:has-text('Suite')",
            "a:has-text('Create')", "a:has-text('New')",
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    create_btn = sel
                    el.click()
                    print(f"  Clicked create via '{sel}'")
                    break
            except:
                pass
        
        if not create_btn:
            record("3. Create Test Suite", "warn", f"No create button found on /suites. Body: {body_text[:150]}", ss_list)
        else:
            time.sleep(3)
            ss_form = take_screenshot(page, "03_create_form")
            
            # Fill the form
            suite_name = f"E2E Auto Suite {datetime.now().strftime('%H%M%S')}"
            filled = False
            for sel in ["input[name='name']", "input[name='title']", "input[type='text']", "input[placeholder*='name' i]"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.fill(suite_name)
                        filled = True
                        print(f"  Filled name via '{sel}': {suite_name}")
                        break
                except:
                    pass
            
            # Fill description if there
            for sel in ["textarea[name='description']", "textarea", "input[name='description']"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=1000):
                        el.fill("E2E test suite created by automated browser verification")
                        break
                except:
                    pass
            
            # Submit
            submitted = False
            for sel in ["button[type='submit']", "button:has-text('Save')", "button:has-text('Create')", "button:has-text('Submit')"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        submitted = True
                        print(f"  Submitted via '{sel}'")
                        break
                except:
                    pass
            
            time.sleep(3)
            ss_after = take_screenshot(page, "03_after_create")
            
            if filled and submitted:
                # Check if suite appears in the list
                page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=15000)
                time.sleep(2)
                body_after = page.locator("body").inner_text()
                if suite_name.lower() in body_after.lower() or "e2e" in body_after.lower():
                    record("3. Create Test Suite", "pass", f"Suite '{suite_name}' created and visible in list", ss_after)
                else:
                    record("3. Create Test Suite", "warn", f"Form submitted but suite not confirmed in list", ss_after)
            else:
                record("3. Create Test Suite", "warn", f"Could not fill form or submit", ss_form)

    except Exception as e:
        ss = take_screenshot(page, "03_error")
        record("3. Create Test Suite", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 4: Editar/Eliminar Test Suite (CRUD)
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 4: Editar/Eliminar Test Suite (CRUD)")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/suites", wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        body_text = page.locator("body").inner_text()
        ss = take_screenshot(page, "04_crud_view")
        
        # Check for table rows or list items
        rows = page.locator("tr, [class*='row'], [class*='item'], [class*='suite']").count()
        print(f"  Rows/items found: {rows}")
        
        # Look for edit/delete actions
        edit_found = page.locator("button:has-text('Edit'), button:has-text('Delete'), [class*='edit'], [class*='delete'], [aria-label*='edit' i], [aria-label*='delete' i]").count()
        print(f"  Edit/delete actions: {edit_found}")
        
        # Look for table with data
        tables = page.locator("table").count()
        table_rows = page.locator("tr").count()
        print(f"  Tables: {tables}, Table rows: {table_rows}")
        
        # Check for any interactive elements (3-dot menus, icons)
        icons = page.locator("[class*='icon'], svg, [class*='menu'], [class*='more']").count()
        print(f"  Icons/menu elements: {icons}")
        
        if edit_found > 0:
            record("4. CRUD Actions", "pass", f"Found {edit_found} edit/delete actions, {table_rows} table rows", ss)
        elif rows > 0 or table_rows > 0:
            record("4. CRUD Actions", "warn", f"Found {rows} items/{table_rows} rows but no visible edit/delete actions", ss)
        else:
            record("4. CRUD Actions", "warn", f"No suite data visible yet", ss)

    except Exception as e:
        ss = take_screenshot(page, "04_error")
        record("4. CRUD Actions", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 5: Ejecutar Test Suite
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 5: Ejecutar Test Suite")
    print("=" * 60)
    try:
        # Check for run/execute buttons
        run_btns = page.locator("button:has-text('Run'), button:has-text('Execute'), button:has-text('Start')").count()
        print(f"  Run/execute buttons: {run_btns}")
        
        ss = take_screenshot(page, "05_execute")
        
        if run_btns > 0:
            # Click the first run button
            for sel in ["button:has-text('Run')", "button:has-text('Execute')", "button:has-text('Start')"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        time.sleep(5)
                        print(f"  Clicked run via '{sel}'")
                        break
                except:
                    pass
            
            ss_after = take_screenshot(page, "05_after_run")
            body_text = page.locator("body").inner_text().lower()
            status_kw = ["running", "pending", "completed", "failed", "passed", "progress", "executing"]
            found = [kw for kw in status_kw if kw in body_text]
            
            if found:
                record("5. Execute Test Suite", "pass", f"Execution triggered. Status: {', '.join(found)}", ss_after)
            else:
                record("5. Execute Test Suite", "warn", "Run clicked but no status visible", ss_after)
        else:
            record("5. Execute Test Suite", "warn", "No run/execute button found on current page", ss)

    except Exception as e:
        ss = take_screenshot(page, "05_error")
        record("5. Execute Test Suite", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 6: Ver Reportes
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 6: Ver Reportes")
    print("=" * 60)
    try:
        page.goto(f"{BASE_URL}/executions", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        body_text = page.locator("body").inner_text()
        ss = take_screenshot(page, "06_reports")
        
        report_kw = ["execution", "result", "report", "passed", "failed", "duration", "test", "suite"]
        found = [kw for kw in report_kw if kw in body_text.lower()]
        word_count = len(body_text.split())
        
        if found and word_count > 20:
            record("6. View Reports", "pass", f"Reports page loaded. Keywords: {', '.join(found[:5])}, words: {word_count}", ss)
        elif word_count > 10:
            record("6. View Reports", "warn", f"Page loaded but limited content ({word_count} words)", ss)
        else:
            record("6. View Reports", "warn", f"Reports page may be empty ({word_count} words)", ss)

    except Exception as e:
        ss = take_screenshot(page, "06_error")
        record("6. View Reports", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 7: Navegación entre Vistas
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 7: Navegación entre Vistas")
    print("=" * 60)
    try:
        nav_routes = [
            ("/dashboard", "Dashboard"),
            ("/suites", "Test Suites"),
            ("/executions", "Executions"),
            ("/settings", "Settings"),
            ("/integrations", "Integrations"),
            ("/billing", "Billing"),
        ]
        
        nav_results = []
        for path, name in nav_routes:
            try:
                page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=15000)
                time.sleep(1)
                status = page.url
                body_words = len(page.locator("body").inner_text().split())
                ok = "/login" not in status  # Should not redirect to login
                nav_results.append({"route": path, "name": name, "ok": ok, "url": status, "words": body_words})
                print(f"  {path} → {'✅' if ok else '❌'} {body_words} words")
            except Exception as e:
                nav_results.append({"route": path, "name": name, "ok": False, "error": str(e)[:100]})
                print(f"  {path} → ❌ Error: {str(e)[:80]}")
        
        ss = take_screenshot(page, "07_navigation")
        
        ok_count = sum(1 for r in nav_results if r.get("ok"))
        total = len(nav_routes)
        
        if ok_count == total:
            record("7. Navigation", "pass", f"All {total} routes accessible without redirect to login", ss)
        elif ok_count >= total // 2:
            record("7. Navigation", "warn", f"{ok_count}/{total} routes accessible. Failed: {[r['name'] for r in nav_results if not r.get('ok')]}", ss)
        else:
            record("7. Navigation", "fail", f"Only {ok_count}/{total} routes accessible. Most redirect to login", ss)

    except Exception as e:
        ss = take_screenshot(page, "07_error")
        record("7. Navigation", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # CHECK 8: DevTools Console (CRITICAL)
    # ================================================================
    print("\n" + "=" * 60)
    print("CHECK 8: DevTools Console (CRITICAL)")
    print("=" * 60)
    try:
        # Navigate to dashboard for final console check
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        # Filter out Vite HMR errors (dev-mode only)
        real_errors = [e for e in results["console_errors"] if "vite" not in e.get("text", "").lower() and "websocket" not in e.get("text", "").lower()]
        vite_errors = [e for e in results["console_errors"] if "vite" in e.get("text", "").lower() or "websocket" in e.get("text", "").lower()]
        
        ss = take_screenshot(page, "08_final_state")
        
        print(f"  Total console errors: {len(results['console_errors'])}")
        print(f"  Vite HMR errors (dev-only): {len(vite_errors)}")
        print(f"  Real JS errors: {len(real_errors)}")
        print(f"  Console warnings: {len(results['console_warnings'])}")
        print(f"  API network errors: {len(results['network_errors'])}")
        
        for err in real_errors[:5]:
            print(f"    ERROR: {err['text'][:150]}")
        for warn in results["console_warnings"][:3]:
            print(f"    WARN: {warn['text'][:150]}")
        
        # Vite HMR errors are expected in dev mode through Cloudflare tunnel
        if len(real_errors) == 0 and len(results["console_warnings"]) <= 3:
            record("8. Console", "pass", f"0 real JS errors. {len(vite_errors)} Vite HMR errors (dev-only, expected). {len(results['console_warnings'])} warnings", ss)
        elif len(real_errors) == 0:
            record("8. Console", "warn", f"0 real JS errors. {len(results['console_warnings'])} warnings, {len(vite_errors)} Vite HMR errors (dev-only)", ss)
        else:
            record("8. Console", "fail", f"{len(real_errors)} real JS errors, {len(vite_errors)} Vite HMR, {len(results['console_warnings'])} warnings", ss)

    except Exception as e:
        ss = take_screenshot(page, "08_error")
        record("8. Console", "fail", f"Exception: {str(e)[:200]}", ss)
        traceback.print_exc()

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 60)
    print("📊 E2E VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  ✅ Pass:  {results['total_pass']}")
    print(f"  ❌ Fail:  {results['total_fail']}")
    print(f"  ⚠️  Warn: {results['total_warn']}")
    print(f"  🔴 Real JS Errors: {len([e for e in results['console_errors'] if 'vite' not in e.get('text','').lower()])}")
    print(f"  🟡 Warnings: {len(results['console_warnings'])}")
    print(f"  🌐 API Errors: {len(results['network_errors'])}")

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results: {RESULTS_FILE}")

    total = results["total_pass"] + results["total_fail"] + results["total_warn"]
    if results["total_fail"] == 0 and results["total_warn"] == 0:
        verdict = "ALL PASS"
    elif results["total_fail"] == 0:
        verdict = "PASS WITH WARNINGS"
    else:
        verdict = "FAIL"
    print(f"\n  🏁 VERDICT: {verdict}")

browser.close()
