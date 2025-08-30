import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://zimaev.github.io/text_input/")
    page.get_by_role("textbox", name="Email address").click()
    page.get_by_role("textbox", name="Email address").fill("gfghfhfh")
    page.get_by_role("textbox", name="Username").click()
    page.get_by_role("textbox", name="Username").click()
    page.get_by_role("textbox", name="Username").fill("rererererere")
    page.get_by_role("textbox", name="Password").click()
    page.get_by_role("textbox", name="Password").fill("fghdghsdgsdhyedh")
    page.get_by_text("Check me out").click()
    page.get_by_role("button", name="Submit").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)