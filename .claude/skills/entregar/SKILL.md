---
name: entregar
description: Fecha uma entrega do AEP ESOFT6S (Interviewer) com o padrão de qualidade do projeto — verificação completa (pytest com cobertura ≥ 70%, build do frontend), três revisões independentes por agentes (spec/AEP, código, interface), correção dos achados, spec de evoluções atualizada e PR. Use sempre que pedirem para entregar, finalizar, fechar, revisar antes de subir, abrir PR ou "mandar pra main/devjoao" qualquer mudança deste repositório, mesmo que não digam /entregar.
---

# Entrega com padrão de qualidade

Rotina obrigatória antes de qualquer PR de código do AEP ESOFT6S. Ela existe porque a nota da AEP
depende de evidência no repositório: evolução verificável, NoSQL do 2º semestre, POO, testes com
cobertura ≥ 70%, documentação e versionamento (ver `docs/EVOLUCOES.md`, seção 2).

## 1. Preparar

- Branch criada a partir da branch de integração atualizada (`devjoao`/`main`), nomeada pelo item
  da spec: `feat/EV-xx-descricao`, `fix/EV-xx-...`, `docs/...`, `chore/...`.
- Os itens `EV-xx` tocados estão descritos em `docs/EVOLUCOES.md`; decisões novas tomadas no código
  estão registradas lá (no próprio item ou na tabela de riscos).
- Commits **separados por assunto** (backend, frontend, testes, docs), Conventional Commits em
  português com o ID do item: `feat(EV-41): ...`, `fix(EV-11): ...`. Sem linha de atribuição.
- Nunca entram: `.env`, `.coverage`, `*.stackdump`, `.venv/`, `node_modules/`, `.reviews/`,
  `.superpowers/`, chaves de API, áudio ou transcrição real de participante.

## 2. Verificação determinística

```bash
bash scripts/verify-delivery.sh             # backend (pytest + cobertura) + frontend (build)
bash scripts/verify-delivery.sh --backend   # só backend
```

O script para no primeiro erro e diz qual etapa falhou. **Corrija pela causa:** não apague teste,
não afrouxe critério, não baixe o `--cov-fail-under=70`, não volte a pôr arquivo no `omit` da
cobertura para ficar verde. Bug conhecido que não é desta entrega fica com
`pytest.mark.xfail(strict=True, reason="BUG: ...")` e vai para os limites do PR.

Testes nunca chamam a OpenAI de verdade: use os dublês do `tests/conftest.py` ou
`LLM_PROVIDER=fake`.

## 3. Revisão por agentes

Gere a base que os revisores leem (eles só leem, não executam comandos):

```bash
BASE_BRANCH=main   # ou devjoao, conforme o alvo do PR
git fetch origin "$BASE_BRANCH"
mkdir -p .reviews
BASE=$(git merge-base "origin/$BASE_BRANCH" HEAD)
git diff "$BASE" > .reviews/diff.patch
{ git diff --name-only "$BASE"; git ls-files --others --exclude-standard; } | sort -u > .reviews/files.txt
git log --oneline "$BASE"..HEAD > .reviews/commits.txt
```

Dispare **em paralelo, numa única mensagem**, os subagentes do projeto (`.claude/agents/`).
Passe a cada um o resumo do recorte e os `EV-xx` que a entrega fecha:

- `revisor-spec`: aderência à `docs/EVOLUCOES.md` e aos critérios da AEP 2026.2;
- `revisor-codigo`: backend (camadas, providers, async, Mongo, segurança/LGPD) e testes;
- `revisor-interface`: só se a mudança tocar `frontend/`.

Se os agentes do projeto não aparecerem como tipo de subagente na sessão, dispare um subagente
genérico por revisor com a instrução "leia `.claude/agents/<revisor>.md` e siga-o à risca".

Consolide os achados numa tabela única em `.reviews/achados.md`
(severidade | arquivo:linha | achado | decisão). A pasta é ignorada pelo git.

Para cada achado:

- **Corrija** P1 e P2 reais, com um teste que falharia sem a correção.
- **Recuse com motivo** o que não tem cenário concreto ou contraria a spec.
- **Decisão de produto:** spec omissa → adote o padrão mais seguro coerente com ela e registre no
  item `EV-xx` da `docs/EVOLUCOES.md`; mudança de escopo (algo da seção "Fora de escopo", feature
  nova) → pergunte ao João antes.
- **P3:** corrija se for barato; senão, registre como limite no PR.

Depois das correções, rode de novo o passo 2. Se as correções foram grandes, gere outro
`.reviews/diff.patch` e rode de novo o revisor afetado.

## 4. Spec de evoluções

Antes do PR, atualize `docs/EVOLUCOES.md`:

- status dos itens entregues → `DONE` (heading ou coluna da tabela);
- riscos mitigados → nota "**mitigado**" na linha do `RK-xx`;
- decisões tomadas durante a entrega → no item correspondente.

Commit próprio: `docs: marca EV-xx como concluido`.

## 5. PR e merge

Siga só quando a pessoa pediu a entrega ou o PR. Um pedido apenas de revisão para no passo 3.

- Push da branch e PR com base na branch de integração combinada (`main` por padrão, ou
  `devjoao`). O corpo, em pt-BR, traz:
  - o que entra, com os `EV-xx`;
  - como testar (comandos e, se houver tela, 3 a 5 passos);
  - a verificação, com números (testes, cobertura);
  - a tabela resumida dos achados e o que foi feito com cada um;
  - limites e riscos que continuam abertos.
- Espere o CI do PR ficar verde (`gh pr checks <n> --watch`).
- **Merge** só quando o João pedir ou autorizar nesta conversa. Antes de mergear, avise e espere
  confirmação se a PR:
  - muda o formato de documentos no MongoDB (sessões antigas podem quebrar ao carregar);
  - mexe em `.github/`, `docker-compose.yml`, segredos ou deploy;
  - muda o contrato HTTP usado pelo frontend.
- Versão de entrega da AEP: tag + release só quando o João pedir (`v0.1.0` = 1ª entrega).

## 6. Resposta final

Curta e direta:
- link do PR e se foi mergeado;
- verificação com números (testes, cobertura, build);
- achados corrigidos e recusados;
- o que foi atualizado na `docs/EVOLUCOES.md`;
- limites e o que depende do João ou da equipe;
- como testar, em 3 a 5 passos.

Diferencie **implementado**, **mergeado** e **testado em tela**.
