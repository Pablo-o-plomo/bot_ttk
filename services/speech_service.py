from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from config import OPENAI_API_KEY


class SpeechError(Exception):
    pass


def transcribe_audio(audio_path: str) -> str:
    """Transcribe voice/audio file using OpenAI speech-to-text API."""
    if not OPENAI_API_KEY:
        raise SpeechError("OPENAI_API_KEY не задан. Расшифровка голоса недоступна.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    path = Path(audio_path)
    if not path.exists():
        raise SpeechError("Аудиофайл не найден для расшифровки.")

    with path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )

    text = (transcript.text or "").strip()
    if not text:
        raise SpeechError("Не удалось получить текст из аудио.")
    return text
