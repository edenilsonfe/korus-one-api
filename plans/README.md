# Implementation Plans (API mirror)

Canonical plan bodies live in the sibling repo:

`/home/dev/Documentos/projetos/korus-one-web/plans/`

This API repo is touched by the following plans (execute from
`/home/dev/Documentos/projetos/korus-one-api` unless the plan says otherwise):

| Plan | Title | Status |
|------|-------|--------|
| 001 | Validar `token_version` no access token | DONE |
| 002 | Corrigir IDOR de evoluções por `session_id` | DONE |
| 003 | Endurecer webhooks de billing | DONE |
| 004 | Não logar URL de reset com token | DONE |
| 006 | Rejeitar `jwt_secret` default fora de debug | DONE |
| 008 | Batch de agregados na listagem de pacientes | DONE |
| 009 | Listar conversas IA sem histórico completo (API half) | DONE |
| 011 | Testes HTTP de isolamento multi-tenant | DONE |
| 012 | Limite de tamanho no upload de anexo | DONE |
| 014 | Ownership antes de `build_patient_context` | DONE |
| 015 | Spike Recursos (API half) | DONE |
| 016 | Spike fidelidade protocolos | DONE |
| 017 | Spike export PDF (API half) | DONE |

Update status in **both** this file and `korus-one-web/plans/README.md` when a
plan finishes.

Web-only plans (005, 007, 010, 013) do not modify this repo.

**Excluded by operator:** CI/CD workflows.
