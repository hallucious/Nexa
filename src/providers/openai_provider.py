from src.providers.safe_mode import apply_safe_mode

class OpenAIProvider:
    def generate(self, prompt: str) -> str:
        prompt = apply_safe_mode(prompt)
        # existing OpenAI GPT-4.1 call here
        return "<openai-response>"
