"""Адаптер LLM (раздел 7 ТЗ).

Единый интерфейс LLMAdapter.chat(system_prompt, messages, temperature) -> LLMResponse.
Фабрика get_llm_provider() выбирает провайдера по LLM_PROVIDER в .env.
Переключение модели — сменой LLM_PROVIDER, БЕЗ правки кода оркестратора.

Доступные провайдеры:
- openai          : OpenAI (gpt-4o-mini и др.)
- anthropic       : Anthropic (claude-*)
- yandexgpt       : YandexGPT (через совместимый прокси или нативный SDK)
- hermes          : Hermes через Nous Portal (OpenAI-совместимый API)
- deepseek        : DeepSeek (OpenAI-совместимый API)
- tencent_hy3     : Nous Portal (Hermes-4-70B по умолчанию; tencent/hy3:free
                    требует спец. формат тега — опционально)
"""
import os
import time


class LLMResponse:
    def __init__(self, text: str, tokens_prompt: int = 0, tokens_completion: int = 0,
                 latency_ms: int = 0, model_name: str = ""):
        self.text = text
        self.tokens_prompt = tokens_prompt
        self.tokens_completion = tokens_completion
        self.latency_ms = latency_ms
        self.model_name = model_name


class LLMAdapter:
    """Базовый класс. Наследники реализуют chat()."""
    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError


class OpenAIProvider(LLMAdapter):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        self.model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        t0 = time.monotonic()
        resp = self.client.chat.completions.create(
            model=self.model, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = getattr(resp, 'usage', None)
        return LLMResponse(
            text=resp.choices[0].message.content,
            tokens_prompt=getattr(usage, 'prompt_tokens', 0) if usage else 0,
            tokens_completion=getattr(usage, 'completion_tokens', 0) if usage else 0,
            latency_ms=latency_ms, model_name=self.model,
        )


class AnthropicProvider(LLMAdapter):
    def __init__(self):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model, temperature=temperature, max_tokens=1024,
            system=system_prompt,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        return LLMResponse(
            text=resp.content[0].text,
            tokens_prompt=resp.usage.input_tokens,
            tokens_completion=resp.usage.output_tokens,
            latency_ms=latency_ms, model_name=self.model,
        )


class YandexGPTProvider(LLMAdapter):
    def __init__(self):
        from yandex_cloud_ml_sdk import YCloudML
        self.sdk = YCloudML(
            folder_id=os.environ['YANDEX_FOLDER_ID'],
            auth=os.environ['YANDEX_API_KEY'],
        )
        self.model = os.environ.get('YANDEX_MODEL', 'yandexgpt')

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        t0 = time.monotonic()
        model = self.sdk.models.completions(self.model)
        resp = model.run(messages=[{"role": "system", "text": system_prompt}, *messages], temperature=temperature)
        latency_ms = int((time.monotonic() - t0) * 1000)
        return LLMResponse(text=resp[0].text, latency_ms=latency_ms, model_name=self.model)


class HermesProvider(LLMAdapter):
    """Hermes через Nous Portal (OpenAI-совместимый API)."""
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ['NOUS_PORTAL_API_KEY'],
            base_url=os.environ.get('NOUS_PORTAL_BASE_URL', 'https://inference-api.nousresearch.com/v1'),
        )
        self.model = os.environ.get('NOUS_PORTAL_MODEL', 'tencent/hy3')

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        max_tokens = int(os.environ.get('NOUS_PORTAL_MAX_TOKENS', '1024'))
        stream = os.environ.get('NOUS_PORTAL_STREAM', 'false').lower() in ('1', 'true', 'yes')
        t0 = time.monotonic()
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=temperature, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system_prompt}, *messages],
                stream=stream,
            )
        except Exception:
            # Fallback: некоторые модели (stepfun:free и др.) не отдают контент
            # в non-streaming режиме — повторяем со streaming.
            resp = self.client.chat.completions.create(
                model=self.model, temperature=temperature, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system_prompt}, *messages],
                stream=True,
            )
            stream = True
        if stream:
            text_parts = []
            finish_reason = None
            for chunk in resp:
                if not getattr(chunk, "choices", None):
                    continue
                ch = chunk.choices[0]
                if getattr(ch, "finish_reason", None):
                    finish_reason = ch.finish_reason
                delta = getattr(ch.delta, "content", None)
                if delta:
                    text_parts.append(delta)
            text = "".join(text_parts)
        else:
            text = resp.choices[0].message.content
        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = getattr(resp, 'usage', None) if not stream else None
        return LLMResponse(
            text=text,
            tokens_prompt=getattr(usage, 'prompt_tokens', 0) if usage else 0,
            tokens_completion=getattr(usage, 'completion_tokens', 0) if usage else 0,
            latency_ms=latency_ms, model_name=self.model,
        )


class DeepSeekProvider(LLMAdapter):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ['DEEPSEEK_API_KEY'],
            base_url=os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
        )
        self.model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        t0 = time.monotonic()
        resp = self.client.chat.completions.create(
            model=self.model, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = getattr(resp, 'usage', None)
        return LLMResponse(
            text=resp.choices[0].message.content,
            tokens_prompt=getattr(usage, 'prompt_tokens', 0) if usage else 0,
            tokens_completion=getattr(usage, 'completion_tokens', 0) if usage else 0,
            latency_ms=latency_ms, model_name=self.model,
        )


class TencentHY3Provider(LLMAdapter):
    """Nous Portal (тот же OpenAI-совместимый endpoint, что и HermesProvider).
    По умолчанию Hermes-4-70B. tencent/hy3:free требует незадокументированный
    формат тега — оставлен как опция через TENCENT_HY3_MODEL / NOUS_PORTAL_MODEL.
    """
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ['NOUS_PORTAL_API_KEY'],
            base_url=os.environ.get('NOUS_PORTAL_BASE_URL', 'https://inference-api.nousresearch.com/v1'),
        )
        self.model = os.environ.get('NOUS_PORTAL_MODEL',
                         os.environ.get('TENCENT_HY3_MODEL', 'tencent/hy3'))

    def chat(self, system_prompt: str, messages: list[dict], temperature: float = 0.2) -> LLMResponse:
        max_tokens = int(os.environ.get('NOUS_PORTAL_MAX_TOKENS', '1024'))
        t0 = time.monotonic()
        resp = self.client.chat.completions.create(
            model=self.model, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = getattr(resp, 'usage', None)
        return LLMResponse(
            text=resp.choices[0].message.content,
            tokens_prompt=getattr(usage, 'prompt_tokens', 0) if usage else 0,
            tokens_completion=getattr(usage, 'completion_tokens', 0) if usage else 0,
            latency_ms=latency_ms, model_name=self.model,
        )


_PROVIDERS = {
    'openai': OpenAIProvider,
    'anthropic': AnthropicProvider,
    'yandexgpt': YandexGPTProvider,
    'hermes': HermesProvider,
    'deepseek': DeepSeekProvider,
    'tencent_hy3': TencentHY3Provider,
}


def get_llm_provider() -> 'LLMAdapter':
    from ai_consultant.services.llm_adapter_stub import OfflineProvider
    name = os.environ.get('LLM_PROVIDER', 'openai')
    cls = _PROVIDERS.get(name)
    if not cls:
        # неизвестный провайдер — не падаем, отдаём заглушку
        return OfflineProvider(
            reason=f"Неизвестный LLM_PROVIDER: {name}. Допустимо: {list(_PROVIDERS)}"
        )
    try:
        return cls()
    except KeyError as e:
        # нет нужного API-ключа в окружении (Render и т.п.)
        return OfflineProvider(reason=f"Не задан API-ключ для провайдера «{name}»: {e}")
    except Exception as e:  # noqa
        return OfflineProvider(reason=f"Ошибка инициализации провайдера «{name}»: {e}")
