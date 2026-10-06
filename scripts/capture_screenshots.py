"""Drives the real Streamlit UI (backend on :8000, UI on :8501, Ollama running, empty tara.db) and saves
screenshots of each step to evaluation/results/screenshots/. Used as evidence in the report.

    python -m scripts.capture_screenshots
"""
import os

from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation", "results", "screenshots")
os.makedirs(OUT, exist_ok=True)
LLM_WAIT = 240_000


def shot(page, name):
    page.wait_for_timeout(1500)
    try:
        wait_idle(page)
    except Exception:
        pass
    page.wait_for_timeout(1000)
    page.screenshot(path=os.path.join(OUT, name), full_page=False)
    print("saved", name)


def tab(page, label):
    page.get_by_role("tab", name=label).click()
    page.wait_for_timeout(1500)


def wait_idle(page, timeout=60_000):
    page.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=timeout)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 1150})
    page.goto("http://localhost:8501")
    page.wait_for_selector("text=Extract Assets")

    # 1. assets
    page.get_by_role("button", name="Extract Assets").click()
    page.wait_for_selector("text=Extracted", timeout=LLM_WAIT)
    shot(page, "01_assets_extracted.png")

    # 2. threats for the Gateway ECU
    tab(page, "2. Threats")
    page.wait_for_selector("[data-testid='stSelectbox']:visible", timeout=60_000)
    page.locator("[data-testid='stSelectbox']:visible").first.click()
    page.get_by_role("option", name="Gateway ECU").click()
    page.get_by_role("button", name="Generate Threats").click()
    page.wait_for_selector("text=Generated", timeout=LLM_WAIT)
    page.wait_for_timeout(1500)
    shot(page, "02_threats_with_citations.png")

    # 3. risk assessment for threat 1 (Impact HIGH, Feasibility MEDIUM)
    tab(page, "3. Risk Assessment")
    page.wait_for_selector("[data-testid='stSelectbox']:visible", timeout=60_000)
    selects = page.locator("[data-testid='stSelectbox']:visible")
    selects.nth(0).click()
    page.get_by_role("option", name="HIGH").click()
    selects.nth(1).click()
    page.get_by_role("option", name="MEDIUM").click()
    page.get_by_role("button", name="Submit Risk Assessment").click()
    page.wait_for_selector("text=Risk Level", timeout=30_000)
    shot(page, "03_risk_level.png")

    # 4. mitigation, draft then approve
    tab(page, "4. Mitigations")
    page.get_by_role("button", name="Suggest Mitigation").click()
    page.wait_for_selector("text=Mitigation drafted", timeout=LLM_WAIT)
    shot(page, "04_mitigation_draft.png")
    page.get_by_role("button", name="Approve Mitigation").click()
    page.wait_for_selector("text=Mitigation approved", timeout=30_000)
    shot(page, "05_mitigation_approved.png")

    # 5. traceability report
    tab(page, "5. Traceability Report")
    page.get_by_role("button", name="Generate Report").click()
    page.wait_for_selector("table:visible", timeout=30_000)
    shot(page, "06_traceability_report.png")
    browser.close()
