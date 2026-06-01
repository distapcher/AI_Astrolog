# AI_Astrolog — Telegram-бот астролог

Бот строит **натальную карту** по дате, времени и месту рождения:

- **Kerykeion** — расчёт положений планет, домов, аспектов (Swiss Ephemeris)
- **Astrologer API** (RapidAPI, `astrologer.p.rapidapi.com`) — SVG-колесо карты
- **Опционально** — полная ИИ-расшифровка по 10 разделам (OpenAI-совместимый API)

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/chart` | Построить натальную карту |
| `/help` | Справка |

## Переменные окружения

Скопируйте `.env.example` в `.env`:

```bash
BOT_TOKEN=...
RAPIDAPI_KEY=...
RAPIDAPI_HOST=astrologer.p.rapidapi.com
CHART_THEME=dark
CHART_LANGUAGE=RU

# Опционально — расшифровка
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# отредактируйте .env
python -m bot.main
```

## Docker (VPS)

```bash
cd /opt/AI_Astrolog
cp .env.example .env   # один раз
docker compose up -d --build
docker compose logs -f
```

Деплой с Mac (после `gh auth login` и push):

```bash
./scripts/deploy.sh "описание изменений"
```

## Сервер

По умолчанию: `root@2.27.25.85`, каталог `/opt/AI_Astrolog`.
