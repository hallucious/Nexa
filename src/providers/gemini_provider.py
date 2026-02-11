from src.providers.safe_mode import apply_safe_mode

class GeminiProvider:
    def generate(self, prompt: str) -> str:
        prompt = apply_safe_mode(prompt)
        # existing Gemini API call here
        return "<gemini-response>"
