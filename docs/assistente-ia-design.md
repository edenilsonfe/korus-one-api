# Korus Fono — Assistente de IA unificado (clínico + gestão)

**Data:** 8 de julho de 2026
**Repositórios:** `korus-one-api` (FastAPI / Python) · `korus-one-web` (TanStack Start + Vite)
**Status:** Design aprovado via grill — pronto para implementação
**Referência:** `afeto-clinic-manager` + `myclinic-back` (módulo `management_assistant`), adaptado ao stack e ao domínio do Korus Fono.

---

## Visão geral

### Problema

O Korus Fono tem um assistente clínico em `/chat` (backend em `app/api/v1/ai.py`) que responde com um **snapshot estático** do paciente injetado no system prompt — sem tool-calling. Não há como o modelo consultar dados reais sob demanda (evoluções recentes, metas, avaliações, agenda) nem responder a perguntas de **gestão da prática** ("quantas sessões fiz este mês", "quais pacientes inativos", "compare este mês com o anterior").

### Solução

Um **assistente de IA unificado** (clínico + gestão) que usa **tool-calling** via OpenCode Zen: o modelo decide quais tools chamar, executa-as contra os dados do próprio profissional, e compõe a resposta final com os resultados. Substitui o backend de `/chat` (UI reaproveitada), mantém as conversas persistidas no DB, e adiciona um conjunto de 11 tools read-only cobrindo os dois mundos.

### Decisão de escopo (v1)

- **Assistente unificado** clínico + gestão, mesma conversa, mesma rota `/chat`.
- **Substituir** o backend do `POST /ai/conversations/{id}/messages` (UI `chat.tsx` reaproveitada).
- **Conversas no DB** (mantém `Conversation`/`ChatMessage` + endpoints, cross-device).
- **Resposta única** (orquestra tools → reply), sem streaming real.
- **Pipeline direto + retry reforçado + fallback** (até 2 round-trips).
- **Reusar `opencode_model`** (`deepseek-v4-flash`).

---

## Domínio

Korus Fono é **profissional autônomo** (fonoaudiologia pediátrica inicial), sem filiais, sem "caixa multi-filial". O equivalente a "gestão" é **gestão da própria prática**: produtividade, sessões, faltas, pacientes ativos/inativos, novos pacientes. O "clínico" é o caso do paciente: evoluções, metas, avaliações, contexto.

Reaproveita serviços existentes: `app/services/dashboard.py` (`build_dashboard`), `app/services/patient.py` (`get_patient_aggregates`, `build_clinical_domains`), `app/services/ai_service.py` (`build_patient_context`).

---

## Arquitetura

### Service dedicado — `app/services/assistant/`

```
app/services/assistant/
├── __init__.py
├── assistant_service.py    # orquestração (chat)
├── prompts.py              # SYSTEM_PROMPT + glossário + few-shots + fallback
├── tools.py                # 11 tool definitions + ToolExecutor
├── format_reply.py         # is_leaked_tool_markup + sanitize_assistant_reply
├── query_heuristics.py     # classify_query (colloquial/compound/none)
├── llm_client.py           # create_opencode_client (AsyncOpenAI)
└── rate_limit.py           # enforce_assistant_rate_limit (Redis)
```

### `AssistantService` (`assistant_service.py`)

```python
class AssistantService:
    def __init__(self, db, professional, conversation, llm_client=None): ...
    async def chat(self, user_message: str) -> ChatResponse: ...
```

Pipeline:
1. Resolve contexto (paciente vinculado à conversa → injetar `patient_id` no system context; data de hoje).
2. Constrói `llm_messages` = [system, system-context, ...histórico].
3. **Direto:** chama o LLM com `tools=TOOL_DEFINITIONS, tool_choice="auto"`.
4. Se vier `tool_calls`: executa via `ToolExecutor`, anexa resultados, chama LLM novamente (`tool_choice="none"`) para a resposta final.
5. Se **não** vier `tool_calls`: **retry** com instrução reforçada + `temperature=0.1`. Se o retry chamar tools → executa + resposta final. Se ainda não → **fallback**.
6. Sanitiza a reply (`sanitize_assistant_reply`); se vazou markup → fallback.
7. Retorna `ChatResponse { reply, metadata, suggestions? }`.

**Retry só quando não chamou tool** (decisão 8). Sem intent planner (decisão 7).

### ToolExecutor (`tools.py`)

```python
class ToolExecutor:
    def __init__(self, db, professional): ...
    async def execute(self, name: str, args: dict) -> dict: ...
    @property
    def tools_used(self) -> list[str]: ...
    @property
    def date_from(self) -> date | None: ...
    @property
    def date_to(self) -> date | None: ...
```

Cada tool é registrada com schema (JSON) + handler assíncrono. `TOOL_DEFINITIONS` é derivado do registry. **MAX_TOOL_CALLS = 4** por mensagem.

### Tools (11)

**Gestão da prática (escopadas por `professional.id`):**

| Tool | Parâmetros | Retorna |
|------|------------|---------|
| `get_dashboard_stats` | — | KPIs (pacientes ativos, novos no mês, sessões realizadas, pendentes, relatórios IA) |
| `get_appointment_kpis` | `metric: no_show\|cancellation\|completion\|all`, `date_from?`, `date_to?` | contagens/taxas |
| `get_practice_trend` | `metric: sessions\|new_patients`, `months?` (default 6, máx 12) | série mensal |
| `get_patient_ranking` | `sort_by: appointments\|no_shows`, `limit?` (default 10, máx 20) | ranking de pacientes |
| `get_inactive_patients` | `inactive_days?` (default 90, máx 365) | pacientes sem sessão concluída há N dias |
| `get_appointments_list` | `window: today\|upcoming\|recent`, `limit?` | agenda |

**Clínico (validam posse `patient.professional_id == professional.id`):**

| Tool | Parâmetros | Retorna |
|------|------------|---------|
| `search_patient_by_name` | `name: str`, `limit?` | pacientes do profissional com `name ilike` |
| `get_patient_context` | `patient_id: uuid` | snapshot (dados, agregados, metas, evoluções recentes, avaliações) |
| `get_patient_evolutions` | `patient_id: uuid`, `limit?` (default 5) | evoluções recentes |
| `get_patient_goals` | `patient_id: uuid` | metas e progresso |
| `get_patient_assessments` | `patient_id: uuid`, `limit?` (default 5) | avaliações aplicadas e resultados |

**Segurança:** toda tool clínica valida posse; se não bate, retorna `{"error": "paciente não encontrado"}` (o modelo responde graciosamente). `search_patient_by_name` filtra por `professional_id` (não vaza).

### System prompt (`prompts.py`)

- `SYSTEM_PROMPT`: persona ("Assistente clínico e de gestão da prática Korus Fono"), descrição das 11 tools, regras de escolha, escopo permitido/recusado, regras de formatação (texto simples, sem markdown, parágrafos curtos, listas com hífen).
- `DOMAIN_GLOSSARY`: mapeia sinônimos → tool (ex.: "como está minha clínica"→`get_dashboard_stats`, "pacientes parados"→`get_inactive_patients`, "evolução do paciente"→`get_patient_evolutions`, "progresso das metas"→`get_patient_goals`), adaptado ao domínio fonoaudiológico pediátrico.
- `FEW_SHOT_EXAMPLES`: exemplos pergunta→tool.
- `FALLBACK_REPLY` + `FALLBACK_SUGGESTIONS`.
- `build_retry_messages`: anexa instrução reforçada ("Reinterprete e escolha a ferramenta mais próxima. Você DEVE chamar pelo menos uma ferramenta.").

### `format_reply.py`

Porta de `myclinic`: `is_leaked_tool_markup` (detecta `<|tool_call|>`, DSML, `tool_calls`/`invoke`) + `sanitize_assistant_reply` (remove markup, headings, bold, metadata footer, normaliza linhas em branco).

### `query_heuristics.py`

`classify_query(query) -> "colloquial" | "compound" | "none"`. Adaptado: coloquial = "como está minha clínica/prática", "panorama", "visão geral"; compound = conectores "vs", "comparado", "e também", ou múltiplos domínios. Usado para logging/telemetria (não gateia retry — retry é só quando não chamou tool).

### `llm_client.py`

`create_opencode_client()` → `AsyncOpenAI(api_key=settings.opencode_api_key, base_url=settings.opencode_base_url, timeout=120)`. Valida API key (503 se ausente) e modelo (rejeita prefixos `claude-`/`gpt-`/`gemini-` que não suportam tool_calls no Zen).

### Rate limit (`rate_limit.py`)

`enforce_assistant_rate_limit(professional_id)`: Redis `INCR`+`EXPIRE` na key `assistant:rl:{professional_id}`, janela 3600s, limite `settings.assistant_rate_limit_per_hour` (default 30). Fail-open: se Redis indisponível, loga warning e permite. 429 com `Retry-After` quando excede.

### Settings (`app/core/config.py`)

```python
assistant_rate_limit_per_hour: int = 30
assistant_llm_timeout_seconds: int = 120
```

---

## Schemas (`app/schemas/assistant.py`)

```python
class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

class ChatMetadata(BaseModel):
    tools_used: list[str] = []
    date_from: date | None = None
    date_to: date | None = None
    queried_at: datetime

class ChatResponse(CamelModel):
    reply: str
    metadata: ChatMetadata
    suggestions: list[str] | None = None

class MessageCreate(BaseModel):  # já existe, mantém
    content: str
```

---

## API — substituir o handler `send_message`

`POST /api/v1/ai/conversations/{conversation_id}/messages`

- Auth: `get_current_professional`.
- Carrega a conversa (404 se não pertence ao profissional).
- **Rate limit** (`enforce_assistant_rate_limit`).
- Salva a `ChatMessage(role="user")`.
- Chama `AssistantService(db, professional, conversation).chat(content)`.
- Salva `ChatMessage(role="assistant", content=response.reply)`.
- Retorna `ChatResponse` (JSON único — **não** mais SSE).

> A resposta só retorna ao vivo; a `ChatMessage` persiste só `content` (metadata é efêmera — decisão 17). Ao recarregar a conversa, o histórico vem de `/ai/conversations` (só texto).

Os demais endpoints de `/ai/*` (relatórios, transcrição, etc.) **continuam intactos**.

---

## Frontend (`korus-one-web`)

### `chat.tsx` (ajustes mínimos)

- Sugestões iniciais **mistas** (clínico + gestão):
  - "Quantas sessões realizei este mês?"
  - "Quais pacientes estão inativos há 90 dias?"
  - "Quais os principais avanços do paciente nas últimas sessões?"
  - "Sugira metas terapêuticas com base na evolução."
  - "Compare minha produtividade deste mês com a do anterior."
- Subtítulo: "Assistente clínico e de gestão da sua prática" (era "IA clínica com contexto dos seus casos").
- `PatientSelect` opcional mantido (vincula `patient_id` à conversa).
- Indicador "Pensando…" durante `sendMessage.isPending`.
- Chip sutil de tools usadas na mensagem do assistant ("consultou: agenda, pacientes") quando `metadata.toolsUsed` não vazio.

### `services/ai.ts` — `sendChatMessage`

Troca de parser SSE para `apiRequest<ChatResponse>`:

```ts
export interface AssistantReplyDto {
  reply: string;
  metadata: { toolsUsed: string[]; dateFrom: string | null; dateTo: string | null; queriedAt: string };
  suggestions?: string[];
}

export async function sendChatMessage(conversationId: string, content: string): Promise<AssistantReplyDto> {
  return apiRequest<AssistantReplyDto>(`/ai/conversations/${conversationId}/messages`, {
    method: "POST", body: { content },
  });
}
```

### `hooks/use-ai.ts` — `useSendChatMessage`

`mutationFn` retorna `AssistantReplyDto`; `chat.tsx` usa `reply.reply` como conteúdo e `reply.metadata.toolsUsed` para o chip.

---

## Testes (`tests/test_assistant.py`)

LLM client mockado (`AsyncOpenAI` fake que retorna `tool_calls` ou texto controlado). Casos:

| Alvo | Casos |
|------|-------|
| Tool-call direto | modelo chama `get_dashboard_stats` → executa → resposta final com dados |
| Não-tool → retry → tool | primeira resposta sem `tool_calls`; retry chama tool → resposta |
| Não-tool → retry → não-tool → fallback | ambas sem tools → `FALLBACK_REPLY` |
| Markup vazado | resposta final contém `<|tool_call|>` → sanitize → fallback |
| Validação de posse | `get_patient_context` com paciente de outro profissional → `{"error": ...}` |
| Rate limit | excedido → 429 (mock Redis ou contagem) |
| `search_patient_by_name` | escopado ao profissional (não retorna de outros) |

Sem testar tools isoladas (suas queries são cobertas pelos serviços reaproveitados).

---

## Ordem de implementação

1. **Backend — settings** (`assistant_rate_limit_per_hour`, `assistant_llm_timeout_seconds`).
2. **Backend — `app/services/assistant/`**: `llm_client`, `format_reply`, `query_heuristics`, `prompts` (glossário + few-shots), `tools` (11 tools + `ToolExecutor`), `rate_limit`, `assistant_service` (orquestração).
3. **Backend — schemas** (`app/schemas/assistant.py`).
4. **Backend — substituir handler** `send_message` em `ai.py` (JSON, rate limit, `AssistantService`).
5. **Backend — testes** (`tests/test_assistant.py`, LLM mockado).
6. **Frontend — `services/ai.ts`** (`sendChatMessage` → `AssistantReplyDto`).
7. **Frontend — `hooks/use-ai.ts`** (`useSendChatMessage`).
8. **Frontend — `chat.tsx`** (sugestões mistas, subtítulo, "Pensando…", chip de tools).

## Referências no codebase

### Backend (`korus-one-api`)
- `app/api/v1/ai.py` (`send_message` a substituir)
- `app/services/ai_service.py` (`build_patient_context` reaproveitado como tool)
- `app/services/dashboard.py` (`build_dashboard` reaproveitado)
- `app/services/patient.py` (`get_patient_aggregates`, `build_clinical_domains`)
- `app/models/ai.py` (`Conversation`, `ChatMessage`)
- `app/core/config.py` (`opencode_*` settings)
- `app/db/session.py` (`get_db`)

### Frontend (`korus-one-web`)
- `src/routes/chat.tsx` (UI a ajustar)
- `src/lib/api/services/ai.ts` (`sendChatMessage` a trocar)
- `src/lib/api/hooks/use-ai.ts` (`useSendChatMessage`)

### Referência externa
- `myclinic-back/app/services/management_assistant/` (assistant_service, prompts, tools, format_reply, query_heuristics, llm_client, rate_limit)
- `myclinic-back/app/utils/rate_limit.py` (Redis + fallback)
- `myclinic-back/app/routes/management_assistant.py` (handler enxuto)
- `afeto-clinic-manager/src/services/managementAssistant.ts` + `src/hooks/useManagementAssistantConversation.ts` (UI patterns)
