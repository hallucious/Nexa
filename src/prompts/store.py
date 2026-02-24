from pathlib import Path
from .registry import PROMPT_REGISTRY


class PromptStore:
    """Load prompt templates.

    Backward compatible:
    - Versioned IDs: "g7_final_review@v1" (preferred)
    - Legacy filenames: "g7_final_review.prompt.txt"
    """

    BASE_DIR = Path(__file__).parent

    @classmethod
    def load(cls, key: str) -> str:
        # Versioned ID path
        if key in PROMPT_REGISTRY:
            file_name = PROMPT_REGISTRY[key]["file"]
            path = cls.BASE_DIR / file_name
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found for id '{key}': {path}")
            return path.read_text(encoding="utf-8")

        # Legacy filename path (kept for tests and incremental migration)
        if key.endswith(".prompt.txt") or key.endswith(".txt"):
            path = cls.BASE_DIR / key
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            return path.read_text(encoding="utf-8")

        raise ValueError(f"Unknown prompt key (not in registry and not a filename): {key}")
