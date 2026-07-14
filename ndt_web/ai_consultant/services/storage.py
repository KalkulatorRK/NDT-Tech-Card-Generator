"""Хранилище файлов документов (S3-совместимое: AWS S3, Cloudflare R2, Yandex Object Storage).

Клиент создаётся через endpoint_url (переносимость между облаками, раздел 6.2 ТЗ).
Импорт boto3 — внутри функций, чтобы отсутствие пакета не ломало импорт приложения.
"""
import os


def _get_client():
    import boto3  # ленивый импорт
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('S3_ACCESS_KEY'),
        aws_secret_access_key=os.environ.get('S3_SECRET_KEY'),
        region_name=os.environ.get('S3_REGION', 'auto'),
    )


def upload_document(local_path: str, storage_key: str) -> str:
    """Загружает файл в бакет. Возвращает storage_key. Пропускает, если S3 не настроен."""
    if not os.environ.get('S3_ENDPOINT_URL'):
        return storage_key  # хранение локально, ключ не требуется
    client = _get_client()
    bucket = os.environ['S3_BUCKET_DOCUMENTS']
    client.upload_file(local_path, bucket, storage_key)
    return storage_key


def get_document_url(storage_key: str) -> str | None:
    """Возвращает presigned-URL или None, если хранилище не настроено."""
    if not os.environ.get('S3_ENDPOINT_URL'):
        return None
    client = _get_client()
    bucket = os.environ['S3_BUCKET_DOCUMENTS']
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': storage_key},
        ExpiresIn=3600,
    )
