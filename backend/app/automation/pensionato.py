"""Playwright automation for the real UNASP "Liberação de saída" form.

Flow: open site -> log in (profile + RA + senha) -> navigate to the liberacao
page -> fill the form (radio / selects / text / date / time / textarea) ->
submit -> screenshot as proof.

All site-specific selectors/labels live in `field_map.py`. Set `dry_run=True`
(or env DRY_RUN=1) to fill everything EXCEPT the final submit, for safe testing.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import Page, async_playwright

from app.automation import field_map as fm
from app.automation.browser import (
    _normalize as _norm,
    click_first,
    is_present,
    locate,
    select_option_loose,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Headless on Render is slower; allow extra time for the SPA to mount.
_FORM_READY_TIMEOUT_MS = 20_000 if settings.playwright_headless else 10_000
_POST_NAV_SETTLE_MS = 800 if settings.playwright_headless else 300
_FILL_RETRY_DELAY_MS = 2_000


@dataclass
class Credentials:
    username: str  # RA
    password: str
    profile: str | None = None


@dataclass
class SubmitResult:
    status: str  # "sent" | "failed"
    message: str
    screenshot_path: str | None = None


@dataclass
class FillReport:
    filled: int = 0
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def _format_fill_failure(report: FillReport, page_url: str) -> str:
    expected = len([k for k in fm.FORM if k not in report.skipped])
    parts = [
        f"Nenhum campo do formulário foi preenchido (0/{expected}). "
        f"Página: {page_url}. "
        "Confira o comprovante e os seletores em field_map.py."
    ]
    if report.failed:
        detail = "; ".join(f"{name}: {reason}" for name, reason in report.failed[:6])
        parts.append(f"Detalhes: {detail}.")
    return " ".join(parts)


def _screenshot_path(prefix: str) -> str:
    directory = Path(settings.screenshots_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return str(directory / f"{prefix}_{stamp}.png")


def _normalize_value(kind: str, value: str) -> str:
    """Coerce a payload value into the format the HTML input expects."""
    value = str(value).strip()
    if kind == "date":
        # Accept YYYY-MM-DD or DD/MM/YYYY -> emit YYYY-MM-DD.
        if "/" in value:
            parts = value.split("/")
            if len(parts) == 3 and len(parts[0]) == 2:
                d, m, y = parts
                return f"{y}-{m}-{d}"
        return value
    if kind == "time":
        return value[:5]  # HH:MM
    return value


async def _select_profile(page: Page, profile: str) -> None:
    """Select the login profile. The <select> uses option VALUES.

    Profile options can populate asynchronously, so retry until the selection
    sticks (input_value is non-empty) before giving up.
    """
    value = fm.PROFILE_VALUES.get(profile)
    select = await locate(page, fm.LOGIN["profile_select"], timeout=8000)
    if select is None:
        return
    for _ in range(10):
        try:
            if value:
                await select.select_option(value=value)
            else:
                await select_option_loose(page, profile, fm.LOGIN["profile_select"])
            if await select.input_value():
                return
        except Exception:
            pass
        await page.wait_for_timeout(500)
    # Final fallback: match by visible label, accent-insensitive.
    await select_option_loose(page, profile, fm.LOGIN["profile_select"])


async def _login(page: Page, credentials: Credentials) -> bool:
    await page.goto(settings.pensionato_base_url, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle")
    except Exception:
        pass

    # 1. Choose profile - this conditionally renders the RA/Senha inputs.
    if credentials.profile:
        await _select_profile(page, credentials.profile)

    # 2. Wait for the RA input to appear after the profile selection.
    user_loc = await locate(page, fm.LOGIN["username"], timeout=8000)
    pass_loc = await locate(page, fm.LOGIN["password"], timeout=8000)
    if user_loc is None or pass_loc is None:
        return False

    # 3. Fill credentials. Use fill, then fall back to typing to trigger React.
    await user_loc.fill("")
    await user_loc.fill(credentials.username)
    if (await user_loc.input_value()) != credentials.username:
        await user_loc.press_sequentially(credentials.username, delay=20)
    await pass_loc.fill(credentials.password)
    if not (await pass_loc.input_value()):
        await pass_loc.press_sequentially(credentials.password, delay=20)

    # 4. Submit and wait for the SPA to navigate away from the login screen.
    await click_first(page, fm.LOGIN["submit"])
    try:
        await page.wait_for_url(
            lambda url: "/dashboard" in url or url.rstrip("/") != settings.pensionato_base_url.rstrip("/"),
            timeout=10000,
        )
    except Exception:
        pass
    await page.wait_for_load_state("networkidle")
    if "/dashboard" in page.url:
        return True
    return await is_present(page, fm.LOGIN["post_login_marker"], timeout=6000)


async def _wait_for_form_ready(page: Page) -> bool:
    """Wait until the exit form (not just the login placeholder) has rendered."""
    markers = getattr(fm, "FORM_READY_MARKERS", [fm.FORM_READY])
    per_marker = max(_FORM_READY_TIMEOUT_MS // max(len(markers), 1), 4_000)
    for selector in markers:
        loc = page.locator(selector).first
        try:
            await loc.wait_for(state="visible", timeout=per_marker)
        except Exception as exc:
            logger.warning("Form not ready — marker %r: %s", selector, exc)
            return False
    await page.wait_for_timeout(_POST_NAV_SETTLE_MS)
    return True


# JS that reports every visible clock number with its on-screen center. The
# "inner" flag marks the 24h ring (00 + 13-23); the outer ring is 1-12.
_CLOCK_NODES_JS = """
() => {
    const sel = '.tp-ui-value-tips, .tp-ui-value-tips-24h, [role="option"]';
    const seen = new Set();
    const out = [];
    for (const el of document.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const text = (el.innerText || el.textContent || '').trim();
        if (!/^\\d{1,2}$/.test(text)) continue;
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        const key = text + ':' + Math.round(cx) + ':' + Math.round(cy);
        if (seen.has(key)) continue;
        seen.add(key);
        out.push({ text, inner: el.classList.contains('tp-ui-value-tips-24h'), cx, cy });
    }
    return out;
}
"""

async def _clock_nodes(page: Page) -> list[dict]:
    try:
        return await page.evaluate(_CLOCK_NODES_JS)
    except Exception:
        return []


def _angle_point(
    cx: float, cy: float, radius: float, units: float, per_unit_deg: float
) -> tuple[float, float]:
    """Point on a dial ring; 12/00 is at the top and angles grow clockwise."""
    theta = math.radians((units * per_unit_deg) % 360)
    return cx + radius * math.sin(theta), cy - radius * math.cos(theta)


def _ring_radius(nodes: list[dict], cx: float, cy: float, *, inner: bool) -> float:
    dists = [
        math.hypot(n["cx"] - cx, n["cy"] - cy) for n in nodes if n["inner"] == inner
    ]
    if not dists:
        dists = [math.hypot(n["cx"] - cx, n["cy"] - cy) for n in nodes]
    return sum(dists) / len(dists)


async def _click_clock_value(
    page: Page, value: int, *, is_minute: bool, prefer_angle: bool = False
) -> bool:
    """Click a clock number by pixel coordinates.

    A transparent overlay intercepts pointer events and resolves the selection
    from the pointer position (angle + ring), so we click the exact on-screen
    center of the target number. Hours 1-12 live on the outer ring; 00 and 13-23
    on the inner ring; minutes (multiples of 5) on the outer ring. For an
    unlabeled minute, or as a fallback, we compute the point geometrically from
    the dial center and ring radius.
    """
    nodes = await _clock_nodes(page)
    if not nodes:
        return False

    # Minutes sit on the outer ring; hours 00/13-23 sit on the inner ring.
    inner = (not is_minute) and (value == 0 or value >= 13)

    if not prefer_angle:
        targets = {str(value), f"{value:02d}"}
        for node in nodes:
            if node["text"] in targets and node["inner"] == inner:
                await page.mouse.click(node["cx"], node["cy"])
                return True

    cx = sum(n["cx"] for n in nodes) / len(nodes)
    cy = sum(n["cy"] for n in nodes) / len(nodes)
    radius = _ring_radius(nodes, cx, cy, inner=inner)
    if is_minute:
        x, y = _angle_point(cx, cy, radius, value, 6)
    else:
        x, y = _angle_point(cx, cy, radius, value % 12, 30)
    await page.mouse.click(x, y)
    return True


async def _set_clock_time(
    page: Page, hour: int, minute: int, *, prefer_angle: bool = False
) -> None:
    """Drive the custom 'tp-ui' clock dialog: pick hour, pick minute, confirm.

    Picking the hour auto-advances the dialog to minute mode. The digital boxes
    (.tp-ui-hour / .tp-ui-minutes) are unreliable mid-flow, so the caller checks
    the input's final value and retries with prefer_angle if needed.
    """
    ok = page.locator(fm.TIME_DIALOG["ok"]).first
    await ok.wait_for(state="visible", timeout=6000)
    # The overlay that captures clicks needs a moment to settle after the dialog
    # opens; clicking too soon is silently dropped (time stays at the default).
    await page.wait_for_timeout(600)

    await _click_clock_value(page, hour, is_minute=False, prefer_angle=prefer_angle)
    await page.wait_for_timeout(500)

    # Ensure minute mode (hour selection auto-advances, but click to be safe).
    try:
        await page.locator(".tp-ui-minutes").first.click()
    except Exception:
        pass
    await page.wait_for_timeout(400)

    await _click_clock_value(page, minute, is_minute=True, prefer_angle=prefer_angle)
    await page.wait_for_timeout(400)

    # Confirm ("Definir") and wait for the dialog to close.
    await ok.click()
    try:
        await ok.wait_for(state="hidden", timeout=3000)
    except Exception:
        pass
    await page.wait_for_timeout(150)


async def _fill_one(page: Page, cfg: dict, value: str) -> bool:
    """Fill a single field according to its positional spec."""
    kind = cfg["kind"]

    if kind == "radio":
        index = cfg["options"].get(str(value))
        if index is None:
            return False
        await page.locator(cfg["css"]).nth(index).check()
        return True

    loc = page.locator(cfg["css"]).nth(cfg.get("nth", 0))

    if kind == "select":
        # Try exact label, then value, then accent-insensitive match.
        for attempt in (
            lambda: loc.select_option(label=str(value)),
            lambda: loc.select_option(value=str(value)),
        ):
            try:
                await attempt()
                return True
            except Exception:
                pass
        target = _norm(str(value))
        for opt in await loc.locator("option").all():
            text = (await opt.text_content()) or ""
            opt_value = (await opt.get_attribute("value")) or ""
            if _norm(text) == target or _norm(opt_value) == target:
                if opt_value:
                    await loc.select_option(value=opt_value)
                else:
                    await loc.select_option(label=text)
                return True
        return False

    if kind == "date":
        await loc.fill(_normalize_value("date", value))
        return True

    if kind == "time":
        hhmm = _normalize_value("time", value)
        hh, mm = (hhmm.split(":") + ["00"])[:2]
        target = f"{int(hh):02d}:{int(mm):02d}"
        # First attempt clicks labeled numbers; retry with geometric angle if the
        # input did not end up at the requested time.
        for prefer_angle in (False, True):
            await loc.click()
            await _set_clock_time(page, int(hh), int(mm), prefer_angle=prefer_angle)
            if (await loc.input_value()).strip() == target:
                return True
        return True

    # text / textarea
    await loc.fill(str(value))
    return True


async def _fill_form(page: Page, form_data: dict) -> FillReport:
    """Fill every known field present in form_data (in spec order)."""
    report = FillReport()
    for name, cfg in fm.FORM.items():
        value = form_data.get(name)
        if value in (None, ""):
            report.skipped.append(name)
            continue
        try:
            if await _fill_one(page, cfg, value):
                report.filled += 1
            else:
                reason = f"locator/select failed for {cfg.get('kind')}"
                report.failed.append((name, reason))
                logger.warning("Field %s not filled: %s", name, reason)
        except Exception as exc:
            reason = str(exc) or exc.__class__.__name__
            report.failed.append((name, reason))
            logger.warning("Field %s raised: %s", name, reason, exc_info=True)
    return report


async def submit_exit(
    credentials: Credentials,
    form_data: dict,
    *,
    dry_run: bool | None = None,
) -> SubmitResult:
    """Log into UNASP and submit (or dry-run) an exit request."""
    if dry_run is None:
        dry_run = os.getenv("DRY_RUN", "0") in ("1", "true", "True")

    screenshot = _screenshot_path("exit")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.playwright_headless)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        try:
            if not await _login(page, credentials):
                await page.screenshot(path=screenshot)
                return SubmitResult(
                    "failed",
                    "Falha no login (verifique RA/senha/perfil ou os seletores em field_map.py).",
                    screenshot,
                )

            # Navigate straight to the exit form (SPA keeps the auth token).
            liberacao_url = urljoin(settings.pensionato_base_url, fm.LIBERACAO_PATH)
            await page.goto(liberacao_url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception:
                logger.warning("networkidle timeout on liberacao page; continuing")

            if not await _wait_for_form_ready(page):
                await page.screenshot(path=screenshot)
                return SubmitResult(
                    "failed",
                    f"Formulário de liberação não carregou a tempo. Página: {page.url}. "
                    "Veja o comprovante e field_map.py (FORM_READY_MARKERS).",
                    screenshot,
                )

            fill_report = await _fill_form(page, form_data)
            if fill_report.filled == 0:
                logger.warning(
                    "First fill pass filled 0 fields; retrying after %sms",
                    _FILL_RETRY_DELAY_MS,
                )
                await page.wait_for_timeout(_FILL_RETRY_DELAY_MS)
                fill_report = await _fill_form(page, form_data)

            if fill_report.filled == 0:
                await page.screenshot(path=screenshot)
                return SubmitResult(
                    "failed",
                    _format_fill_failure(fill_report, page.url),
                    screenshot,
                )

            filled = fill_report.filled

            if dry_run:
                await page.screenshot(path=screenshot)
                return SubmitResult(
                    "sent",
                    f"Dry run: {filled} campo(s) preenchido(s), formulário NÃO enviado.",
                    screenshot,
                )

            if not await click_first(page, fm.FORM_SUBMIT):
                await page.screenshot(path=screenshot)
                return SubmitResult(
                    "failed",
                    "Botão de envio não encontrado. Verifique FORM_SUBMIT em field_map.py.",
                    screenshot,
                )
            # A confirmation modal ("Confirmar") may appear after "Enviar".
            await click_first(page, fm.FORM_CONFIRM, timeout=4000)
            await page.wait_for_load_state("networkidle")

            success = await is_present(page, fm.SUCCESS_MARKER, timeout=6000)
            await page.screenshot(path=screenshot)
            if success:
                return SubmitResult("sent", "Saída solicitada com sucesso.", screenshot)
            return SubmitResult(
                "sent",
                "Enviado (sem marcador de sucesso explícito - confirme pelo comprovante).",
                screenshot,
            )
        except Exception as exc:  # noqa: BLE001
            try:
                await page.screenshot(path=screenshot)
            except Exception:
                screenshot = None
            return SubmitResult("failed", f"Erro na automação: {exc}", screenshot)
        finally:
            await context.close()
            await browser.close()
