# API

Referência das rotas da API FastAPI, derivada de `backend/app/api/v1/endpoints/*.py`,
`backend/app/schemas/` e `backend/app/main.py`. Para testar de forma interativa, use o Swagger em
**`/docs`** (por exemplo http://localhost:8000/docs), gerado pelo próprio FastAPI a partir do
mesmo código. Modelos de dados e coleções: [banco.md](banco.md).

- **Prefixo:** tudo sob `/api/v1`, exceto `GET /health` (raiz).
- **Formato:** JSON, salvo uploads (`multipart/form-data`), áudio e SSE.
- **Autenticação:** não há. As rotas do pesquisador e as rotas de convite são abertas
  (limite assumido, RK-11; veja o [README](../README.md#10-limites)). O CORS aceita qualquer origem.
- **Erros:** o corpo é sempre `{"detail": "<mensagem em português>"}`. `422` de validação (corpo, query ou
  parâmetro fora do formato) também é em pt-BR: `{"detail": "Dados inválidos: confira <campos>."}`,
  só com os nomes dos campos (nunca o valor enviado); não é repetido nas tabelas.
- **Cabeçalho `X-Request-ID`:** devolvido em toda resposta (o mesmo id aparece no log).

## Códigos de erro

| Código | Origem | Quando | Mensagem |
|---|---|---|---|
| `400` | `ValueError` (handler em `main.py`) e `HTTPException` | regra de estado violada ou áudio inválido | a da regra (ex.: "Não é possível gerar a síntese antes de encerrar a entrevista.") |
| `404` | `NotFoundError` | recurso inexistente | "Roteiro não encontrado.", "Participante não encontrado.", "Sessão não encontrada.", "Síntese ainda não gerada.", "Relatório do roteiro ainda não gerado.", "Convite inválido ou encerrado." |
| `409` | `ConflictError` | conflito de estado ou versão velha | veja cada rota |
| `411` | `HTTPException` | upload do questionário sem `Content-Length` (por exemplo, `chunked`) | "Envie o arquivo com o tamanho informado." |
| `413` | `FileTooLargeError`/`HTTPException` | arquivo grande demais; no upload do questionário, recusado já pelo `Content-Length` (acima do limite + 64 KB) antes de o servidor gravar o multipart | "Arquivo maior que 2 MB." (questionário), "Áudio maior que o permitido." |
| `415` | `UnsupportedFileError` | extensão não aceita | "Formato não suportado. Envie .txt, .md, .csv, .docx ou .pdf." |
| `422` | `ImportFileError` ou validação | arquivo ilegível/sem perguntas; corpo inválido | "Não consegui abrir o arquivo. Confira se ele não está corrompido.", "O PDF não tem texto (pode ser digitalizado).", "O arquivo .docx é grande demais para ler.", "Não encontrei perguntas no arquivo." |
| `500` | `CorruptDocumentError` | documento do banco fora do modelo | "Erro interno ao ler os dados." |
| `502` | `ProviderError` | falha do provedor de IA (inclui chave ausente) | "Falha ao se comunicar com o provedor de IA." |

Mensagens de `409`: "A entrevista já foi encerrada.", "Este roteiro não está recebendo
entrevistas.", "A sessão foi alterada por outra ação. Tente de novo.", "O registro foi alterado
por outra ação. Tente de novo." (roteiro com versão velha), "Já existe um roteiro com esse
identificador ou link de convite.", "O roteiro padrão não pode ser apagado.", "O roteiro padrão
não pode ser desativado nem ter as perguntas alteradas.", "Este roteiro já tem entrevistas. Crie
um novo roteiro para mudar as perguntas.", "Este participante tem entrevistas registradas e não
pode ser apagado.", "Gere a síntese de pelo menos 2 entrevistas concluídas antes do relatório
do roteiro."

## Saúde

| Método e rota | Resposta |
|---|---|
| `GET /health` | `200` `{"status": "ok"}` (usado pelo Playwright para saber que o backend subiu; o healthcheck do Compose é só do MongoDB) |

## Roteiros (`/api/v1/scripts`)

| Método e rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `GET /scripts?ativos=true` | `ativos=false` inclui os desativados | `200` lista de `ScriptSummary`: `script_id`, `titulo`, `tema`, `descricao`, `slug_convite`, `link_convite`, `ativo`, `perguntas_total`, `persona`, `sessoes_total`, `concluidas`, `em_andamento` | |
| `POST /scripts` | `ScriptCreate`: `titulo` (obrigatório), `tema`, `descricao`, `perguntas[]` (min 1: `texto`, `objetivo`, `max_aprofundamentos` 0 a 5, padrão 2), `persona` (`nome`, `tom`: `acolhedor`/`neutro`/`formal`), `origem` (`tipo`: `manual`/`upload`, `arquivo`) | `201` `InterviewScript` completo (a ordem das perguntas é a posição na lista) | `409` identificador ou link duplicado |
| `POST /scripts/upload` | multipart, campo `file` (`.txt`, `.md`, `.csv`, `.docx`, `.pdf`; máx `MAX_UPLOAD_BYTES`, 2 MB) | `200` `ScriptDraft`: `titulo`, `tema`, `descricao`, `perguntas[]` (`texto`, `objetivo`), `origem`, `avisos[]`. **Não grava nada**: a pessoa revisa e publica por `POST /scripts` | `413`, `415`, `422`, `502` |
| `GET /scripts/{script_id}` | | `200` `InterviewScript` | `404` |
| `PUT /scripts/{script_id}` | `ScriptUpdate`: todos opcionais (`titulo`, `tema`, `descricao`, `perguntas`, `persona`, `ativo`); só o que vier muda | `200` `InterviewScript` | `404`; `409` roteiro padrão (desativar ou mudar perguntas), roteiro com entrevistas (mudar perguntas) ou versão velha |
| `DELETE /scripts/{script_id}` | | `204`. Sem sessões apaga; com sessões só desativa | `404`; `409` roteiro padrão |
| `GET /scripts/{script_id}/sessions?status=&limit=` | `status`: `em_andamento` ou `concluida`; `limit` 1 a 200 (padrão 50) | `200` lista de `SessionSummary`: `session_id`, `script_id`, `participant_id`, `participante` (apelido), `status`, `respostas`, `created_at`, `updated_at`, `tem_sintese` | `404` roteiro |
| `GET /scripts/{script_id}/painel` | | `200` `ScriptDashboard`: `total_sessoes`, `concluidas`, `em_andamento`, `taxa_conclusao`, `duracao_media_min` (`null` sem base), `media_respostas`, `acoes[]`, `aprofundamentos_por_pergunta[]`, `custo_total_usd` (inclui o custo dos relatórios do roteiro ainda existentes), `custo_medio_usd` (média entre as entrevistas com custo medido), `sinteses_sessao` (nº de sínteses de sessão), `temas_mais_citados[]`, `sessoes_por_dia[]` (últimos 30 dias, fuso America/Sao_Paulo), `canais[]` | `404` |
| `GET /scripts/{script_id}/convite` | | `200` `{slug, link}` | `404` |
| `GET /scripts/{script_id}/qrcode.svg` | | `200` `image/svg+xml` (QR do link de convite) | `404` |
| `GET /scripts/{script_id}/sintese` | | `200` `Synthesis` (`escopo: roteiro`) já salvo | `404` roteiro ou relatório ainda não gerado |
| `POST /scripts/{script_id}/sintese?refresh=false` | | `200` `Synthesis`. Devolve o salvo; sem ele (ou com `refresh=true`) gera pelo LLM a partir das sínteses de sessão (no máximo 30, com teto de 12 mil caracteres no prompt) e grava | `404`; `409` menos de 2 sínteses de sessão; `502` |

## Participantes (`/api/v1/participants`)

| Método e rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `GET /participants` | | `200` lista de `Participant` | |
| `POST /participants` | `ParticipantCreate`: `apelido`, `faixa_etaria`, `regiao` (todos opcionais), `canal` (`voz` padrão, ou `texto`) | `201` `Participant` | |
| `GET /participants/{participant_id}` | | `200` `Participant` | `404` |
| `PUT /participants/{participant_id}` | `ParticipantUpdate`: só o que vier muda; `null` limpa o campo (exceto `canal`); vale a última escrita | `200` `Participant` | `404` |
| `DELETE /participants/{participant_id}` | | `204` | `404`; `409` se tem entrevistas |

## Convite público (`/api/v1/convite`)

Rotas **sem login**: o participante entra só pelo link. Só roteiros ativos aceitam convite.

| Método e rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `GET /convite/{slug}` | | `200` `InvitePublic`: `slug`, `titulo`, `tema`, `descricao`, `persona`, `perguntas_total`, `link` (nada de sessão nem de participante) | `404` convite inválido ou roteiro desativado |
| `POST /convite/{slug}/sessao` | opcional `InviteStart`: `canal` (`voz`/`texto`), `apelido` (máx 40), `faixa_etaria` (máx 20), `regiao` (máx 60); texto vazio vira ausente | `201` `SessionResponse` (igual a `POST /session`); cria o participante e abre a sessão | `404` convite inválido ou encerrado |
| `GET /convite/{slug}/sessao/{session_id}` | | `200` `InviteSession`: `session_id`, `titulo`, `perguntas_total`, `current_index`, `finished`, `acolhimento`, `persona` (`nome`, `tom`) e `conversation[]` (`role`, `text`). Estado mínimo para retomar a entrevista pública: sem objetivos das perguntas, perfil, participante nem métricas | `404` "Convite inválido ou encerrado." (também quando a sessão não é do roteiro do convite) |
| `POST /convite/{slug}/sessao/{session_id}/canal` | `InviteChannel`: `canal` (`voz`/`texto`) | `204`; atualiza o canal do participante da sessão | `404` como acima; `422` |

Estas rotas são públicas e não têm limite de requisições (RK-15).

## Sessões (`/api/v1/session`)

| Método e rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `POST /session` | opcional `SessionCreate`: `script_id`, `participant_id`; sem corpo usa o roteiro padrão | `200` `SessionResponse`: `session_id`, `pergunta` (a 1ª), `script_id`, `titulo`, `perguntas_total` | `404` roteiro ou participante; `409` roteiro desativado |
| `GET /session/{id}` | | `200` `InterviewState` (estado completo: `conversation`, `profile`, `metricas`, `finished`, `status`, `versao`…) | `404` |
| `GET /session/{id}/detalhes` | | `200` `SessionDetails`: `session`, `script`, `participant` (resolvidos por `$lookup`; `script` e `participant` podem ser `null`) | `404` |
| `DELETE /session/{id}` | | `204`. Apaga a sessão e, em cascata, a síntese dela e os relatórios de roteiro que a usaram (`sessoes_ids` ou citação dela; precisam ser regerados, e o custo gravado neles sai do total do painel) | `404` |
| `POST /session/{id}/finish` | | `200` `InterviewState`. Idempotente | `404`; `409` se a sessão mudou de novo durante o encerramento |
| `POST /session/{id}/synthesis?refresh=false` | | `200` `{"sintese": "<resumo>"}`. Devolve a salva; sem ela (ou com `refresh=true`) gera pelo LLM e grava | `400` entrevista não encerrada ou sem respostas do participante; `404`; `502` |
| `GET /session/{id}/synthesis` | | `200` `Synthesis` completa (`resumo`, `temas`, `lacunas`, `modelo`…) | `404` sessão ou síntese ainda não gerada |

## Turnos (`/api/v1/turn`)

O corpo é `{"texto": "<fala transcrita>"}` (`texto` com pelo menos 1 caractere).

### `POST /turn/{session_id}`

Processa a resposta e devolve `200` `TurnResponse`:

| Campo | Tipo | Significado |
|---|---|---|
| `fala` | string | próxima fala do entrevistador |
| `finalizada` | bool | a entrevista acabou |
| `indice_atual` | int | posição da pergunta atual |
| `acao` | `deepen` \| `advance` \| `finish` \| null | decisão tomada |
| `pergunta_ordem` | int \| null | pergunta central a que a fala pertence |
| `perguntas_total` | int | total de perguntas do roteiro |
| `aprofundamentos_restantes` | int \| null | quantos aprofundamentos ainda cabem na pergunta |

Erros: `404`; `409` entrevista encerrada ou sessão alterada por outra ação (versão velha);
`502`.

### `POST /turn/{session_id}/stream` (SSE)

Mesmo turno, em `text/event-stream` (cabeçalhos `Cache-Control: no-cache` e
`X-Accel-Buffering: no`). `404` e `409` (sessão inexistente ou já encerrada) respondem HTTP
normal **antes** de abrir o stream. Cada evento tem o formato:

```
event: <nome>
data: <json em uma linha>

```

| Evento | `data` | Quando |
|---|---|---|
| `pensando` | `{"risco": "nenhum" \| "sofrimento" \| "pedido_parar"}` | na hora, antes de o LLM responder; o `risco` vem da checagem determinística (sem LLM) e o front não toca filler se for diferente de `nenhum` |
| `frase` | `{"texto": "...", "indice": 0, "finalizada": false, "acolhimento": false}` | uma por frase da fala já decidida, em ordem |
| `fim` | o mesmo corpo de `POST /turn/{id}` (`TurnResponse`, que inclui `acolhimento`: a fala é o acolhimento com o CVV e o front não navega sozinho) | depois da última frase |
| `erro` | `{"detail": "..."}` | falha depois do início: provedor ("Falha ao se comunicar com o provedor de IA."), conflito/sessão ausente (mensagem do domínio) ou inesperada ("Não consegui processar sua resposta. Tente de novo.") |

O LLM é chamado uma vez; o turno é gravado antes da primeira `frase` e sobrevive a uma
desconexão do cliente. Não é streaming token a token.

## Voz (`/api/v1/voice`)

| Método e rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `POST /voice/transcricao?session_id=` | multipart, campo `file` (áudio; máx `MAX_AUDIO_BYTES`, 25 MB). `session_id` (opcional) atribui os segundos de áudio à sessão nas métricas | `200` `{"texto": "..."}` | `400` "Áudio vazio." ou "Não foi possível entender o áudio."; `413` "Áudio maior que o permitido."; `502` |
| `POST /voice/fala?session_id=` | JSON `{"texto": "...", "tom": "acolhedor"}` (`texto` obrigatório; `tom` opcional: `acolhedor`/`neutro`/`formal`, escolhe a entonação). `session_id` (opcional) atribui os caracteres de TTS à sessão | `200` `audio/mpeg` | `502` |

O áudio nunca é armazenado: a gravação vai para a transcrição e é descartada.

## Exemplo rápido com `curl`

Com a API em `localhost:8000` e `LLM_PROVIDER=fake`:

```bash
# abre uma sessão no roteiro padrão
curl -s -X POST http://localhost:8000/api/v1/session
# responde um turno (troque SESSION_ID pelo valor devolvido)
curl -s -X POST http://localhost:8000/api/v1/turn/SESSION_ID \
  -H "Content-Type: application/json" -d '{"texto": "Eu trabalho como diarista."}'
```
