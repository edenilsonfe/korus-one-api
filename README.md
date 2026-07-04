# Korus One API

Backend FastAPI para o Korus One — sistema operacional para terapias infantis.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker (PostgreSQL, Redis, MinIO)

## Setup

```bash
cp .env.example .env
docker compose up -d
docker compose --profile tools run --rm migrate   # alembic upgrade + seed demo
docker compose --profile app up api               # API em http://localhost:8000
```

Para rodar a API direto no host (requer Postgres acessível em localhost:5433):

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

> **Nota Windows:** conexões do host ao Postgres Docker podem exigir `scram-sha-256`. Use o serviço `api` via Docker Compose ou `docker compose --profile tools run --rm migrate` para bootstrap.

## Endpoints

- Health: `GET /health`
- API: `GET /api/v1/...`
- Docs: `GET /docs`

## Migrations (Alembic)

```bash
# Aplicar migrations + seed (recomendado via Docker)
docker compose --profile tools run --rm migrate

# Gerar nova migration após alterar modelos em app/models/
docker compose --profile tools run --rm migrate sh -c "uv sync && uv run alembic revision --autogenerate -m 'descricao da mudanca'"

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

## Testes

```bash
uv run pytest
```

## Credenciais demo

- Email: `camila.rocha@korusone.com`
- Senha: `demo12345`
