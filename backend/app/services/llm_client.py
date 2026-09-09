import json

from openai import OpenAI

from app.core.config import settings


class LLMClient:
    def __init__(self, client: OpenAI | None = None, model: str = "gpt-4o-mini") -> None:
        self._client = client or OpenAI(api_key=settings.openai_api_key or None)
        self._model = model

    def complete_json(self, prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def complete_text(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
