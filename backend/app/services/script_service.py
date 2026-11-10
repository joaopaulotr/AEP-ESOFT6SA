from app.core.errors import ConflictError
from app.services.invite_service import build_invite_link
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.api import QuestionCreate, ScriptCreate, ScriptSummary, ScriptUpdate
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question

HAS_SESSIONS_MESSAGE = (
    "Este roteiro já tem entrevistas. Crie um novo roteiro para mudar as perguntas."
)
DEFAULT_SCRIPT_MESSAGE = "O roteiro padrão não pode ser apagado."
DEFAULT_SCRIPT_EDIT_MESSAGE = "O roteiro padrão não pode ser desativado nem ter as perguntas alteradas."

_SUMMARY_FIELDS = {"script_id", "titulo", "tema", "descricao", "slug_convite", "ativo", "persona"}


def _questions(items: list[QuestionCreate]) -> list[Question]:
    """A ordem da pergunta é a posição na lista (1, 2, 3...)."""
    return [Question(ordem=position, **item.model_dump()) for position, item in enumerate(items, 1)]


class ScriptService:
    """Regras dos roteiros: edição segura, exclusão que preserva histórico e resumo com contagens."""

    def __init__(self, scripts: ScriptRepository, sessions: SessionRepository) -> None:
        self._scripts = scripts
        self._sessions = sessions

    async def list_summaries(self, *, only_active: bool = True) -> list[ScriptSummary]:
        scripts = await (self._scripts.list_active() if only_active else self._scripts.list())
        counts = await self._sessions.count_by_script([s.script_id for s in scripts])
        summaries = []
        for script in scripts:
            total, concluidas = counts.get(script.script_id, (0, 0))
            summaries.append(
                ScriptSummary(
                    **script.model_dump(include=_SUMMARY_FIELDS),
                    link_convite=build_invite_link(script.slug_convite),
                    perguntas_total=len(script.perguntas),
                    sessoes_total=total,
                    concluidas=concluidas,
                    em_andamento=total - concluidas,
                )
            )
        return summaries

    async def get(self, script_id: str) -> InterviewScript:
        return await self._scripts.get_or_raise(script_id)

    async def create(self, data: ScriptCreate) -> InterviewScript:
        fields = data.model_dump(exclude={"perguntas", "persona", "origem"})
        script = InterviewScript(**fields, perguntas=_questions(data.perguntas))
        if data.origem is not None:
            script.origem = data.origem
        if data.persona is not None:
            script.persona = data.persona
        return await self._scripts.create(script)

    async def update(self, script_id: str, data: ScriptUpdate) -> InterviewScript:
        script = await self._scripts.get_or_raise(script_id)
        if script_id == DEFAULT_SCRIPT_ID and (data.perguntas is not None or data.ativo is False):
            # É o fallback de POST /session sem corpo: precisa ficar ativo e íntegro.
            raise ConflictError(DEFAULT_SCRIPT_EDIT_MESSAGE)
        changes = data.model_dump(exclude_unset=True, exclude={"perguntas", "persona"})
        # null explícito em campo obrigatório é o mesmo que não enviar.
        changes = {key: value for key, value in changes.items() if value is not None}
        if data.perguntas is not None:
            # Janela conhecida, não atômica: uma sessão pode abrir entre esta checagem e o save.
            if await self._sessions.has_for_script(script_id):
                # A conversa guarda a posição da pergunta: mexer nelas embaralha a transcrição
                # das entrevistas já feitas (concluídas ou não).
                raise ConflictError(HAS_SESSIONS_MESSAGE)
            changes["perguntas"] = _questions(data.perguntas)
        if data.persona is not None:
            changes["persona"] = data.persona
        updated = InterviewScript.model_validate({**script.model_dump(), **changes})
        await self._save(updated)
        return updated

    async def delete(self, script_id: str) -> None:
        """Sem sessões, apaga. Com sessões, só desativa: o histórico não perde o roteiro."""
        script = await self._scripts.get_or_raise(script_id)
        if script_id == DEFAULT_SCRIPT_ID:
            raise ConflictError(DEFAULT_SCRIPT_MESSAGE)
        if await self._sessions.has_for_script(script_id):
            script.ativo = False
            await self._save(script)
        else:
            await self._scripts.delete(script_id)

    async def _save(self, script: InterviewScript) -> None:
        if not await self._scripts.save(script):
            await self._scripts.get_or_raise(script.script_id)  # apagado no meio -> 404
