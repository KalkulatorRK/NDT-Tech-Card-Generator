"""Заглушка LLM-провайдера для случаев, когда не задан API-ключ
или провайдер недоступен (например, на Render не прописаны переменные окружения).

Вместо падения с KeyError и возврата HTML-ошибки фронтенду
(что даёт «Unexpected token '<'»), возвращаем аккуратный ответ,
поясняющий причину. Фронт показывает его как обычное сообщение
консультанта, не ломаясь.
"""
from ai_consultant.services.llm_adapter import LLMAdapter, LLMResponse


class OfflineProvider(LLMAdapter):
    """Провайдер-заглушка: сообщает, что LLM недоступен и почему."""

    def __init__(self, reason: str = ""):
        self.reason = reason or "LLM-провайдер недоступен."

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        text = (
            "Извините, сейчас я работаю в ограниченном режиме: модуль языковой "
            "модели (LLM) на сервере не настроен. Точные ответы по формулам и "
            "нормативным таблицам (через встроенные инструменты) доступны, но "
            "свободный диалог временно отключён.\n\n"
            f"Техническая причина: {self.reason}"
        )
        return LLMResponse(text=text, model_name="offline-stub")
