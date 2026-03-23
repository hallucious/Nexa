from __future__ import annotations

import os
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
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
            "[ERROR] OPENAI_API_KEY not found\n\n"
            "Fix:\n"
            "1. Create a .env file in project root\n"
            "2. Add:\n"
            "   OPENAI_API_KEY=your_key_here\n\n"
            "OR\n\n"
            "export OPENAI_API_KEY=your_key_here\n"
        )
        return cls(api_key=key)

    def judge_continuity(self, *, pic_text: str, current_text: str) -> ContinuityJudgement:
        pic = (pic_text or "").strip()
        cur = (current_text or "").strip()
        if not pic or not cur:
            return ContinuityJudgement(verdict="UNKNOWN", rationale="empty input")
        if pic == cur:
            return ContinuityJudgement(verdict="SAME", rationale="exact match")
        return ContinuityJudgement(verdict="DRIFT", rationale="content differs (heuristic)")
