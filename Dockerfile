FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librsvg2-bin \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY bot /app/bot
COPY prompts /app/prompts

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

CMD ["python", "-m", "bot.main"]
