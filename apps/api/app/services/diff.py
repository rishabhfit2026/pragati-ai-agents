from __future__ import annotations

from typing import Any


def diff_analyses(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    old_score, new_score = old["score"]["final_score"], new["score"]["final_score"]
    old_rec, new_rec = old["decision"]["final_recommendation"], new["decision"]["final_recommendation"]

    sub_score_changes = {}
    for key in ("technical_fit", "capability_fit", "compliance_readiness", "strategic_fit",
                "commercial_attractiveness", "delivery_feasibility"):
        ov, nv = old["score"].get(key), new["score"].get(key)
        if ov != nv:
            sub_score_changes[key] = {"old": ov, "new": nv, "delta": round((nv or 0) - (ov or 0), 1)}

    old_reqs, new_reqs = len(old["requirements"]), len(new["requirements"])
    old_gaps = sum(1 for r in old["requirements"] if (r.get("capability_match") or {}).get("status") == "GAP")
    new_gaps = sum(1 for r in new["requirements"] if (r.get("capability_match") or {}).get("status") == "GAP")

    return {
        "score_changed": old_score != new_score,
        "score_delta": round((new_score or 0) - (old_score or 0), 1),
        "recommendation_changed": old_rec != new_rec,
        "old_score": old_score, "new_score": new_score,
        "old_recommendation": old_rec, "new_recommendation": new_rec,
        "sub_score_changes": sub_score_changes,
        "requirement_count_delta": new_reqs - old_reqs,
        "gap_count_delta": new_gaps - old_gaps,
        "old_config": {
            "llm_provider": old["llm_provider"], "llm_model": old["llm_model"],
            "prompt_version": old["prompt_version"], "scoring_version": old["scoring_version"],
        },
        "new_config": {
            "llm_provider": new["llm_provider"], "llm_model": new["llm_model"],
            "prompt_version": new["prompt_version"], "scoring_version": new["scoring_version"],
        },
    }
