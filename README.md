# Automação de Saídas UNASP (api_saidas)

Automatiza o formulário diário de autorização de saída do [pensionato.unasp.edu.br](https://pensionato.unasp.edu.br/).

Feito para estudantes que precisam preencher o mesmo pedido de saída chato todos os dias.
Em vez disso, faça login uma vez, salve um modelo e:

- **Envie agora** com um único clique.
- **Agende** um envio para uma data e hora específicas.
- **Repita** automaticamente (ex.: todo dia útil às 18:00).
- **Acompanhe** cada envio com status de sucesso/falha e um comprovante em imagem.

## Como funciona

```
Frontend React  ->  Backend FastAPI  ->  Playwright (navegador headless)  ->  Site do UNASP
                         |
                         +-- APScheduler (tarefas agendadas / recorrentes)
                         +-- SQLite (usuários, modelos, agendamentos, histórico)
```

Um navegador headless preenche e envia o formulário real do UNASP no lugar do
usuário, então funciona exatamente como se o estudante tivesse feito manualmente.

## Stack de tecnologia

| Camada       | Tecnologia                          |
| ------------ | ----------------------------------- |
| Backend      | Python, FastAPI, SQLAlchemy         |
| Automação    | Playwright (Chromium)               |
| Agendador    | APScheduler (job store SQLAlchemy)  |
| Banco        | SQLite (migrável para Postgres)     |
| Frontend     | React, Vite, TypeScript, Tailwind   |
| Autenticação | JWT + credenciais criptografadas (Fernet) |

## Início rápido

Veja o [docs/SETUP.md](docs/SETUP.md) para o guia completo. Resumindo:

```bash
# 1. Configure secrets (a partir da raiz do projeto)
copy .env.example .env          # Windows — edite SECRET_KEY e ENCRYPTION_KEY
copy .env backend\.env          # backend local também lê backend/.env

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload

# 3. Frontend (novo terminal)
cd frontend
npm install
npm run dev
```

O backend roda em `http://localhost:8000` (docs em `/docs`) e o frontend em `http://localhost:5173`.

Ou rode tudo com Docker (requer `.env` na raiz com chaves preenchidas):

```bash
copy .env.example .env   # edite os valores secretos
docker compose up --build
```

### Produção (Render + Vercel)

Backend no [Render](https://render.com) (Docker + disco persistente) e frontend na [Vercel](https://vercel.com). Guia passo a passo: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Documentação

- [docs/SETUP.md](docs/SETUP.md) — instalação e configuração local
- [docs/DEPLOY.md](docs/DEPLOY.md) — **deploy em produção (Render + Vercel)**
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — como as peças se encaixam
- [docs/API.md](docs/API.md) — referência dos endpoints REST
- [docs/ROADMAP.md](docs/ROADMAP.md) — Phase 2 mobile roadmap

## Status do projeto

A Fase 1 (aplicação web) está implementada. A camada de automação com Playwright
([backend/app/automation/pensionato.py](backend/app/automation/pensionato.py))
usa um **mapa de campos configurável**, de modo que os seletores exatos do
formulário do UNASP podem ser conectados sem alterar o resto do código. A Fase 2
(aplicativo mobile) está planejada e reutiliza a mesma API do backend.

## Aviso

Esta ferramenta automatiza um formulário que o usuário já está autorizado a
enviar, usando as próprias credenciais. Use de forma responsável e de acordo com
as regras do UNASP.
