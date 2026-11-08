from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _scalar_to_str(value: Any) -> str | None:
    """Converte escalar em string; retorna None se nao for escalar."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return None


class DecisionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: Literal["deepen", "advance", "finish"]
    next_utterance: str = ""
    profile_updates: dict[str, str] = Field(default_factory=dict)
    closing_statement: str = ""

    @field_validator("next_utterance", "closing_statement", mode="before")
    @classmethod
    def _none_to_empty(cls, value: Any) -> Any:
        return "" if value is None else value

    @field_validator("profile_updates", mode="before")
    @classmethod
    def _coerce_profile(cls, value: Any) -> Any:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value
        result: dict[str, str] = {}
        for key, item in value.items():
            if isinstance(item, list):
                parts = [s for s in (_scalar_to_str(i) for i in item) if s is not None]
                if parts:
                    result[key] = ", ".join(parts)
                continue
            text = _scalar_to_str(item)
            if text is not None:
                result[key] = text
        return result
