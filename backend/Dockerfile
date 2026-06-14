# Playwright's image already bundles Chromium + system dependencies.
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8000

# Render (and similar hosts) inject PORT; default 8000 for local Docker Compose.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
