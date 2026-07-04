from typing import Any

from app.services.instrument_content_package import InstrumentContentPackage

MASTERY_ACQUIRED = 2


class InstrumentScoringService:
    @staticmethod
    def score(package: InstrumentContentPackage, answers: dict[str, Any]) -> dict[str, Any]:
        engine = package.scoring.get("engine", "scaled_sum")
        dispatch = {
            "scaled_sum": InstrumentScoringService._score_scaled_sum,
            "scaled_likert_mean": InstrumentScoringService._score_scaled_likert_mean,
            "domain_mastery": InstrumentScoringService._score_domain_mastery,
            "battery_module": InstrumentScoringService._score_battery_module,
            "observational_rubric": InstrumentScoringService._score_observational_rubric,
        }
        handler = dispatch.get(engine)
        if not handler:
            raise ValueError(f"Unsupported scoring engine: {engine}")
        return handler(package, answers)

    @staticmethod
    def _require_answer(answers: dict[str, Any], item_id: str) -> int | float:
        raw = answers.get(item_id)
        if raw is None:
            raise ValueError(f"Resposta obrigatória ausente: {item_id}")
        return int(raw) if isinstance(raw, (int, float, str)) and str(raw).isdigit() else float(raw)

    @staticmethod
    def _score_scaled_sum(
        package: InstrumentContentPackage, answers: dict[str, Any]
    ) -> dict[str, Any]:
        domain_config = package.scoring.get("domains", {})
        domain_scores: dict[str, float | int] = {}

        for domain_id, config in domain_config.items():
            method = config.get("method", "sum")
            if method == "item_value":
                domain_scores[domain_id] = int(
                    InstrumentScoringService._require_answer(answers, config["item_id"])
                )
            elif method == "sum":
                total = 0
                for item_id in config.get("item_ids", []):
                    total += int(InstrumentScoringService._require_answer(answers, item_id))
                domain_scores[domain_id] = total
            else:
                raise ValueError(f"Unsupported domain scoring method: {method}")

        total = domain_scores.get("TOTAL")
        if total is None and len(domain_scores) == 1:
            total = next(iter(domain_scores.values()))

        interpretation = InstrumentScoringService._match_interpretation(
            package, float(total) if total is not None else 0.0
        )
        level_label = InstrumentScoringService._level_label(package, total)
        summary = InstrumentScoringService._build_summary(package, total)
        detail = InstrumentScoringService._build_detail(interpretation, level_label)

        return {
            "engine": "scaled_sum",
            "domains": domain_scores,
            "total": total,
            "interpretation": interpretation,
            "level_label": level_label,
            "summary": summary,
            "detail": detail,
            "suggested_goals": InstrumentScoringService._suggested_goals(package, domain_scores),
            "cutoffs": package.scoring.get("cutoffs", []),
        }

    @staticmethod
    def _score_scaled_likert_mean(
        package: InstrumentContentPackage, answers: dict[str, Any]
    ) -> dict[str, Any]:
        domain_config = package.scoring.get("domains", {})
        domain_scores: dict[str, float] = {}

        for domain_id, config in domain_config.items():
            item_ids = config.get("item_ids", [])
            values = [
                float(InstrumentScoringService._require_answer(answers, item_id))
                for item_id in item_ids
            ]
            domain_scores[domain_id] = round(sum(values) / len(values), 2) if values else 0.0

        total = domain_scores.get("TOTAL") or (
            next(iter(domain_scores.values())) if domain_scores else 0.0
        )
        interpretation = InstrumentScoringService._match_interpretation(package, float(total))
        summary = f"Média {total:.2f} — {package.instrument_title}"
        detail = InstrumentScoringService._build_detail(interpretation, None)

        return {
            "engine": "scaled_likert_mean",
            "domains": domain_scores,
            "total": total,
            "interpretation": interpretation,
            "level_label": None,
            "summary": summary,
            "detail": detail,
            "suggested_goals": [],
        }

    @staticmethod
    def _score_domain_mastery(
        package: InstrumentContentPackage, answers: dict[str, Any]
    ) -> dict[str, Any]:
        domain_config = package.scoring.get("domains", {})
        domain_scores: dict[str, float] = {}
        suggested_goals: list[dict[str, Any]] = []

        for domain_id, config in domain_config.items():
            item_ids = config.get("item_ids", [])
            if not item_ids:
                continue
            acquired = sum(
                1
                for item_id in item_ids
                if answers.get(item_id) is not None
                and int(answers[item_id]) >= MASTERY_ACQUIRED
            )
            pct = round((acquired / len(item_ids)) * 100, 1)
            domain_scores[domain_id] = pct
            if pct < 50:
                suggested_goals.append(
                    {
                        "domain": domain_id,
                        "text": f"Desenvolver habilidades do domínio {domain_id} ({pct:.0f}% adquirido)",
                        "priority": "high" if pct < 30 else "medium",
                    }
                )

        overall = (
            round(sum(domain_scores.values()) / len(domain_scores), 1) if domain_scores else 0.0
        )
        interpretation = InstrumentScoringService._match_interpretation(package, overall)
        summary = f"Mestria geral {overall:.1f}% — {package.instrument_title}"

        return {
            "engine": "domain_mastery",
            "domains": domain_scores,
            "total": overall,
            "interpretation": interpretation,
            "level_label": None,
            "summary": summary,
            "detail": interpretation,
            "suggested_goals": suggested_goals,
        }

    @staticmethod
    def _score_battery_module(
        package: InstrumentContentPackage, answers: dict[str, Any]
    ) -> dict[str, Any]:
        subtest_config = package.scoring.get("subtests", {})
        subtest_scores: dict[str, int | float] = {}

        for subtest_id, config in subtest_config.items():
            item_ids = config.get("item_ids", [])
            if not item_ids:
                continue
            if not all(answers.get(item_id) is not None for item_id in item_ids):
                continue
            subtest_scores[subtest_id] = sum(
                int(InstrumentScoringService._require_answer(answers, item_id))
                for item_id in item_ids
            )

        composite = sum(subtest_scores.values()) if subtest_scores else 0
        summary = f"Bateria {package.instrument_title} — {len(subtest_scores)} subteste(s)"

        return {
            "engine": "battery_module",
            "domains": subtest_scores,
            "total": composite,
            "interpretation": None,
            "level_label": None,
            "summary": summary,
            "detail": ", ".join(f"{k}: {v}" for k, v in subtest_scores.items()),
            "suggested_goals": [],
            "subtests": subtest_scores,
        }

    @staticmethod
    def _score_observational_rubric(
        package: InstrumentContentPackage, answers: dict[str, Any]
    ) -> dict[str, Any]:
        module_config = package.scoring.get("modules", {})
        module_scores: dict[str, float] = {}
        pending_modules: list[str] = []

        for module_id, config in module_config.items():
            item_ids = config.get("item_ids", [])
            answered = [item_id for item_id in item_ids if answers.get(item_id) is not None]
            if not answered:
                pending_modules.append(module_id)
                continue
            values = [float(answers[item_id]) for item_id in answered]
            module_scores[module_id] = round(sum(values) / len(values), 2)

        overall = (
            round(sum(module_scores.values()) / len(module_scores), 2) if module_scores else None
        )
        summary = package.instrument_title
        if pending_modules:
            summary += f" — {len(pending_modules)} módulo(s) pendente(s)"

        return {
            "engine": "observational_rubric",
            "domains": module_scores,
            "total": overall,
            "interpretation": None,
            "level_label": None,
            "summary": summary,
            "detail": None,
            "suggested_goals": [],
            "pending_modules": pending_modules,
        }

    @staticmethod
    def _match_interpretation(package: InstrumentContentPackage, total: float) -> str | None:
        for band in package.scoring.get("interpretations", []):
            minimum = float(band["min"])
            maximum = float(band["max"])
            if minimum <= total <= maximum:
                return str(band["label"])
        return None

    @staticmethod
    def _level_label(package: InstrumentContentPackage, total: Any) -> str | None:
        if total is None:
            return None
        scale_labels = {int(entry["value"]): entry["label"] for entry in package.scale}
        return scale_labels.get(int(total))

    @staticmethod
    def _build_summary(package: InstrumentContentPackage, total: Any) -> str:
        if package.slug == "fois" and total is not None:
            return f"FOIS nível {total}"
        if total is not None:
            return f"{package.instrument_title} — total {total}"
        return package.instrument_title

    @staticmethod
    def _build_detail(interpretation: str | None, level_label: str | None) -> str | None:
        parts = [p for p in [interpretation, level_label] if p]
        return " — ".join(parts) if parts else None

    @staticmethod
    def _suggested_goals(
        package: InstrumentContentPackage, domain_scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        goals: list[dict[str, Any]] = []
        for cutoff in package.scoring.get("cutoffs", []):
            domain = cutoff.get("domain", "TOTAL")
            value = domain_scores.get(domain)
            if value is None:
                continue
            threshold = cutoff.get("value")
            op = cutoff.get("operator", ">=")
            triggered = (
                (op == ">=" and value >= threshold)
                or (op == ">" and value > threshold)
                or (op == "<=" and value <= threshold)
            )
            if triggered:
                goals.append(
                    {
                        "domain": domain,
                        "text": cutoff.get("label", "Acompanhamento clínico indicado"),
                        "priority": "high",
                    }
                )
        return goals
