from __future__ import annotations

import re
from typing import Any, Dict, List

from fastmcp import FastMCP

mcp = FastMCP("Resume Bullet Tools (FastMCP)")


ACTION_VERBS: List[str] = [
    "Led", "Built", "Designed", "Implemented", "Optimized", "Automated",
    "Improved", "Reduced", "Accelerated", "Delivered", "Scaled", "Streamlined",
    "Developed", "Launched", "Spearheaded", "Refactored", "Integrated",
]

WEAK_PHRASES: List[str] = [
    "responsible for", "worked on", "helped with", "did", "tasked with", "involved in"
]


def _score_bullet(bullet: str) -> Dict[str, Any]:
    b = bullet.strip()
    score = 5

    if any(b.startswith(v + " ") for v in ACTION_VERBS):
        score += 2
    if re.search(r"\b\d+(\.\d+)?%?\b", b):
        score += 2
    if len(b) > 180:
        score -= 1

    low = b.lower()
    if any(p in low for p in WEAK_PHRASES):
        score -= 2

    score = max(0, min(10, score))
    issues: List[str] = []
    if score <= 5:
        if not any(b.startswith(v + " ") for v in ACTION_VERBS):
            issues.append("Doesn't start with a strong action verb.")
        if not re.search(r"\b\d+(\.\d+)?%?\b", b):
            issues.append("No measurable impact (numbers/metrics).")
        if any(p in low for p in WEAK_PHRASES):
            issues.append("Contains weak phrasing (e.g., 'worked on', 'helped with').")
    return {"score": score, "issues": issues}


@mcp.tool
def resume_bullet_tool(bullet: str, target_role: str = "Software Engineer") -> Dict[str, Any]:
    """
    Rewrite a resume bullet to be stronger and more impact-oriented.
    Returns rewritten variants + a heuristic score + issues.
    """
    original = bullet.strip()

    verb = "Improved"
    lower = original.lower()
    for v in ACTION_VERBS:
        if "deploy" in lower and v in ["Implemented", "Delivered", "Scaled"]:
            verb = v
            break
        if "optimiz" in lower and v == "Optimized":
            verb = v
            break
        if "automat" in lower and v == "Automated":
            verb = v
            break

    cleaned = original
    for p in WEAK_PHRASES:
        cleaned = re.sub(re.escape(p), "", cleaned, flags=re.IGNORECASE).strip()

    metric_hint = ""
    if not re.search(r"\b\d+(\.\d+)?%?\b", cleaned):
        metric_hint = " (add metric: e.g., reduced latency by X% / saved Y hrs/week)"

    variants = [
        f"{verb} {cleaned}{metric_hint}",
        f"{verb} {cleaned} for {target_role}{metric_hint}",
        f"{verb} {cleaned}; contributed to measurable outcomes{metric_hint}",
    ]

    scored = [(v, _score_bullet(v)["score"]) for v in variants]
    best_variant = max(scored, key=lambda x: x[1])[0]
    best_score_info = _score_bullet(best_variant)

    return {
        "original": original,
        "best_variant": best_variant,
        "variants": variants,
        "score": best_score_info["score"],
        "issues": best_score_info["issues"],
    }


if __name__ == "__main__":
    # We'll run with the fastmcp CLI in Docker (recommended).
    # You can still run directly for local debugging:
    #   python mcp_tool_server.py
    mcp.run(transport="http", host="0.0.0.0", port=9000)
