"""Helpers for working with Playwright pages.

Supports two location strategies that we try in order:
 1. A list of candidate CSS selectors (from field_map).
 2. Accessible label-based locators (Playwright get_by_label), which survive
    unknown name/id attributes on a React SPA.
"""

from __future__ import annotations

import unicodedata

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeout


def _normalize(text: str) -> str:
    """Lowercase + strip accents, for tolerant text matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.strip().lower()


async def find_first(
    page: Page, selectors: list[str], timeout: int = 4000
) -> Locator | None:
    """Return a locator for the first selector that becomes visible, else None."""
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return locator
        except PlaywrightTimeout:
            continue
    return None


async def locate(
    page: Page,
    selectors: list[str] | None = None,
    label: str | None = None,
    timeout: int = 4000,
) -> Locator | None:
    """Find an element via CSS selectors first, then by accessible label."""
    if selectors:
        loc = await find_first(page, selectors, timeout=timeout)
        if loc is not None:
            return loc
    if label:
        try:
            loc = page.get_by_label(label, exact=False).first
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except PlaywrightTimeout:
            return None
    return None


async def fill_field(
    page: Page,
    value: str,
    selectors: list[str] | None = None,
    label: str | None = None,
    timeout: int = 4000,
) -> bool:
    loc = await locate(page, selectors, label, timeout)
    if loc is None:
        return False
    await loc.fill(str(value))
    return True


async def click_first(page: Page, selectors: list[str], timeout: int = 4000) -> bool:
    loc = await find_first(page, selectors, timeout=timeout)
    if loc is None:
        return False
    await loc.click()
    return True


async def select_option_loose(
    page: Page,
    value: str,
    selectors: list[str] | None = None,
    label: str | None = None,
    timeout: int = 4000,
) -> bool:
    """Select an <option> matching `value` case/accent-insensitively."""
    loc = await locate(page, selectors, label, timeout)
    if loc is None:
        return False
    # Try exact label, then exact value, then loose match against option texts.
    for attempt in (
        lambda: loc.select_option(label=value),
        lambda: loc.select_option(value=value),
    ):
        try:
            await attempt()
            return True
        except Exception:
            pass
    try:
        target = _normalize(value)
        options = await loc.locator("option").all()
        for opt in options:
            text = (await opt.text_content()) or ""
            opt_value = (await opt.get_attribute("value")) or ""
            if _normalize(text) == target or _normalize(opt_value) == target:
                if opt_value:
                    await loc.select_option(value=opt_value)
                else:
                    await loc.select_option(label=text)
                return True
    except Exception:
        return False
    return False


async def choose_radio(
    page: Page, question_label: str, option_text: str, timeout: int = 4000
) -> bool:
    """Click the radio option `option_text` (e.g. 'Sim'/'Não')."""
    # Prefer a radio whose own label matches the option text.
    try:
        loc = page.get_by_label(option_text, exact=True).first
        await loc.wait_for(state="visible", timeout=timeout)
        await loc.check()
        return True
    except Exception:
        pass
    # Fallback: click the visible text near the radios.
    try:
        loc = page.get_by_text(option_text, exact=True).first
        await loc.wait_for(state="visible", timeout=timeout)
        await loc.click()
        return True
    except Exception:
        return False


async def is_present(page: Page, selectors: list[str], timeout: int = 4000) -> bool:
    return (await find_first(page, selectors, timeout=timeout)) is not None
