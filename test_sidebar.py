import re
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:8501")
        await page.wait_for_selector('[data-testid="stSidebar"]')
        
        # Get expanded state HTML
        expanded_html = await page.evaluate("document.querySelector('[data-testid=\"stSidebar\"]').outerHTML")
        expanded_style = await page.evaluate("window.getComputedStyle(document.querySelector('[data-testid=\"stSidebar\"]')).transform")
        
        # Click close button
        await page.click('[data-testid="collapsedControl"]')
        await asyncio.sleep(1)
        
        # Get collapsed state HTML
        collapsed_html = await page.evaluate("document.querySelector('[data-testid=\"stSidebar\"]').outerHTML")
        collapsed_style = await page.evaluate("window.getComputedStyle(document.querySelector('[data-testid=\"stSidebar\"]')).transform")
        
        print(f"EXPANDED TRANSFORM: {expanded_style}")
        print(f"COLLAPSED TRANSFORM: {collapsed_style}")
        with open("sidebar_expanded.html", "w") as f: f.write(expanded_html)
        with open("sidebar_collapsed.html", "w") as f: f.write(collapsed_html)
        
        await browser.close()

asyncio.run(main())
