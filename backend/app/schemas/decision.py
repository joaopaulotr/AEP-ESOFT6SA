from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    probe_tipo: Literal["elaboracao", "exemplo", "sentimento", "clarificacao", "confirmacao"] | None = None
    risco: Literal["nenhum", "sofrimento", "pedido_parar"] = "nenhum"
    reconhecimento: str = ""

    @field_validator("next_utterance", "closing_statement", "reconhecimento", mode="before")
    @classmethod
    def _none_to_empty(cls, value: Any) -> Any:
        return "" if value is None else value

    @field_validator("probe_tipo", mode="before")
    @classmethod
    def _unknown_probe_is_none(cls, value: Any) -> Any:
        valid = {"elaboracao", "exemplo", "sentimento", "clarificacao", "confirmacao"}
        return value if value in valid else None

    @field_validator("risco", mode="before")
    @classmethod
    def _unknown_risk_is_none(cls, value: Any) -> Any:
        # Campo auxiliar: valor desconhecido não pode derrubar a decisão inteira.
        return value if value in {"nenhum", "sofrimento", "pedido_parar"} else "nenhum"

    @model_validator(mode="after")
    def _deepen_needs_an_utterance(self) -> "DecisionResult":
        if self.action == "deepen" and not self.next_utterance.strip():
            raise ValueError("deepen exige next_utterance não vazio")
        return self

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
                joined = ", ".join(parts)
                if joined.strip():
                    result[key] = joined
                continue
            text = _scalar_to_str(item)
            if text is not None and text.strip():
                result[key] = text
        return result
