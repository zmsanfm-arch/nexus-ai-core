from dataclasses import dataclass

@dataclass
class ModelConfig:
    provider: str
    base_url: str
    model_name: str

class ModelRouter:
    """Provider-neutral interface. Add authenticated adapters after selecting a provider."""
    def __init__(self, primary: ModelConfig | None = None):
        self.primary = primary

    def select(self, task_type: str) -> ModelConfig | None:
        # Initial MVP: one configured primary model; multi-model routing is an extension point.
        return self.primary
