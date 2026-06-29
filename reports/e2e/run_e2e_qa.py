#!/usr/bin/env python3
"""
QA-FRAMEWORK E2E Browser Verification
Card: 509b9e0e-7ff2-47dd-a14e-e9010050d66a
Stack: invisible-playwright (Firefox 150 patcheado)
"""
import sys, os, json, time, traceback
from datetime import datetime
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")
RESULTS_FILE = os.path.join(SCREENSHOT_DIR, "e2e_results.json")
TIMEOUT = 30000  # 30s per operation

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
    entry = {
        "check": check_name,
        "status": status,
        "detail": detail,
        "screenshot": screenshot,
    }
    results["checks"].append(entry)
    if status == "pass":
        results["total_pass"] += 1
    elif status == "fail":
        results["total_fail"] += 1
    else:
        results["total_warn"] += 1
    icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    print(f"  {icon} {check_name}: {detail}")
    return entry

def main():
    print(f"\n🧪 QA-FRAMEWORK E2E Verification")
    print(f"   URL: {BASE_URL}")
    print(f"   Time: {results['timestamp']}\n")

    ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)
    
    with ip as browser:
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
        )

        # Capture console and network errors
        def on_console(msg):
            entry = {"type": msg.type, "text": msg.text}
            if msg.type in ("error",):
                results["console_errors"].append(entry)
            elif msg.type in ("warning",):
                results["console_warnings"].append(entry)

        page.on("console", on_console)

        def on_request_failed(req):
            results["network_errors"].append({
                "url": req.url, "status": "failed", "failure": str(req.failure)
            })
        page.on("requestfailed", on_request_failed)

        def on_response(resp):
            if resp.status >= 400:
                results["network_errors"].append({
                    "url": resp.url, "status": resp.status
                })
        page.on("response", on_response)

        # ======== CHECK 1: Load page + Login/Auth flow ========
        print("=" * 60)
        print("CHECK 1: Page Load + Login/Auth Flow")
        print("=" * 60)
        try:
            resp = page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
            status_code = resp.status if resp else 0
            print(f"  HTTP Status: {status_code}")
            time.sleep(2)

            title = page.title()
            print(f"  Page Title: {title}")

            ss = take_screenshot(page, "01_initial_load")

            if status_code == 200 and "QA" in title:
                record("1. Page Load", "pass", f"HTTP {status_code}, title='{title}'", ss)
            else:
                record("1. Page Load", "warn", f"HTTP {status_code}, title='{title}'", ss)

            # Look for login form or auth elements
            login_selectors = [
                "input[type='email']", "input[type='password']",
                "button:has-text('Login')", "button:has-text('Sign')",
                "input[name='email']", "input[name='username']",
                "form",
            ]
            found_login = None
            for sel in login_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        found_login = sel
                        break
                except:
                    pass

            if found_login:
                ss2 = take_screenshot(page, "01_login_form")
                record("1. Login Form", "pass", f"Login form found via '{found_login}'", ss2)
            else:
                # Maybe already logged in or SPA
                nav_selectors = ["nav", "[role='navigation']", "aside", ".sidebar"]
                found_nav = None
                for sel in nav_selectors:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            found_nav = sel
                            break
                    except:
                        pass
                
                if found_nav:
                    ss2 = take_screenshot(page, "01_authenticated")
                    record("1. Login Form", "pass", f"No login form — already authenticated (nav: '{found_nav}')", ss2)
                else:
                    body_text = page.locator("body").inner_text()[:300]
                    ss2 = take_screenshot(page, "01_no_login")
                    record("1. Login Form", "warn", f"No login form, no nav. Body: {body_text[:150]}", ss2)

        except Exception as e:
            ss = take_screenshot(page, "01_error")
            record("1. Page Load", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 2: Dashboard principal ========
        print("\n" + "=" * 60)
        print("CHECK 2: Dashboard Principal")
        print("=" * 60)
        try:
            time.sleep(2)
            
            dashboard_selectors = [
                "[class*='dashboard']", "[class*='card']", "[class*='stat']",
                "[class*='metric']", "[class*='chart']", "h1", "h2", "main",
            ]
            found_elements = []
            for sel in dashboard_selectors:
                try:
                    count = page.locator(sel).count()
                    if count > 0:
                        found_elements.append(f"{sel}({count})")
                except:
                    pass

            print(f"  Dashboard elements: {', '.join(found_elements[:10])}")

            body_text = page.locator("body").inner_text()
            word_count = len(body_text.split())
            has_numbers = any(c.isdigit() for c in body_text)
            print(f"  Body: ~{word_count} words, has_numbers={has_numbers}")

            ss = take_screenshot(page, "02_dashboard")
            
            if found_elements and word_count > 10:
                record("2. Dashboard", "pass", f"Loaded: {', '.join(found_elements[:5])}", ss)
            elif found_elements:
                record("2. Dashboard", "warn", f"Minimal content: {', '.join(found_elements[:3])}", ss)
            else:
                record("2. Dashboard", "fail", "No dashboard elements found", ss)

        except Exception as e:
            ss = take_screenshot(page, "02_error")
            record("2. Dashboard", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 3: Crear test suite ========
        print("\n" + "=" * 60)
        print("CHECK 3: Crear Test Suite")
        print("=" * 60)
        suite_name = f"E2E Suite {datetime.now().strftime('%H%M%S')}"
        try:
            create_selectors = [
                "button:has-text('Create')", "button:has-text('New')",
                "button:has-text('Add')", "[class*='create']",
                "a:has-text('Test Suite')", "a:has-text('Create')",
            ]
            clicked = False
            for sel in create_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        clicked = True
                        print(f"  Clicked create via '{sel}'")
                        break
                except:
                    pass

            if not clicked:
                for path in ["/test-suites", "/tests", "/suites", "/create"]:
                    try:
                        page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=10000)
                        time.sleep(1)
                        forms = page.locator("form").count()
                        if forms > 0:
                            clicked = True
                            print(f"  Found form at {path}")
                            break
                    except:
                        pass

            time.sleep(2)
            ss = take_screenshot(page, "03_create_attempt")

            # Try to fill name field
            name_selectors = [
                "input[name='name']", "input[name='title']",
                "input[placeholder*='name' i]", "input[placeholder*='suite' i]",
                "input[type='text']",
            ]
            filled = False
            for sel in name_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.fill(suite_name)
                        filled = True
                        print(f"  Filled name via '{sel}'")
                        break
                except:
                    pass

            if filled:
                submit_selectors = [
                    "button[type='submit']", "button:has-text('Save')",
                    "button:has-text('Create')", "button:has-text('Submit')",
                ]
                submitted = False
                for sel in submit_selectors:
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
                ss2 = take_screenshot(page, "03_after_submit")
                body_text = page.locator("body").inner_text().lower()
                
                if suite_name.lower() in body_text or "success" in body_text or "created" in body_text:
                    record("3. Create Test Suite", "pass", f"Suite '{suite_name}' created", ss2)
                else:
                    record("3. Create Test Suite", "warn", f"Submitted but success unconfirmed", ss2)
            else:
                record("3. Create Test Suite", "warn", "No create form found", ss)

        except Exception as e:
            ss = take_screenshot(page, "03_error")
            record("3. Create Test Suite", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 4: Editar/Eliminar (CRUD) ========
        print("\n" + "=" * 60)
        print("CHECK 4: Editar/Eliminar Test Suite (CRUD)")
        print("=" * 60)
        try:
            action_selectors = [
                "[class*='edit']", "[class*='delete']",
                "button[aria-label*='edit' i]", "button[aria-label*='delete' i]",
                "[data-testid*='edit']", "[data-testid*='delete']",
            ]
            found_actions = []
            for sel in action_selectors:
                try:
                    count = page.locator(sel).count()
                    if count > 0:
                        found_actions.append(f"{sel}({count})")
                except:
                    pass

            row_count = page.locator("tr").count()
            ss = take_screenshot(page, "04_crud")
            print(f"  Actions: {', '.join(found_actions[:5]) if found_actions else 'none'}")
            print(f"  Table rows: {row_count}")

            if found_actions or row_count > 0:
                detail = f"{len(found_actions)} action types, {row_count} rows"
                record("4. CRUD Actions", "pass", detail, ss)
            else:
                record("4. CRUD Actions", "warn", "No edit/delete UI visible", ss)

        except Exception as e:
            ss = take_screenshot(page, "04_error")
            record("4. CRUD Actions", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 5: Ejecutar test suite ========
        print("\n" + "=" * 60)
        print("CHECK 5: Ejecutar Test Suite")
        print("=" * 60)
        try:
            run_selectors = [
                "button:has-text('Run')", "button:has-text('Execute')",
                "button:has-text('Start')", "[class*='run']",
            ]
            found_run = False
            for sel in run_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        found_run = True
                        print(f"  Clicked run via '{sel}'")
                        break
                except:
                    pass

            if found_run:
                time.sleep(5)
                ss = take_screenshot(page, "05_after_run")
                body_text = page.locator("body").inner_text().lower()
                status_kw = ["running", "pending", "completed", "failed", "passed", "results", "progress"]
                found_kw = [kw for kw in status_kw if kw in body_text]
                
                if found_kw:
                    record("5. Execute Test Suite", "pass", f"Execution triggered. Status: {', '.join(found_kw)}", ss)
                else:
                    record("5. Execute Test Suite", "warn", "Run clicked but no status visible", ss)
            else:
                ss = take_screenshot(page, "05_no_run")
                record("5. Execute Test Suite", "warn", "No run/execute button found", ss)

        except Exception as e:
            ss = take_screenshot(page, "05_error")
            record("5. Execute Test Suite", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 6: Ver reportes ========
        print("\n" + "=" * 60)
        print("CHECK 6: Ver Reportes")
        print("=" * 60)
        try:
            report_selectors = [
                "a:has-text('Reports')", "a:has-text('Report')",
                "[class*='report']", "a[href*='report']",
            ]
            found_report = False
            for sel in report_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        found_report = True
                        print(f"  Clicked reports via '{sel}'")
                        break
                except:
                    pass

            if not found_report:
                for path in ["/reports", "/report", "/executions", "/results"]:
                    try:
                        page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=10000)
                        time.sleep(1)
                        print(f"  Tried direct nav: {path}")
                        break
                    except:
                        pass

            time.sleep(2)
            ss = take_screenshot(page, "06_reports")
            body_text = page.locator("body").inner_text()
            report_kw = ["report", "execution", "result", "passed", "failed", "duration"]
            found_kw = [kw for kw in report_kw if kw in body_text.lower()]
            word_count = len(body_text.split())

            if found_kw and word_count > 10:
                record("6. View Reports", "pass", f"Reports show data. Keywords: {', '.join(found_kw)}", ss)
            else:
                record("6. View Reports", "warn", f"Reports may be empty. Words: {word_count}", ss)

        except Exception as e:
            ss = take_screenshot(page, "06_error")
            record("6. View Reports", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 7: Navegación entre vistas ========
        print("\n" + "=" * 60)
        print("CHECK 7: Navegación entre Vistas")
        print("=" * 60)
        try:
            nav_selectors = [
                "nav a", "aside a", "[role='navigation'] a",
                ".sidebar a", "[class*='nav'] a",
            ]
            nav_links = []
            for sel in nav_selectors:
                try:
                    links = page.locator(sel)
                    count = links.count()
                    for i in range(min(count, 10)):
                        try:
                            href = links.nth(i).get_attribute("href")
                            text = links.nth(i).inner_text()
                            if href and text.strip():
                                nav_links.append({"text": text.strip()[:50], "href": href})
                        except:
                            pass
                    if nav_links:
                        break
                except:
                    pass

            ss = take_screenshot(page, "07_navigation")
            print(f"  Nav links: {len(nav_links)}")
            for link in nav_links[:8]:
                print(f"    - {link['text']} → {link['href']}")

            # Test clicking a nav link
            clicked_nav = False
            if nav_links:
                for link in nav_links[1:]:
                    try:
                        if link["href"].startswith("http"):
                            page.goto(link["href"], wait_until="networkidle", timeout=10000)
                        elif link["href"].startswith("/"):
                            page.goto(f"{BASE_URL}{link['href']}", wait_until="networkidle", timeout=10000)
                        else:
                            continue
                        time.sleep(1)
                        clicked_nav = True
                        print(f"  Navigated to: {link['text']}")
                        ss2 = take_screenshot(page, "07_nav_clicked")
                        record("7. Navigation", "pass", f"Navigated to '{link['text']}'. Total items: {len(nav_links)}", ss2)
                        break
                    except:
                        pass

            if not clicked_nav and nav_links:
                record("7. Navigation", "warn", f"Found {len(nav_links)} links but couldn't navigate", ss)
            elif not nav_links:
                record("7. Navigation", "fail", "No navigation links found", ss)

        except Exception as e:
            ss = take_screenshot(page, "07_error")
            record("7. Navigation", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== CHECK 8: DevTools Console ========
        print("\n" + "=" * 60)
        print("CHECK 8: DevTools Console (CRITICAL)")
        print("=" * 60)
        try:
            print(f"  Console errors: {len(results['console_errors'])}")
            print(f"  Console warnings: {len(results['console_warnings'])}")
            print(f"  Network errors: {len(results['network_errors'])}")

            for err in results["console_errors"][:5]:
                print(f"    ERROR: {err['text'][:120]}")
            for warn in results["console_warnings"][:3]:
                print(f"    WARN: {warn['text'][:120]}")
            for net_err in results["network_errors"][:5]:
                print(f"    NET {net_err.get('status', 'fail')}: {net_err['url'][:100]}")

            page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
            time.sleep(2)
            ss = take_screenshot(page, "08_final_state")

            if len(results["console_errors"]) == 0 and len(results["console_warnings"]) == 0:
                record("8. Console", "pass", "0 errors, 0 warnings — clean! ✨", ss)
            elif len(results["console_errors"]) == 0:
                record("8. Console", "warn", f"0 errors, {len(results['console_warnings'])} warnings", ss)
            else:
                record("8. Console", "fail", f"{len(results['console_errors'])} errors, {len(results['console_warnings'])} warnings", ss)

        except Exception as e:
            ss = take_screenshot(page, "08_error")
            record("8. Console Check", "fail", f"Exception: {str(e)[:200]}", ss)
            traceback.print_exc()

        # ======== SUMMARY ========
        print("\n" + "=" * 60)
        print("📊 E2E VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"  ✅ Pass:  {results['total_pass']}")
        print(f"  ❌ Fail:  {results['total_fail']}")
        print(f"  ⚠️  Warn: {results['total_warn']}")
        print(f"  📸 Screenshots: {len([f for f in os.listdir(SCREENSHOT_DIR) if f.endswith('.png')])}")
        print(f"  🔴 Console Errors: {len(results['console_errors'])}")
        print(f"  🟡 Console Warnings: {len(results['console_warnings'])}")
        print(f"  🌐 Network Errors: {len(results['network_errors'])}")

        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to: {RESULTS_FILE}")

        total_checks = results["total_pass"] + results["total_fail"] + results["total_warn"]
        if results["total_fail"] == 0 and results["total_warn"] == 0:
            verdict = "ALL PASS"
        elif results["total_fail"] == 0:
            verdict = "PASS WITH WARNINGS"
        else:
            verdict = "FAIL"
        print(f"\n  🏁 VERDICT: {verdict}")

    return results


if __name__ == "__main__":
    results = main()
