"""NEXUS-hosted ICT Mentor advisory runtime; never executes trades."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "agents" / "ict_mentor"


class ICTMentorRuntime:
    def __init__(self, model_router, storage):
        self.model_router = model_router
        self.storage = storage
        self.system_prompt = (AGENT_DIR / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
        self.input_schema = json.loads((AGENT_DIR / "schemas/input.schema.json").read_text(encoding="utf-8"))
        self.output_schema = json.loads((AGENT_DIR / "schemas/output.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(self.input_schema)
        Draft202012Validator.check_schema(self.output_schema)
        self.input_validator = Draft202012Validator(self.input_schema, format_checker=FormatChecker())
        self.output_validator = Draft202012Validator(self.output_schema, format_checker=FormatChecker())

    def _blocked(self, reason: str):
        return {
            "agent_id": "ict_mentor",
            "mode": "advisory",
            "answer": "تحلیل تخصصی انجام نشد؛ ورودی یا شواهد کافی برای پاسخ معتبر در دسترس نیست.",
            "source_claims": [],
            "user_rules_used": [],
            "agent_inferences": [],
            "proposed_actions": [],
            "risk_decision": "blocked_insufficient_information",
            "execution_result": None,
            "uncertainties": [reason],
        }

    def invoke(self, payload: dict):
        errors = list(self.input_validator.iter_errors(payload))
        if errors:
            raise ValueError(f"Invalid ICT Mentor input: {errors[0].message}")

        sources = payload.get("retrieved_sources", [])
        if not sources:
            query = payload["request"]
            matches = self.storage.search_knowledge(query, limit=8)
            sources = [{
                "source_id": item["source_id"],
                "title": item["title"],
                "url": item["url"],
                "retrieved_at": item["retrieved_at"],
                "segment_id": item["segment_id"],
                "timestamp_start": item["timestamp_start"],
                "timestamp_end": item["timestamp_end"],
                "summary": item["text"][:1200],
            } for item in matches]
            payload = {**payload, "retrieved_sources": sources}

        prompt = (
            "Return one JSON object only. Follow the output schema exactly.\n"
            "INPUT:\n" + json.dumps(payload, ensure_ascii=False) + "\n"
            "AVAILABLE SOURCE SEGMENTS:\n" + json.dumps(sources, ensure_ascii=False)
        )
        try:
            raw = self.model_router.generate(self.system_prompt, prompt)
            result = json.loads(raw)
        except Exception as exc:
            return self._blocked(f"Specialist response unavailable or invalid ({type(exc).__name__}).")

        errors = list(self.output_validator.iter_errors(result))
        if errors:
            return self._blocked("Specialist output did not satisfy the required advisory contract.")

        valid_sources = {(item["source_id"], item["segment_id"]) for item in sources}
        if any((claim["source_id"], claim["segment_id"]) not in valid_sources for claim in result["source_claims"]):
            return self._blocked("A source claim did not match a retrieved source segment.")
        confirmed_rules = {
            (rule["rule_id"], rule["text"])
            for rule in payload.get("user_rules", [])
            if rule.get("status") == "user_confirmed"
        }
        if any((rule["rule_id"], rule["text"]) not in confirmed_rules for rule in result["user_rules_used"]):
            return self._blocked("A user rule was not explicitly confirmed in the invocation.")
        # These are hard invariants, even if a future schema is accidentally relaxed.
        result["execution_result"] = None
        result["mode"] = "advisory"
        return result
