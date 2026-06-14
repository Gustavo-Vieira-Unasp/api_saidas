# Guia de Instalação

Este guia mostra como rodar o projeto Automação de Saídas UNASP localmente.

## Pré-requisitos

- **Python 3.11+**
- **Node.js 18+** e npm
- (Opcional) **Docker** + Docker Compose para o caminho de um comando só

## 1. Clonar e configurar o ambiente

A partir da raiz do projeto (`api_saidas/`):

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Gere os dois valores secretos e cole-os no `.env`:

```bash
# Segredo do JWT
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Chave de criptografia Fernet (para armazenar as credenciais do UNASP)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

O backend também lê um `backend/.env`. A forma mais simples é copiar o mesmo
arquivo para a pasta do backend, ou usar o `.env` da raiz ao rodar com Docker.

```bash
copy .env backend\.env        # Windows
```

## 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                  # Windows
# source .venv/bin/activate             # macOS/Linux

pip install -r requirements.txt
playwright install chromium             # baixa o navegador usado na automação

uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Docs interativas (Swagger UI): `http://localhost:8000/docs`

O arquivo do banco SQLite (`saidas.db`) e as tabelas são criados automaticamente
na primeira execução. Para evoluir o schema em bancos existentes, use Alembic:

```bash
cd backend
alembic upgrade head
```

## 3. Frontend

Em um novo terminal:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`.

O frontend conversa com o backend em `http://localhost:8000` por padrão. Para
alterar, defina `VITE_API_BASE_URL` em `frontend/.env`.

## 4. Primeiro uso

1. Crie uma conta com seu **RA** e **senha do UNASP** (mesma senha usada no site).
2. Ajuste o **perfil de acesso** em Configurações, se necessário.
3. Preencha o formulário de saída uma vez e **salve como modelo**.
4. Use **Enviar agora** para um envio imediato, ou **Agendar** para depois /
   recorrente.

## 5. Configurando os seletores do formulário

Como os campos exatos do formulário do UNASP precisam ser confirmados a partir
da página real, a automação lê um mapa de campos em
[backend/app/automation/field_map.py](../backend/app/automation/field_map.py).
Atualize os seletores CSS lá para corresponder ao formulário real, e o resto do
app continua funcionando sem alterações. Veja
[ARCHITECTURE.md](ARCHITECTURE.md#camada-de-automação).

## Docker (alternativa)

A partir da raiz do projeto:

```bash
copy .env.example .env        # Windows — preencha SECRET_KEY e ENCRYPTION_KEY
docker compose up --build
```

Isso sobe o backend (`:8000`) e o frontend (`:5173`) juntos. **O backend não
inicia** sem `SECRET_KEY` e `ENCRYPTION_KEY` válidos no `.env` da raiz.

## Solução de problemas

| Problema                              | Solução                                                    |
| ------------------------------------- | ---------------------------------------------------------- |
| Navegador do `playwright` não encontrado | Rode `playwright install chromium` dentro da venv do backend. |
| Erros de CORS no console do navegador | Garanta que `FRONTEND_ORIGIN` no `.env` corresponde à URL do frontend. |
| Envios sempre falham                  | Confira os seletores em `field_map.py` e suas credenciais do UNASP. |
| Tarefas agendadas não disparam        | Verifique `SCHEDULER_TIMEZONE` e se o backend continua rodando. |
