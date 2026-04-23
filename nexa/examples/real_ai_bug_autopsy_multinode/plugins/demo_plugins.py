"""
demo_plugins.py

Deterministic plugin implementations for the investment divergence demo.

Node1: normalize_company_text  — cleans raw company text
Node3: score_analysis          — scores analysis text deterministically
Node4: make_investment_decision — maps score → INVEST / DO_NOT_INVEST
"""
from __future__ import annotations

import re


def normalize_company_text(raw_text: str) -> dict:
    """Node1 — deterministic normalization.

    Lowercases, strips extra whitespace, removes punctuation artifacts.
    Returns: {"normalized_company_text": str}
    """
    text = (raw_text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\.\,\-]", "", text)
    return {"normalized_company_text": text}


def score_analysis(analysis_text) -> dict:
    """Node3 — deterministic scoring.

    Accepts either a plain string or a dict with a 'text' key.
    Scores based on presence of risk/fragility/uncertainty keywords.
    Returns: {"score": int}  (0–100, higher = more risk)
    """
    if isinstance(analysis_text, dict):
        text = str(analysis_text.get("text", analysis_text))
    else:
        text = str(analysis_text or "")

    text_lower = text.lower()

    # Risk-signal keywords → raise score
    high_risk = ["fragil", "uncertain", "unstable", "volatile", "risk", "concern",
                 "decline", "downtur", "weak", "challeng", "threat", "vulnerab"]
    # Continuity/stability keywords → lower score
    low_risk = ["continuity", "stable", "reliable", "consistent", "growth",
                "resilient", "strong", "robust", "proven", "sustain"]

    score = 50  # baseline
    for kw in high_risk:
        count = text_lower.count(kw)
        score += count * 5
    for kw in low_risk:
        count = text_lower.count(kw)
        score -= count * 5

    score = max(0, min(100, score))
    return {"score": score}


def make_investment_decision(score) -> dict:
    """Node4 — deterministic decision gate.

    score < 55  → INVEST
    score >= 55 → DO_NOT_INVEST
    Returns: {"final_decision": str}
    """
    if isinstance(score, dict):
        score = score.get("score", 50)
    score = int(score)

    decision = "INVEST" if score < 55 else "DO_NOT_INVEST"
    return {"final_decision": decision}
