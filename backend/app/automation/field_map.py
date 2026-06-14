"""Selector map for the real UNASP pensionato site.

Everything site-specific lives HERE so the rest of the automation never changes.
Each entry is a list of candidate CSS selectors; the submitter tries them in
order and uses the first one that exists on the page. Because the site is a
React SPA whose exact `name`/`id` attributes are not fully known, the automation
ALSO falls back to accessible label-based locators (see pensionato.py). Run
`python -m app.automation.discover` once to dump the exact attributes/options and
then tighten these lists.

Logical field names (the keys used in a preset/schedule `payload`):
    dormir_fora   "Sim" | "Não"        (radio)
    destino       text
    motivo        select
    com_quem      select
    nome_pessoa   text
    data_saida    date  (YYYY-MM-DD)
    hora_saida    time  (HH:MM)
    hora_retorno  time  (HH:MM)
    descricao     textarea
"""

# Page where the exit ("liberação de saída") form lives.
LIBERACAO_PATH = "dashboard/aluno/saidas/liberacao"

# --- Login page ---
# NOTE (confirmed via discovery): the login inputs have NO name/id - only a
# placeholder "Digite aqui". The RA/Senha inputs render ONLY AFTER a profile is
# chosen. The profile <select> uses option VALUES, not labels.
PROFILE_VALUES = {
    "Funcionário": "funcionario",
    "Aluno Graduação": "aluno-graduacao",
    "Aluno Educação Básica": "aluno-escola-basica",
}

LOGIN = {
    # There is a single <select> on the login screen.
    "profile_select": [
        "select",
    ],
    # RA field (the only text input on the login screen).
    "username": [
        'input[type="text"]',
    ],
    "password": [
        'input[type="password"]',
    ],
    "submit": [
        "button:has-text('Acessar')",
        "button:has-text('Entrar')",
        'button[type="submit"]',
        'input[type="submit"]',
    ],
    # Labels for accessible fallback locators (get_by_label / placeholder).
    "username_label": ["RA"],
    "password_label": ["Senha"],
    # An element that only appears AFTER a successful login.
    "post_login_marker": [
        "text=Bem-vindo",
        "text=Liberação",
        "text=Histórico",
        "text=Apontamentos",
        "text=Perfil",
        "text=Sair",
    ],
}

# --- Exit form fields ---
# CONFIRMED via discovery: NO field has name/id/associated label. The two text
# fields share placeholder "Digite aqui" and the time fields share "--:--", so
# we must locate POSITIONALLY (css + nth). The dict order is the fill order.
#
# kind:
#   radio    -> click the nth radio per the `options` map (value -> index)
#   text     -> fill
#   select   -> select_option (value/label, accent-insensitive)
#   date     -> fill YYYY-MM-DD
#   time     -> masked "--:--" text input; fill HH:MM (digits typed as fallback)
#   textarea -> fill
FORM = {
    "dormir_fora": {
        "kind": "radio",
        "css": 'input[type="radio"]',
        "options": {"Sim": 0, "Não": 1},
    },
    "destino": {"kind": "text", "css": 'input[placeholder="Digite aqui"]', "nth": 0},
    "motivo": {"kind": "select", "css": "select", "nth": 0},
    "com_quem": {"kind": "select", "css": "select", "nth": 1},
    "nome_pessoa": {"kind": "text", "css": 'input[placeholder="Digite aqui"]', "nth": 1},
    "data_saida": {"kind": "date", "css": 'input[type="date"]', "nth": 0},
    "hora_saida": {"kind": "time", "css": 'input[placeholder="--:--"]', "nth": 0},
    "hora_retorno": {"kind": "time", "css": 'input[placeholder="--:--"]', "nth": 1},
    "descricao": {"kind": "textarea", "css": "textarea", "nth": 0},
}

# A field that must exist before we start filling (form has rendered).
FORM_READY = 'input[placeholder="Digite aqui"]'

# Custom clock-picker dialog ("tp-ui") opened by clicking a time field.
# Hour/minute are role="option" spans; confirm with the "Definir" button.
TIME_DIALOG = {
    "root": ".tp-ui-select-time",
    "hour_tab": ".tp-ui-hour-text",
    "minute_tab": ".tp-ui-minute-text",
    "ok": ".tp-ui-ok-btn",
    "cancel": ".tp-ui-cancel-btn",
}

# Known dropdown options (exact texts confirmed via discovery).
MOTIVO_OPTIONS = [
    "Passeio",
    "Trabalho",
    "Médico",
    "Visitar amigos",
    "Autoescola",
    "Pastel",
    "Estágio",
    "Compras",
    "Visitar família",
    "Pastoral",
    "Universitário",
    "Mercearia",
]
COM_QUEM_OPTIONS = ["Sozinho", "Amigo", "Familiar", "UNASP"]

# Submit: the visible green button on the form is "Confirmar". A second modal
# confirmation may appear afterwards (handled by FORM_CONFIRM).
FORM_SUBMIT = [
    "button:has-text('Confirmar')",
    "button:has-text('Enviar')",
    "button:has-text('Solicitar')",
]
# Possible follow-up confirmation in a dialog/modal.
FORM_CONFIRM = [
    "[role='dialog'] button:has-text('Confirmar')",
    "[role='dialog'] button:has-text('Sim')",
    "[role='dialog'] button:has-text('OK')",
]

# Text/elements that confirm the submission succeeded.
SUCCESS_MARKER = [
    "text=sucesso",
    "text=enviada",
    "text=registrada",
    "text=solicitada",
    ".alert-success",
    ".Toastify__toast--success",
]
