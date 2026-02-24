
from pathlib import Path


class PromptStore:
    BASE_DIR = Path(__file__).parent

    @classmethod
    def load(cls, name: str) -> str:
        path = cls.BASE_DIR / name
        return path.read_text(encoding="utf-8")
