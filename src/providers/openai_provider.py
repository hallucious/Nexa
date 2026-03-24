from __future__ import annotations

import os

from src.providers.env_diagnostics import resolve_api_key_or_raise
from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuityJudgement:
    verdict: str
    rationale: str = ""


class OpenAIProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @classmethod
    def from_env(cls) -> "OpenAIProvider":
        key = resolve_api_key_or_raise("OPENAI_API_KEY")
        return cls(api_key=key)

    def judge_continuity(self, *, pic_text: str, current_text: str) -> ContinuityJudgement:
        pic = (pic_text or "").strip()
        cur = (current_text or "").strip()
        if not pic or not cur:
            return ContinuityJudgement(verdict="UNKNOWN", rationale="empty input")
        if pic == cur:
            return ContinuityJudgement(verdict="SAME", rationale="exact match")
        return ContinuityJudgement(verdict="DRIFT", rationale="content differs (heuristic)")
