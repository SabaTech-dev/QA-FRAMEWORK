#!/usr/bin/env python3
"""
Deep exploration of QA-FRAMEWORK to understand the actual app structure.
"""
import os, json, time
from invisible_playwright import InvisiblePlaywright

BASE_URL = "https://qa.sabatech.dev"
SCREENSHOT_DIR = os.path.expanduser("~/repos/QA-FRAMEWORK/reports/e2e")
TIMEOUT = 30000

ip = InvisiblePlaywright(seed=42, headless=True, humanize=True)

with ip as browser:
    page = browser.new_page(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
    )

    console_errors = []
    def on_console(msg):
        if msg.type == "error":
            console_errors.append(msg.text[:200])
    page.on("console", on_console)

    # Step 1: Load the landing page and get ALL links
    print("=" * 60)
    print("STEP 1: Landing page analysis")
    print("=" * 60)
    page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
    time.sleep(3)
    
    title = page.title()
    print(f"Title: {title}")
    
    # Get ALL links on the page
    links = page.locator("a")
    link_count = links.count()
    print(f"Total links: {link_count}")
    for i in range(min(link_count, 30)):
        try:
            href = links.nth(i).get_attribute("href")
            text = links.nth(i).inner_text().strip()
            if text:
                print(f"  [{i}] {text[:60]} → {href}")
        except:
            pass

    # Get ALL buttons
    buttons = page.locator("button")
    btn_count = buttons.count()
    print(f"\nTotal buttons: {btn_count}")
    for i in range(min(btn_count, 20)):
        try:
            text = buttons.nth(i).inner_text().strip()
            cls = buttons.nth(i).get_attribute("class")
            if text:
                print(f"  [{i}] '{text[:50]}' class={cls[:60] if cls else 'none'}")
        except:
            pass

    # Get page HTML structure (first 3000 chars)
    body_html = page.locator("body").inner_html()[:3000]
    print(f"\nBody HTML (first 3000):\n{body_html[:3000]}")
    
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "explore_01_landing.png"), full_page=True)

    # Step 2: Try to find and navigate to the actual app
    print("\n" + "=" * 60)
    print("STEP 2: Looking for app entry points")
    print("=" * 60)
    
    # Common paths to try
    paths_to_try = [
        "/app", "/dashboard", "/login", "/auth", "/signin", "/signup",
        "/home", "/main", "/workspace", "/projects",
    ]
    
    for path in paths_to_try:
        try:
            resp = page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=15000)
            time.sleep(1)
            new_title = page.title()
            new_url = page.url
            body_text = page.locator("body").inner_text()[:200]
            print(f"  {path} → {resp.status} | title='{new_title}' | url='{new_url}'")
            print(f"    Body: {body_text[:150]}")
            
            # Check if this is different from landing
            new_links = page.locator("a").count()
            new_buttons = page.locator("button").count()
            print(f"    Links: {new_links}, Buttons: {new_buttons}")
            
            if new_title != title or "login" in new_url.lower() or "dashboard" in new_url.lower():
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"explore_02_{path.replace('/', '_')}.png"), full_page=True)
        except Exception as e:
            print(f"  {path} → ERROR: {str(e)[:100]}")

    # Step 3: Check if there's a React root with client-side routing
    print("\n" + "=" * 60)
    print("STEP 3: React SPA analysis")
    print("=" * 60)
    page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
    time.sleep(2)
    
    # Check for React root
    react_root = page.locator("#root, #app, [data-reactroot]").count()
    print(f"React root elements: {react_root}")
    
    # Check for React Router
    page.evaluate("window.__reactRouterVersion || 'no router detected'")
    
    # Check all script tags
    scripts = page.locator("script[src]")
    script_count = scripts.count()
    print(f"\nExternal scripts: {script_count}")
    for i in range(min(script_count, 15)):
        src = scripts.nth(i).get_attribute("src")
        if src:
            print(f"  {src[:100]}")

    # Check for hash-based routing or any onclick handlers
    all_elements = page.locator("[onclick], [data-href], [data-link]")
    print(f"\nElements with click handlers: {all_elements.count()}")

    # Check meta tags for clues
    meta_desc = page.locator("meta[name='description']").first.get_attribute("content")
    print(f"\nMeta description: {meta_desc}")

    # Final: get the full page text
    full_text = page.locator("body").inner_text()
    print(f"\nFull page text ({len(full_text)} chars):")
    print(full_text[:1000])

    print(f"\nConsole errors so far: {len(console_errors)}")
    for err in console_errors[:3]:
        print(f"  {err[:150]}")

    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "explore_03_final.png"), full_page=True)
    print("\n✅ Deep exploration complete")
