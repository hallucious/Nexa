
class PromptRenderer:

    @staticmethod
    def render(template: str, **kwargs) -> str:
        result = template
        for k, v in kwargs.items():
            result = result.replace("{{" + k + "}}", str(v))
        return result
