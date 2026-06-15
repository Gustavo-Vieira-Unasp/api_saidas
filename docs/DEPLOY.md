# Deploy: Render (backend) + Vercel (frontend) — **$0/month**

Production layout:

```
Browser  →  Vercel free (React SPA)  →  Render free (FastAPI + Playwright)
                                              ├── Supabase Postgres (persistent)
                                              └── ephemeral disk (screenshots only)
```

**Total cost:** $0 (Vercel Hobby + Render Free + Supabase Free).

Deploy **Supabase first**, then **backend**, then **frontend**, then wire CORS.

---

## Free tier — what you get vs what you give up

| | Free ($0) | Paid Starter (~$7/mo) |
|---|-----------|------------------------|
| Vercel frontend | Yes | Yes |
| Manual “send now” / dry-run | Yes | Yes |
| Public URL | Yes | Yes |
| Service always on | **No** — sleeps ~15 min after idle | Yes |
| Scheduled jobs on time | **Unreliable** — only when awake | Yes |
| Users, templates, schedules, history | **Yes** (Supabase Postgres) | Yes |
| Screenshot PNGs after redeploy | **Lost** (Render disk) | Persists with disk |
| Cold start | 30–60+ s after sleep | Minimal |

The included [`render.yaml`](../render.yaml) uses **Render Free** with **no persistent disk** for screenshots. Database rows survive redeploys via **Supabase Postgres**.

To upgrade later: change `plan: free` → `plan: starter` in `render.yaml`, add a disk block for screenshots (see [Upgrade to Starter](#upgrade-to-starter-optional) below).

---

## Prerequisites

- GitHub repo with this project pushed
- [Render](https://render.com) account (free)
- [Vercel](https://vercel.com) account (Hobby / free)
- [Supabase](https://supabase.com) account (free)

---

## Part 0 — Supabase Postgres (~15 min)

1. [supabase.com](https://supabase.com) → **New project** (pick a region close to Render, e.g. `sa-east-1` if available).
2. **Project Settings → Database** → **Connection string → URI**:
   - Use **Session mode** (port **5432**) — recommended for SQLAlchemy + APScheduler.
   - Append `?sslmode=require` if not already present.
   - Example shape (do **not** commit the real password):

     ```
     postgresql://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require
     ```

3. **Do not** enable Supabase Auth — this app uses JWT auth in FastAPI.
4. Save the URI in a password manager; you will paste it into Render as `DATABASE_URL`.

**Keeping Supabase active:** Supabase pauses projects after ~7 days with no DB activity. Your `/health` endpoint runs `SELECT 1`. With [UptimeRobot](#keep-render-and-supabase-active-uptimerobot-free) pinging every 5 minutes, Render wakes, hits Postgres, and resets the inactivity timer.

**Alternative:** [Neon](https://neon.tech) works the same way — only `DATABASE_URL` changes.

---

## Part 1 — Backend on Render (free)

### Before first deploy — set secrets (critical)

Generate these **once** locally and save in a password manager:

```bash
# JWT signing secret
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Fernet key for encrypted UNASP credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set **`ENCRYPTION_KEY`** and **`SECRET_KEY`** in Render **before** going live. If Render auto-generates them on first boot, a redeploy can change them and **decrypting stored UNASP passwords will fail**. Users would need to re-enter credentials in Settings.

### Option A: Blueprint (recommended)

1. Push this repo to GitHub.
2. Render Dashboard → **New** → **Blueprint**.
3. Connect the repo; Render reads [`render.yaml`](../render.yaml).
4. **Environment variables** (set in Render Dashboard):

   | Variable | Required? | Notes |
   |----------|-----------|--------|
   | `DATABASE_URL` | **Yes** | Supabase Session URI (port 5432) with `?sslmode=require` |
   | `ENCRYPTION_KEY` | **Yes** | Fernet key from above — **must stay stable** across redeploys |
   | `SECRET_KEY` | **Yes** | JWT secret from above — **must stay stable** across redeploys |
   | `FRONTEND_ORIGIN` | After Vercel | Set once you have the Vercel URL |

5. Wait for deploy; check logs for `Alembic migrations applied (head)` and `Scheduler started`.
6. Note the URL, e.g. `https://api-saidas-backend.onrender.com`.
7. Verify: `GET https://YOUR-BACKEND.onrender.com/health` → `"database": "ok"`.

**Tip:** First request after sleep is slow. Open `/health` once before using the app to wake the service.

### Option B: Manual web service

1. **New** → **Web Service** → connect repo.
2. **Runtime:** Docker  
3. **Instance type:** Free  
4. **Dockerfile path:** `./backend/Dockerfile`  
5. **Do not** add a persistent disk (paid only; screenshots remain ephemeral).
6. Environment variables:

   ```
   DATABASE_URL=postgresql://postgres.[ref]:[PASSWORD]@...supabase.com:5432/postgres?sslmode=require
   SCREENSHOTS_DIR=./screenshots
   PLAYWRIGHT_HEADLESS=true
   SCHEDULER_TIMEZONE=America/Sao_Paulo
   SECRET_KEY=<random — save permanently>
   ENCRYPTION_KEY=<fernet key — save permanently>
   CORS_ORIGIN_REGEX=https://.*\.vercel\.app
   FRONTEND_ORIGIN=
   ```

7. **Health check path:** `/health`

---

## Part 2 — Frontend on Vercel (free)

1. Vercel Dashboard → **Add New** → **Project** → import the same GitHub repo.
2. **Root Directory:** `frontend`
3. Framework: **Vite** ([`frontend/vercel.json`](../frontend/vercel.json)).
4. **Environment variables** (Production):

   | Name | Value |
   |------|--------|
   | `VITE_API_BASE_URL` | `https://YOUR-BACKEND.onrender.com` (no trailing slash) |

5. Deploy → note URL, e.g. `https://api-saidas.vercel.app`.
6. Optional: same `VITE_API_BASE_URL` under **Preview** env for branch deploys.

Vercel Hobby is free for personal projects.

---

## Part 3 — Connect CORS (Render)

Render → **api-saidas-backend** → **Environment**:

```
FRONTEND_ORIGIN=https://YOUR-APP.vercel.app
```

Save → auto-redeploy. Preview URLs on `*.vercel.app` are already allowed via `CORS_ORIGIN_REGEX`.

---

## Part 4 — Smoke test and persistence check

1. Open the Vercel URL (may take a minute if backend was sleeping).
2. Register with RA + UNASP password.
3. Dashboard → **dry-run** submission.
4. History → confirm entry.
5. **Redeploy Render intentionally** → confirm user + history still exist (validates Postgres persistence).

**Note:** Screenshot PNGs may 404 after redeploy (ephemeral Render disk). History **rows** (status, message, timestamps) persist in Postgres.

---

## Migrating from old ephemeral SQLite

| Scenario | Action |
|----------|--------|
| Fresh start (most likely) | New Supabase DB; users re-register; recreate templates/schedules |
| Local `saidas.db` backup | Custom export/import script (not included) |
| Encrypted UNASP credentials | **Cannot** move between `ENCRYPTION_KEY` values — users re-enter in Settings |

---

## Environment reference

### Render (backend)

| Variable | Required | Production value |
|----------|----------|------------------|
| `DATABASE_URL` | Yes | Supabase Session URI (`postgresql://...:5432/...?sslmode=require`) |
| `SECRET_KEY` | Yes | Stable random string (password manager) |
| `ENCRYPTION_KEY` | Yes | Stable Fernet key (password manager) |
| `SCREENSHOTS_DIR` | Yes | `./screenshots` |
| `FRONTEND_ORIGIN` | Yes (prod) | `https://your-app.vercel.app` |
| `CORS_ORIGIN_REGEX` | Optional | `https://.*\.vercel\.app` |
| `PLAYWRIGHT_HEADLESS` | Yes | `true` |
| `SCHEDULER_TIMEZONE` | Yes | `America/Sao_Paulo` |

### Vercel (frontend)

| Variable | Required | Example |
|----------|----------|---------|
| `VITE_API_BASE_URL` | Yes | `https://api-saidas-backend.onrender.com` |

Rebuild Vercel after changing `VITE_API_BASE_URL`.

---

## Upgrade to Starter (optional)

When you need reliable schedules and persistent **screenshots**, edit [`render.yaml`](../render.yaml):

```yaml
plan: starter
disk:
  name: api-saidas-data
  mountPath: /data
  sizeGB: 1
# env:
#   SCREENSHOTS_DIR=/data/screenshots
```

Keep `DATABASE_URL` pointing at Supabase. Redeploy via Blueprint.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| CORS error | `FRONTEND_ORIGIN` must match Vercel URL exactly |
| API calls localhost | Rebuild Vercel with `VITE_API_BASE_URL` |
| Backend crash on start | Set `ENCRYPTION_KEY` and `SECRET_KEY` in Render env |
| `"database": "error"` on `/health` | Check `DATABASE_URL`, SSL (`?sslmode=require`), Supabase project not paused |
| SSL / connection refused | Use Session mode port **5432**, not Transaction pooler **6543** |
| Transaction pooler (6543) errors | Switch to Session mode URI, or add `connect_args={"prepare_threshold": None}` (not needed for 5432) |
| Supabase project paused | Open Supabase dashboard → **Restore project**; UptimeRobot keeps it active afterward |
| Very slow first load | Backend waking from sleep — wait or hit `/health` |
| Schedule didn’t run | Free tier was asleep — upgrade or use manual send |
| UNASP password invalid after redeploy | `ENCRYPTION_KEY` changed — set a stable key and re-enter password in Settings |
| Playwright failed | Retry; free tier has less RAM |
| UptimeRobot 405 | Use GET or HEAD on `/health`; redeploy latest backend |
| Enviar hangs / provisional headers | Playwright takes minutes; API now returns immediately — redeploy backend, check Histórico |
| Alembic error on startup | Check Render logs; run `alembic upgrade head` manually from Render shell if needed |

---

## Local vs production

| | Local | Production (free) |
|---|-------|-------------------|
| Frontend | `npm run dev` :5173 | Vercel |
| Backend | `uvicorn` or Docker | Render Free |
| Database | SQLite (`saidas.db`) | Supabase Postgres |
| Cost | $0 | $0 |
| Data persistence | Yes (local disk) | Yes (Postgres); screenshots ephemeral |

Local dev: [SETUP.md](SETUP.md).

---

## Keep Render and Supabase active (UptimeRobot, free)

Render Free sleeps after ~15 min without traffic. Supabase pauses after ~7 days without DB activity. Ping every **5 minutes** to keep both awake.

1. [UptimeRobot](https://uptimerobot.com) → **Add monitor**
2. **Monitor type:** HTTP(s)
3. **URL:** `https://YOUR-BACKEND.onrender.com/health`
4. **HTTP method:** **HEAD** or **GET** (both work after latest deploy)
5. **Interval:** 5 minutes

Optional keyword check on GET: `"database": "ok"`.

**Note:** HEAD requests returned 405 before — fixed in the API. Redeploy Render after pulling latest code, or switch the monitor to **GET** until redeployed.
