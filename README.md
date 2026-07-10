# Korus One API

Backend FastAPI para o Korus One — sistema operacional para terapias infantis.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker (PostgreSQL, Redis, MinIO)

## Setup

```bash
cp .env.example .env

# Subir infra + migrations + API (profile "app" é obrigatório para a API)
docker compose --profile app up -d

# Seed demo (opcional, primeira vez)
docker compose --profile tools run --rm seed
```

A API fica em **http://localhost:8000** — confira com `curl http://localhost:8000/health`.

> **Importante:** o serviço `api` usa o profile `app`. O flag `--profile` vem **antes** do subcomando:
> `docker compose --profile app up -d` (correto) — **não** `docker compose up -d --profile app`.

### Comandos Docker do dia a dia

```bash
docker compose --profile app up -d          # subir tudo (postgres, redis, minio, migrate, api)
docker compose --profile app down           # parar e remover containers
docker compose --profile app down --remove-orphans   # se der erro de rede órfã
docker compose --profile app ps             # status dos containers
docker compose --profile app logs -f api    # logs da API em tempo real
docker compose --profile tools run --rm seed   # recarregar dados demo
```

Se aparecer `network ... not found`, recrie a stack:

```bash
docker rm -f korus-one-api-api-1 2>/dev/null
docker compose --profile app down --remove-orphans
docker compose --profile app up -d
```

Portas expostas: **API** `8000`, **Postgres** `5433`, **Redis** `6380`, **MinIO** `9000`/`9001`.

Para rodar a API direto no host (requer Postgres acessível em localhost:5433):

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

> **Nota Windows:** conexões do host ao Postgres Docker podem exigir `scram-sha-256`. Use o serviço `api` via `docker compose --profile app up -d` ou `docker compose run --rm migrate` para bootstrap.

## Env de e-mail (Resend)

Para o fluxo de recuperação de senha (`/auth/forgot-password` → `/auth/reset-password`), configure no `.env`:

- `RESEND_API_KEY`: chave da conta Resend.
- `EMAIL_FROM`: remetente aprovado no Resend.
- `EMAIL_SENDING_ENABLED=true`: habilita envio real (em dev pode ficar `false`).
- `FRONTEND_URL`: base usada no link `.../reset-password?token=...`.
- `PASSWORD_TOKEN_EXPIRE_MINUTES`: validade do token de reset.
- `PASSWORD_RESET_COOLDOWN_SECONDS`: cooldown entre solicitações por usuário.

## Endpoints

- Health: `GET /health`
- API: `GET /api/v1/...`
- Docs: `GET /docs` (Swagger — debug local; contrato = `app/schemas/` + `app/api/v1/`)

## Migrations (Alembic)

```bash
# Aplicar migrations (também roda automaticamente no docker compose --profile app up)
docker compose run --rm migrate

# Seed demo (primeira vez ou reset manual)
docker compose --profile tools run --rm seed

# Gerar nova migration após alterar modelos em app/models/
docker compose run --rm migrate sh -c "uv sync && uv run alembic revision --autogenerate -m 'descricao da mudanca'"

# Comandos locais (Postgres em localhost:5433)
uv sync
uv run alembic upgrade head          # aplicar
uv run alembic revision --autogenerate -m "descricao"  # gerar
uv run alembic current               # versão atual
uv run alembic history               # histórico
```

> **Importante:** revise sempre o arquivo gerado em `alembic/versions/` antes de commitar — o autogenerate pode omitir renomeações ou detectar falsos positivos.

## Worker IA (opcional)

```bash
uv run arq worker.WorkerSettings
```

Configure `OPENCODE_API_KEY` no `.env` (chave em [opencode.ai/auth](https://opencode.ai/auth)). Modelos disponíveis: [OpenCode Zen](https://opencode.ai/docs/zen/).

## Testes

```bash
uv run pytest
```

## Credenciais demo

- Email: `camila.rocha@korusone.com`
- Senha: `demo12345`
