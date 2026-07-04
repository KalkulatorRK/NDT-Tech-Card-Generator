"""MCP-сервер «Карта-НК Gateway» — внешние интеграции проекта."""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from karta_nk_gateway.pravo import PravoClient, format_json

mcp = FastMCP(
    "karta-nk-gateway",
    instructions=(
        "Единый MCP для внешних операций проекта «Карта-НК»: "
        "поиск и скачивание НПА с publication.pravo.gov.ru и др."
    ),
)

_pravo: PravoClient | None = None


def _get_pravo() -> PravoClient:
    global _pravo
    if _pravo is None:
        _pravo = PravoClient()
    return _pravo


def _normative_docs_dir() -> Path:
    custom = os.environ.get("KARTA_NK_NORMATIVE_DOCS")
    if custom:
        return Path(custom).expanduser().resolve()
    # mcp_gateway/karta_nk_gateway/server.py → repo root → ndt_web/normative_docs
    return Path(__file__).resolve().parents[2] / "ndt_web" / "normative_docs"


@mcp.tool()
def pravo_search_documents(
    name: str | None = None,
    number: str | None = None,
    document_text: str | None = None,
    number_search_type: int = 1,
    jd_reg_number: str | None = None,
    publish_date_from: str | None = None,
    publish_date_to: str | None = None,
    page_size: int = 30,
    page: int = 1,
) -> str:
    """Поиск нормативно-правовых актов на publication.pravo.gov.ru.

    number_search_type: 0 — точное совпадение номера, 1 — содержит, 2 — начинается с.
    page_size: 10, 30, 100 или 200.
    Даты: YYYY-MM-DD.
    """
    client = _get_pravo()
    result = client.search_documents(
        name=name,
        number=number,
        document_text=document_text,
        number_search_type=number_search_type,
        jd_reg_number=jd_reg_number,
        publish_date_from=publish_date_from,
        publish_date_to=publish_date_to,
        page_size=page_size,
        page=page,
    )
    return format_json(result)


@mcp.tool()
def pravo_get_document(eo_number: str) -> str:
    """Метаданные одного НПА по номеру электронного опубликования (eoNumber)."""
    client = _get_pravo()
    return format_json(client.get_document(eo_number))


@mcp.tool()
def pravo_download_pdf(
    eo_number: str,
    filename: str | None = None,
) -> str:
    """Скачать PDF документа с pravo.gov.ru в ndt_web/normative_docs/."""
    client = _get_pravo()
    meta = client.get_document(eo_number)
    safe_name = filename or f"pravo_{eo_number}.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    safe_name = Path(safe_name).name
    destination = _normative_docs_dir() / safe_name
    result = client.download_pdf(eo_number, destination)
    result["title"] = meta.get("complexName")
    result["number"] = meta.get("number")
    return format_json(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
