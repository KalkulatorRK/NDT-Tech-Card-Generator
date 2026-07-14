"""Эмбеддинги фрагментов нормативных документов.

Фиксированная модель (независимо от генеративного LLM, раздел 8 ТЗ),
по умолчанию OpenAI text-embedding-3-small (1536 изм.).
Батчинг по 50 фрагментов; защита от лимита токенов: текст > 24000 символов
обрезается (text-embedding-3-small ~ 8192 токена).
"""
import os

EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')
EMBEDDING_DIM = int(os.environ.get('EMBEDDING_DIM', '1536'))


def get_embedding_model_name() -> str:
    return EMBEDDING_MODEL


def _truncate(text: str, limit: int = 24000) -> str:
    return text[:limit] if len(text) > limit else text


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Возвращает список векторов для списка текстов."""
    if not texts:
        return []
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    batch_size = 50
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = [_truncate(t) for t in texts[i:i + batch_size]]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend([d.embedding for d in resp.data])
    return vectors


def embed_query(text: str) -> list[float]:
    """Вектор для поискового запроса."""
    return embed_texts([text])[0]
