from fastapi import APIRouter

from app.automation.field_map import COM_QUEM_OPTIONS, MOTIVO_OPTIONS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/field-options")
def field_options() -> dict:
    """Canonical select options shared with the frontend form."""
    return {
        "motivo": MOTIVO_OPTIONS,
        "com_quem": COM_QUEM_OPTIONS,
        "dormir_fora": ["Sim", "Não"],
    }
