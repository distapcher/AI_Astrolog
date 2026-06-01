from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PERSONALITY_PROMPT_PATH = BASE_DIR / "prompts" / "astrolog_prof_ru.md"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    rapidapi_key: str
    rapidapi_host: str
    chart_theme: str
    chart_language: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    geonames_username: str | None
    personality_prompt_path: Path
    ai_max_tokens: int


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "").strip()

    if not bot_token:
        raise ValueError("BOT_TOKEN is not set")
    if not rapidapi_key:
        raise ValueError("RAPIDAPI_KEY is not set")

    openai_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    prompt_path = Path(os.getenv("PERSONALITY_PROMPT_PATH", str(PERSONALITY_PROMPT_PATH)))

    return Settings(
        bot_token=bot_token,
        rapidapi_key=rapidapi_key,
        rapidapi_host=os.getenv("RAPIDAPI_HOST", "astrologer.p.rapidapi.com").strip(),
        chart_theme=os.getenv("CHART_THEME", "dark").strip(),
        chart_language=os.getenv("CHART_LANGUAGE", "RU").strip(),
        openai_api_key=openai_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "deepseek-chat").strip(),
        geonames_username=os.getenv("GEONAMES_USERNAME", "").strip() or None,
        personality_prompt_path=prompt_path,
        ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", "12000")),
    )
