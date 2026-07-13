# C2 — ScoringSession Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deepen scoring behind `ScoringSession` so callers get `NormalizedScores` without knowing engines; `assessment_scoring.py` becomes thin delegates.

**Architecture:** YAGNI slice 1 = **manifest only**. Battery/SPM/client stay behind existing engines. `ScoringSession.from_protocol` + `.score(answers)` + `.to_assessment_fields()`. Web: Manifest form stops inventing `%` when scores exist (API derives).

**Tech Stack:** Python 3.11 · FastAPI · pytest · TypeScript (web thin fix)

**Repos:** api (primary) + web (ManifestInstrumentForm)

---

### Task 1: `NormalizedScores` + `ScoringSession` (manifest) — TDD

**Files:**
- Create: `app/services/scoring_session.py`
- Create: `tests/test_scoring_session.py`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Implement `scoring_session.py`**
- [ ] **Step 3: Tests green**

### Task 2: Thin `assessment_scoring.py` delegates

- [ ] Re-export / wrap via `ScoringSession`; keep public signatures stable
- [ ] `test_assessment_scoring.py` stays green

### Task 3: `clinical.py` uses `ScoringSession` for manifest create

- [ ] Replace `score_manifest_protocol` + `build_assessment_from_scores` pair with session.score when mode=manifest and scores is None

### Task 4: Web — ManifestInstrumentForm omit local `%`

- [ ] When posting with `scores`, omit `percentage` (or set undefined) so API `NormalizedScores` wins
- [ ] Vitest / typecheck on touched files if applicable

### Task 5: Checkpoint A partial note

- [ ] Update mother spec §3.1 status; C2 DoD: two adapters (real FOIS + fixture scores dict) documented in `test_scoring_session.py`

**Deferred:** battery/SPM engines behind ScoringSession; `result-analysis.ts` (no prod callers).
