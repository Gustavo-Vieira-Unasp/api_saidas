"""One-shot discovery helper for the real UNASP form.

Logs in with RA/senha, opens the liberação form, and dumps every field's
tag/name/id/type/label plus the exact <option> texts of each dropdown. Use the
output to tighten the selectors and option lists in `field_map.py`.

Usage (from backend/, with the venv active and `playwright install chromium` done):

    python -m app.automation.discover --ra 072960 --senha SUASENHA --perfil "Aluno Graduação"

By default it runs with a visible browser (headed) so you can watch. Add
`--headless` to hide it. Nothing is ever submitted.
"""

from __future__ import annotations

import argparse
import asyncio
from urllib.parse import urljoin

from playwright.async_api import Page, async_playwright

from app.automation import field_map as fm
from app.automation.pensionato import Credentials, _login, _wait_for_form_ready
from app.core.config import settings


async def _dump_fields(page: Page) -> None:
    print("\n=== CAMPOS DO FORMULÁRIO ===")
    fields = await page.evaluate(
        """
        () => Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            name: el.getAttribute('name') || '',
            id: el.id || '',
            placeholder: el.getAttribute('placeholder') || '',
            options: el.tagName.toLowerCase() === 'select'
                ? Array.from(el.options).map(o => ({ value: o.value, text: o.text }))
                : undefined,
        }))
        """
    )
    for f in fields:
        line = f"[{f['tag']}] type={f['type']!r} name={f['name']!r} id={f['id']!r} placeholder={f['placeholder']!r}"
        print(line)
        if f.get("options"):
            for o in f["options"]:
                print(f"      option value={o['value']!r} text={o['text']!r}")


async def discover(ra: str, senha: str, perfil: str, headless: bool) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        try:
            print(f"-> Login com perfil={perfil!r}")
            ok = await _login(page, Credentials(username=ra, password=senha, profile=perfil))
            print(f"-> Login bem-sucedido: {ok}")
            print(f"-> URL após login: {page.url}")

            if not ok:
                await page.screenshot(path="discover_login.png", full_page=True)
                print("-> Login falhou. Screenshot em discover_login.png")
                return

            liberacao_url = urljoin(settings.pensionato_base_url, fm.LIBERACAO_PATH)
            print(f"-> Navegando para {liberacao_url}")
            await page.goto(liberacao_url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception:
                pass
            ready = await _wait_for_form_ready(page)
            print(f"-> Formulário pronto: {ready}")
            print(f"-> URL do formulário: {page.url}")

            await _dump_fields(page)

            print("\n=== BOTÕES ===")
            buttons = await page.evaluate(
                "() => Array.from(document.querySelectorAll('button')).map(b => (b.innerText||'').trim()).filter(Boolean)"
            )
            for b in buttons:
                print(f"   button: {b!r}")

            shot = "discover_form.png"
            await page.screenshot(path=shot, full_page=True)
            print(f"\n-> Screenshot salvo em {shot}")

            # --- Inspect the time-picker dialog ---
            print("\n=== DIÁLOGO DE HORÁRIO ===")
            time_input = page.locator('input[placeholder="--:--"]').first
            await time_input.click()
            await page.wait_for_timeout(800)
            dialog_info = await page.evaluate(
                """
                () => {
                    const root = document.querySelector("[role='dialog']") || document.body;
                    const nodes = Array.from(root.querySelectorAll('button, [role], input, span, div'))
                        .filter(el => (el.innerText||'').trim().length > 0 && el.children.length === 0)
                        .slice(0, 60)
                        .map(el => ({
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role') || '',
                            cls: (el.className || '').toString().slice(0, 60),
                            text: (el.innerText||'').trim().slice(0, 24),
                        }));
                    return nodes;
                }
                """
            )
            for n in dialog_info:
                print(f"   <{n['tag']}> role={n['role']!r} text={n['text']!r} cls={n['cls']!r}")

            html = await page.evaluate(
                """
                () => {
                    const ok = document.querySelector('.tp-ui-ok-btn');
                    if (!ok) return '(ok-btn não encontrado)';
                    let el = ok;
                    for (let i = 0; i < 6 && el.parentElement; i++) el = el.parentElement;
                    return el.outerHTML;
                }
                """
            )
            print("\n=== HTML DO CONTÊINER DO DIÁLOGO (recortado) ===")
            print(html[:1500])

            await page.screenshot(path="discover_time.png", full_page=True)
            print("-> Screenshot do diálogo em discover_time.png")

            # Diagnostic: click the hour option "14" via real pixel coordinates
            # and report what the picker shows.
            print("\n=== TESTE: clicar na hora 14 ===")
            opt = page.get_by_role("option", name="14", exact=True).first
            box = await opt.bounding_box()
            print(f"   bbox de '14': {box}")
            if box:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                await page.wait_for_timeout(600)
            disp = await page.evaluate(
                """
                () => {
                    const h = document.querySelector('.tp-ui-hour-text');
                    const m = document.querySelector('.tp-ui-minute-text');
                    const active = document.querySelector('.tp-ui-value-tips.active, .tp-ui-value-tips-24h.active');
                    return {
                        hour: h ? h.innerText.trim() : null,
                        minute: m ? m.innerText.trim() : null,
                        activeOption: active ? active.innerText.trim() : null,
                    };
                }
                """
            )
            print(f"   após clique -> {disp}")
            await page.screenshot(path="discover_after_hour.png", full_page=True)
            print("-> Screenshot em discover_after_hour.png")
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Descobre os campos do formulário do UNASP")
    parser.add_argument("--ra", default=settings.unasp_ra)
    parser.add_argument("--senha", default=settings.unasp_senha)
    parser.add_argument("--perfil", default="Aluno Graduação")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    if not args.ra or not args.senha:
        parser.error("RA/senha não informados (use --ra/--senha ou defina UNASP_RA/UNASP_SENHA no .env)")
    asyncio.run(discover(args.ra, args.senha, args.perfil, args.headless))


if __name__ == "__main__":
    main()
