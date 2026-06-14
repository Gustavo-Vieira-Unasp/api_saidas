"""Run a single exit submission (or dry-run) from the command line.

Useful for testing the automation without the full API/frontend. By default it
runs as a DRY RUN: it fills every field but does NOT click "Enviar".

Example (dry run):
    python -m app.automation.run_once --ra 072960 --senha SENHA \\
        --destino "Casa" --motivo "Passeio" --com-quem "Sozinho" \\
        --data 2026-06-20 --saida 14:00 --retorno 20:00 --descricao "Visita"

Add --submit to actually send the request.
"""

from __future__ import annotations

import argparse
import asyncio

from app.automation.pensionato import Credentials, submit_exit
from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Envio/dry-run de uma saída no UNASP")
    parser.add_argument("--ra", default=settings.unasp_ra)
    parser.add_argument("--senha", default=settings.unasp_senha)
    parser.add_argument("--perfil", default="Aluno Graduação")
    parser.add_argument("--dormir-fora", default="Não", choices=["Sim", "Não"])
    parser.add_argument("--destino", default="Casa")
    parser.add_argument("--motivo", default="Passeio")
    parser.add_argument("--com-quem", default="Sozinho")
    parser.add_argument("--nome-pessoa", default="")
    parser.add_argument("--data", default="", help="YYYY-MM-DD")
    parser.add_argument("--saida", default="14:00", help="HH:MM")
    parser.add_argument("--retorno", default="20:00", help="HH:MM")
    parser.add_argument("--descricao", default="Saída de teste")
    parser.add_argument("--submit", action="store_true", help="Realmente enviar (sem isto, é dry-run)")
    args = parser.parse_args()
    if not args.ra or not args.senha:
        parser.error("RA/senha não informados (use --ra/--senha ou defina UNASP_RA/UNASP_SENHA no .env)")

    payload = {
        "dormir_fora": args.dormir_fora,
        "destino": args.destino,
        "motivo": args.motivo,
        "com_quem": args.com_quem,
        "nome_pessoa": args.nome_pessoa,
        "data_saida": args.data,
        "hora_saida": args.saida,
        "hora_retorno": args.retorno,
        "descricao": args.descricao,
    }
    creds = Credentials(username=args.ra, password=args.senha, profile=args.perfil)

    result = asyncio.run(submit_exit(creds, payload, dry_run=not args.submit))
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"screenshot: {result.screenshot_path}")


if __name__ == "__main__":
    main()
