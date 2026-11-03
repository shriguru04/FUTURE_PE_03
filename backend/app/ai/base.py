class ProviderError(Exception):
    """Raised for any provider failure. Message must never contain secrets."""


class Provider:
    name = "base"
    model = ""
    is_mock = False

    def complete(self, system: str, user: str, max_tokens: int = 2000, json_mode: bool = True):
        """Returns (text, usage) where usage = {'input_tokens': int|None, 'output_tokens': int|None}."""
        raise NotImplementedError
