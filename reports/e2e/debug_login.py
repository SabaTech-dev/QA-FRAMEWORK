#!/usr/bin/env python3
"""
Debug login redirect + console errors
"""
import os, json, time
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")

ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)

with ip as browser:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    console_msgs = []
    def on_console(msg):
        console_msgs.append({"type": msg.type, "text": msg.text[:200]})
    page.on("console", on_console)

    # Load login page
    page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Fill credentials
    page.locator("input").first.fill("e2e_v2")
    page.locator("input[type='password']").first.fill("TestPass123!")
    time.sleep(0.5)
    
    # Clear console before clicking login
    console_msgs.clear()
    
    # Click login
    page.locator("button:has-text('Login')").first.click()
    
    # Wait with polling to see URL changes
    for i in range(20):
        time.sleep(1)
        url = page.url
        print(f"  t={i+1}s URL={url}")
        if "/dashboard" in url or "/onboarding" in url:
            print(f"  ✅ Redirected at t={i+1}s")
            break
    
    # Show console messages during login
    print(f"\nConsole messages during login ({len(console_msgs)}):")
    for msg in console_msgs[:15]:
        print(f"  [{msg['type']}] {msg['text'][:150]}")
    
    # Check localStorage for auth
    auth_data = page.evaluate("localStorage.getItem('auth-storage')")
    print(f"\nlocalStorage auth-storage: {auth_data[:200] if auth_data else 'null'}")
    
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_login.png"), full_page=True)
    
    # If still on login, try navigating to dashboard directly
    if "/login" in page.url:
        print("\nStill on login. Trying direct navigation to /dashboard...")
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=15000)
        time.sleep(3)
        print(f"After direct nav: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_login_direct.png"), full_page=True)
        
        # Check auth state
        auth_data2 = page.evaluate("localStorage.getItem('auth-storage')")
        print(f"localStorage after nav: {auth_data2[:300] if auth_data2 else 'null'}")
    
    browser.close()
