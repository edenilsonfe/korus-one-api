# Korus One — Architecture Refactor (C1–C5)

- **Data:** 2026-07-12
- **Origem:** `architecture-review-20260712-204203.html` (review de arquitetura Korus One)
- **Repos:** `korus-one-api` + `korus-one-web`
- **Domínio:** Instrumento/Protocolo · Aplicação · Paciente · Timeline · Responsável
- **Estado do app:** em desenvolvimento — **sem retrocompatibilidade** a preservar; rotas/shapes/views legados podem ser reescritos ou removidos livremente.
- **Postura de testes:** TDD por candidato (red-green-refactor definindo a nova interface primeiro) **+** suite de regressão existente mantida verde como rede de segurança.
- **Cópias canônicas:** este spec vive em `docs/superpowers/specs/` em **ambos** os repos (web e api), mantidas em sincronia.

---

## 1. Programa-mãe

### 1.1 Escopo

Implementar 5 dos 7 candidatos identificados pelo review de arquitetura. Os 5 escolhidos cobrem os dois níveis de confiança acionáveis: **Strong** (C1, C2) e **Worth exploring** (C3, C4, C5). Os dois **Speculative** (C6 CaregiverOutreach, C7 Battery shell) ficam de fora do programa (§1.5).

### 1.2 Sequência: dois clusters sequenciais

```
Cluster A (protocolo/scoring)      Cluster B (paciente/timeline/view)
─────────────────────────────      ──────────────────────────────────
C1 ProtocolApplication  ─┐
                          ├→ checkpoint A
C2 ScoringSession        ─┘                    C3 PatientRecord ─┐
                                              C4 ClinicalActivity ─┼→ checkpoint B (final)
                                              C5 PatientView    ─┘
```

**Por que dois clusters (e não sequencial estrito C1→C2→C3→C4→C5):** captura os dois leverages explícitos do review — C1 encolhe a interface que C2 consome (scoring), e C3 provê DTOs limpos que C5 consome (view). Além disso, a sobreposição C3↔C4 (ambos tocam `clinical.py`, `prontuario`, `sessions`) fica dentro do mesmo cluster, abrindo esses arquivos uma só vez em vez de três.

**Por que não paralelo:** `clinical.py` é compartilhado entre C2 (lado scoring, cluster A) e C3/C4 (lado paciente/timeline, cluster B). Paralelismo ingênuo quebraria o mandato "um writer por cwd/worktree". Sequencial por cluster evita conflito de writer no arquivo compartilhado.

### 1.3 Dependências entre candidatos

1. **C1 → C2** (Cluster A): C1 estabelece o "mode resolve" (qual instrumento/protocolo → qual `scoringMode`). C2 consome esse mode e aprofunda `assessment_scoring` em `ScoringSession`. Sem C1, C2 fica preso na disputa slug×scoringMode descrita no review.
2. **C3 → C5** (Cluster B): C3 concentra leitura/escrita coesa do paciente e produz DTOs limpos. C5 consome esses DTOs na camada de view; `types.ts` deixa de importar `mock-data`.
3. **C3 ↔ C4** (Cluster B): ambos tocam `clinical.py`/`prontuario`/`sessions`. C3 é o módulo de leitura/escrita do paciente; C4 é o emitter de timeline que vive ao lado da entidade. Adjacentes, mesma passada.
4. **`clinical.py` transversal:** aparece em C2 (scoring), C3 (prontuário), C4 (timeline). Resolução: C2 abre o lado scoring no cluster A; C3/C4 abrem o lado prontuário/sessions no cluster B — sem escrita simultânea.

### 1.4 Checkpoints

- **Checkpoint A** (fim do cluster A): C1+C2 verdes. Legados internalizados (slugs viram implementação no registry, não mais `if` em `aplicar.tsx`). UI de protocolo roda sobre `ProtocolApplication.resolve()`. `result-analysis.ts` (web) não re-calcula `%`.
- **Checkpoint B** (fim do programa): C3+C4+C5 verdes. Deletion test de `create_timeline_event` (corrigido por C4) passando. `mock-data.ts` sem seed morto. `types.ts` não importa `mock-data`. Nenhum `if` de slug em `aplicar.tsx`. Callers de timeline usam `recordX(...)` sem montar `title`/`description`.

### 1.5 O que NÃO está no programa (Speculative)

- **C6 — CaregiverOutreach** — *Speculative*. Gatilho futuro: **chegada de 2º informante** (p.ex. M-CHAT informante). Por ora SPM e notificações WhatsApp compartilham infra via rotas separadas; carecem de um módulo de domínio unificado (token + telefone + opt-in + template + log) quando o gatilho surgir. Interface proposta: `issueLink · sendLink · resolvePublic`, com adapter `WhatsAppProvider`.
- **C7 — Battery shell** — *Speculative*. Gatilho futuro: **lifecycle SPM convergir** com `BatteryService`. Colapsar `AbfwBatteryDetailView`/`SpmBatteryDetailView`/`GenericBatteryInstrumentForm` num `BatteryShell` de props `{features, panels}` só vale quando `SpmBatteryService` e `BatteryService` tiverem ciclo de vida comum. Por ora a UI web permanece com shells separados.

Ambos ficam registrados para um futuro programa, não apagados da memória.

### 1.6 Definição de pronto (todo o programa)

1. Os 5 candidatos implementados com TDD; suite de regressão existente verde.
2. Deletion test de `create_timeline_event` (C4) passando.
3. `mock-data.ts` sem seed morto; `types.ts` não importa `mock-data`.
4. Nenhum `if` de slug espalhado em `aplicar.tsx` — só `resolve()`.
5. `result-analysis.ts` não re-calcula `%`.
6. Callers de `clinical.py`/`prontuario`/`sessions` usam `recordX(...)`, não montam `title`/`description`.
7. Dois adapters (API real + fixture) documentados para C2.

---

## 2. Candidato C1 — ProtocolApplication (detalhado)

> **Top recommendation do review.** É o módulo mais raso com maior leverage: cada Instrumento novo ainda toca switch de slug, rotas legadas e detail views. Aprofundar `ProtocolApplication` primeiro encolhe a interface que a UI precisa aprender; `ScoringSession` (C2) e `BatteryShell` (C7) ficam mais baratos depois.

- **Confiança do review:** Strong
- **Estilo:** in-process
- **Repos:** web (principal) + api (realinhado)
- **Arquivos candidatos citados pelo review:**
  - web: `src/routes/avaliacoes_.$protocolId.aplicar.tsx` · `adapters-ext.ts` · `battery-routes.ts` · `AbfwBatteryDetailView` · `BatteryDetailView`
  - api: `assessment_scoring.get_protocol_scoring_mode` · `instrument_aliases.py`

### 2.1 Problema

`aplicar.tsx` decide o formulário por um switch de `protocolId` (slug) misturado com `scoringMode`:

```ts
if (protocolId === "portage") form = <PortageInstrumentForm .../>
else if (protocolId === "rastreio-tea") form = <RastreioTeaInstrumentForm .../>
else if (protocolId === "spm") ...
else if (mode === "battery") form = <GenericBatteryInstrumentForm .../>
else if (mode === "manifest") form = <ManifestInstrumentForm .../>
else if (protocolId === "mchat" || protocolId === "m-chat-r") ...
else if (scoredConfig) ...
```

Slug switch e `scoringMode` competem; a interface do roteamento equivale à implementação espalhada. Cada instrumento novo exige novo `if`. Legados (`portage`, `abfw`, `proc`, `abllsr`, `mchat`) ramificam a árvore de decisão sem centralização.

### 2.2 Solução

Um módulo deep `ProtocolApplication` com interface `resolve → Descriptor`. Os legados viram **implementação** (entradas no registry), não mais ramos de `if`.

```
ProtocolApplication.resolve(protocolId, { scoringMode }) → Descriptor {
  formComponent,      // PortageInstrumentForm | Spm | Mchat | ...
  sessionKind,       // "single" | "battery" | "manifest"
  apiPrefix,         // rota de submissão
  resumeTarget,      // rota pós-onComplete
} | undefined        // protocolo desconhecido
```

`aplicar.tsx` reduz-se a:

```ts
const d = ProtocolApplication.resolve(protocolId, { scoringMode: protocol.scoringMode ?? "manual" });
return <PageContainer>...{d ? <d.formComponent .../> : <NotImplemented/>}</PageContainer>;
```

No api, `instrument_aliases.py` + `get_protocol_scoring_mode` viram a **fonte única** de `scoringMode` servida ao web (via `toProtocolView` em `adapters-ext.ts`). O web não decide mais mode localmente.

### 2.3 Wins (do review)

- **Localidade:** uma árvore de decisão (o registry), não N `if`s.
- **Leverage:** N call sites, 1 interface.
- **Interface encolhe:** formulários só renderizam.
- **Teste:** matriz `resolve()` sem React.

### 2.4 Divisão por arquivo (web)

```
src/lib/assessments/protocol-application/   (novo)
  ├─ descriptor.ts      // tipo Descriptor (inclui RenderCtx/Descriptor — importa `type { ReactNode }`)
  ├─ registry.tsx       // tabela protocolo → Descriptor (legados como entradas) — .tsx porque contém JSX
  ├─ resolve.ts         // resolve(protocolId, {scoringMode}) → Descriptor | undefined (puro, sem React)
  └─ resolve.test.ts    // matriz (protocolId, mode) → expected.formComponentKey, SEM React
```

- Componentes são referenciados por **key** no registry, não importados no teste — a "matriz resolve() sem React" é uma tabela de `(protocolId, mode) → formComponentKey`.
- `aplicar.tsx` reescrito (~10 linhas): chama `resolve`, renderiza `d.formComponent`.
- `adapters-ext.ts::toProtocolView`: garante que `scoringMode` venha do api (fonte única).

### 2.5 Realinhamento api

- `app/core/instrument_aliases.py` e `app/services/assessment_scoring.py::get_protocol_scoring_mode` continuam como fonte canônica de `scoringMode` por protocolo. Sem duplicação web.
- Nenhuma rota api nova obrigatória no C1; o que muda é **quem decide** o mode (api, não web).

### 2.6 Testes (TDD — red-green-refactor)

**Vermelho primeiro:** `resolve.test.ts` define a matriz esperada para todos os protocolos legados + `battery` + `manifest` + `mchat`, **antes** do registry existir.

**Como o registry decide:** a chave primária é `protocolId` (slug) — cada protocolo legado tem entrada própria com seu `formComponentKey` e `sessionKind` fixos (portage, abfw, proc, abllsr, mchat, spm, rastreio-tea). O `scoringMode` (vindo do api via `toProtocolView`, já mapeado hoje em `adapters-ext.ts:28`) só dispara os casos **genéricos** — `battery` e `manifest` — para protocolos sem entrada legada dedicada. Assim, `abfw` resolve pelo slug (sua própria entrada) e não compete com o ramo `mode === "battery"`.

Casos da matriz (os valores de `mode` abaixo são ilustrativos; os reais vêm do api e serão fixados no plano do C1 a partir de `toProtocolView`):
- `resolve("portage", {mode})` → `{ sessionKind: "single", formComponentKey: "portage" }`
- `resolve("abfw", {mode})` → `{ sessionKind: "battery", formComponentKey: "abfw" }`  *(legado dedicado; mode ignorado)*
- `resolve("proc", {mode})` → `{ sessionKind: "battery", formComponentKey: "proc" }`  *(legado dedicado)*
- `resolve("mchat", {mode})` / `resolve("m-chat-r", {mode})` → `{ sessionKind: "single", formComponentKey: "mchat" }`
- `resolve("spm", {mode})` → `{ sessionKind: "single", formComponentKey: "spm" }`
- `resolve("abllsr", {mode})` → `{ sessionKind: "single", formComponentKey: "abllsr" }`
- `resolve("rastreio-tea", {mode})` → `{ sessionKind: "single", formComponentKey: "rastreio-tea" }`
- `resolve("<slug-desconhecido>", {mode})` → `undefined`
- Casos **genéricos** por `scoringMode` (só para protocolos sem entrada legada): `resolve("<novo-proto>", {battery})` → `formComponentKey: "generic-battery"`; `resolve("<novo-proto>", {manifest})` → `formComponentKey: "manifest"`.

**Verde:** implementar `registry.ts` + `resolve.ts` até a matriz passar.

**Refactor:** reescrever `aplicar.tsx` para usar `resolve`; remover os `if` de slug. Rodar suite de regressão do web (`result-analysis.test.ts`, `scoring.test.ts`, etc.) — deve continuar verde (C1 não toca scoring, só roteamento).

### 2.7 Estratégia de erro

- `resolve()` retorna `Descriptor | undefined`. `aplicar.tsx` já tem branch "não encontrado"/"em desenvolvimento". Sem throw.
- Protocolo desconhecido não é exceção — é estado normal em dev enquanto catálogo evolui.

### 2.8 Migração (sem retrocompatibilidade)

Substituição de raiz: registry novo + `aplicar.tsx` reescrito. Slugs `portage`/`abfw`/`proc`/`abllsr`/`rastreio-tea`/`mchat` viram **entradas** do registry, não ramos de `if`. Sem depreciação — o app está em dev.

### 2.9 Pronto (C1)

- [x] `resolve.test.ts` verde (matriz sem React).
- [x] `aplicar.tsx` sem `if` de slug — só `resolve()` + render.
- [x] `scoringMode` servido pelo api (via `toProtocolView`), não decidido no web.
- [x] Suite de regressão do web verde.

---

## 3. Demais candidatos (specs detalhados no seu turno)

Per §1.2, cada candidato abaixo ganha seu próprio spec→plano→implementação quando seu cluster chegar. Esta seção registra a interface acordada e o posicionamento de arquivos para que o programa-mãe permaneça coerente.

### 3.1 C2 — ScoringSession (Cluster A, após C1) — ✅ fatia manifest (2026-07-12)

- **Confiança:** Strong · **Estilo:** ports & adapters · **Repo:** api (web consome)
- **Status:** Implementado — `scoring_session.py`; `assessment_scoring` delega; `clinical.py` usa `ScoringSession`; Manifest omite `%` local. Battery/SPM/`result-analysis` adiados.
- **Interface:** `ScoringSession.from_protocol(...).score(answers) → NormalizedScores` (+ `from_scores` fixture adapter)
- **Testes:** `tests/test_scoring_session.py` (2 adapters) + `test_assessment_scoring.py`

### 3.2 C3 — PatientRecord (Cluster B) — ✅ fatia leitura (2026-07-12)

- **Confiança:** Worth exploring · **Estilo:** ports & adapters · **Repo:** api + web
- **Status:** Implementado — `patient_record.build_patient_detail` + `map_assessment`; `fetchPatient(id, include?)`. `appendNote`/`listActivities`/SessionEvolution adiados.
- **Testes:** `tests/test_patient_record.py`

### 3.3 C4 — ClinicalActivity (Cluster B) — ✅ fatia 3 recorders (2026-07-12)

- **Confiança:** Worth exploring · **Estilo:** in-process · **Repo:** api
- **Status:** Implementado — `record_session`/`record_assessment`/`record_evolution` + deletion test; sessions/clinical/prontuario migrados. Meta/attachment/report/battery/spm ainda usam `create_timeline_event`.
- **Testes:** `tests/test_clinical_activity.py`

### 3.4 C5 — PatientView (Cluster B, último)

- **Confiança:** Worth exploring · **Estilo:** local-substitutable · **Repo:** web
- **Interface:**
  ```
  toPatientView(PatientDto) → PatientView   // + peers: SessionView, AssessmentView...
  ```
- **Arquivos (web):** `src/lib/api/views/patient-view.ts` (novo) + peers. `src/lib/api/types.ts` deixa de importar `mock-data.ts`. `mock-data.ts` reduz-se a `statusConfig` + seeds; **seed morto deletado**.
- **Testes:** `views/patient-view.test.ts` — dois adapters: `DTO→view` (real) e `fake→view` (mock-data residual); asserção de que `types.ts` não importa `mock-data`.

---

## 4. Cross-cutting

### 4.1 Estratégia de erro (uniforme, deep modules)

Cada módulo trata erros no interior; a interface expõe **um tipo de resultado**, não exceções espalhadas:

| Candidato | Retorno de falha | Observação |
|-----------|------------------|------------|
| C1 | `Descriptor \| undefined` | protocolo desconhecido é normal em dev, sem throw |
| C2 | `ScoreError` interno capturado na borda do submit web | entrada inválida (resp. ausente / mode sem engine) nunca vaza `%`/norma p/ UI |
| C3 | `Slice` vazia é válida ("prontuário vazio"); `appendNote → NoteRef \| Error` | falha de persistência como erro explícito do módulo, não 500 do router |
| C4 | `recordX → EventRef \| Error` | falha de emissão não derruba o caller — logada internamente (idempotência por `source_id`) |
| C5 | `PatientView` com valores `null` explícitos se DTO malformado | em dev deve ser inexistente; se aparecer, é bug do DTO a eliminar |

### 4.2 Migração (sem retrocompatibilidade)

Substituição de raiz por candidato. Sem depreciação. Between clusters: checkpoint A (C1+C2 verdes) e checkpoint B (C3+C4+C5 verdes = fim do programa).

### 4.3 Isolamento e clareza das unidades

Cada candidato é uma árvore de arquivos focada (1 serviço/diretório + testes). Sem arquivo "saguão". Cada módulo responde "o que faz / como usa / do que depende" sem ler o interno do outro — mandato do brainstorming para unidades bem-delimitadas.

---

## 5. Referências

- Review de origem: `architecture-review-20260712-204203.html`
- Vocabulário (module · interface · implementation · depth · seam · adapter · leverage · locality): codebase-design.
- Domínio (Instrumento/Protocolo · Aplicação · Paciente · Timeline · Responsável): `korus-one-web/CONTEXT.md`.
- Sem ADRs em `docs/adr/` (a ausência é notada pelo review; não é escopo deste programa criar ADRs).