"""Клиент API publication.pravo.gov.ru (официальное опубликование НПА)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

PRAVO_BASE = "http://publication.pravo.gov.ru"
DEFAULT_TIMEOUT = 30.0
VALID_PAGE_SIZES = {10, 30, 100, 200}


def _normalize_page_size(page_size: int | None) -> int:
    if page_size in VALID_PAGE_SIZES:
        return page_size
    return 30


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).replace("\n", " ").strip()


def _summarize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "eoNumber": item.get("eoNumber"),
        "id": item.get("id"),
        "number": item.get("number"),
        "name": item.get("name"),
        "complexName": _strip_html(item.get("complexName")),
        "documentDate": item.get("documentDate"),
        "publishDateShort": item.get("publishDateShort"),
        "jdRegNumber": item.get("jdRegNumber"),
        "jdRegDate": item.get("jdRegDate"),
        "pagesCount": item.get("pagesCount"),
        "pdfFileLength": item.get("pdfFileLength"),
        "viewUrl": f"{PRAVO_BASE}/Document/View/{item.get('eoNumber')}" if item.get("eoNumber") else None,
        "pdfUrl": f"{PRAVO_BASE}/File/pdf/{item.get('eoNumber')}" if item.get("eoNumber") else None,
    }


class PravoClient:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "Karta-NK-MCP/1.0"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def search_documents(
        self,
        *,
        name: str | None = None,
        number: str | None = None,
        document_text: str | None = None,
        number_search_type: int = 1,
        jd_reg_number: str | None = None,
        publish_date_from: str | None = None,
        publish_date_to: str | None = None,
        document_date_from: str | None = None,
        document_date_to: str | None = None,
        page_size: int = 30,
        page: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "NumberSearchType": number_search_type,
            "PageSize": _normalize_page_size(page_size),
            "Index": max(page, 1),
        }
        if name:
            params["Name"] = name
        if number:
            params["Number"] = number
        if document_text:
            params["DocumentText"] = document_text
        if jd_reg_number:
            params["JdRegNumber"] = jd_reg_number
        if publish_date_from:
            params["PublishDateFrom"] = publish_date_from
        if publish_date_to:
            params["PublishDateTo"] = publish_date_to
        if document_date_from:
            params["DocumentDateFrom"] = document_date_from
        if document_date_to:
            params["DocumentDateTo"] = document_date_to

        if not any(k in params for k in ("Name", "Number", "DocumentText", "JdRegNumber")):
            raise ValueError(
                "Укажите хотя бы один критерий поиска: name, number, document_text или jd_reg_number."
            )

        response = self._client.get(f"{PRAVO_BASE}/api/Documents", params=params)
        response.raise_for_status()
        data = response.json()

        items = [_summarize_item(item) for item in data.get("items", [])]
        return {
            "items": items,
            "itemsTotalCount": data.get("itemsTotalCount", 0),
            "currentPage": data.get("currentPage", page),
            "pagesTotalCount": data.get("pagesTotalCount", 0),
            "itemsPerPage": data.get("itemsPerPage", params["PageSize"]),
            "query": params,
        }

    def get_document(self, eo_number: str) -> dict[str, Any]:
        response = self._client.get(
            f"{PRAVO_BASE}/api/Document",
            params={"eoNumber": eo_number},
        )
        response.raise_for_status()
        data = response.json()
        summary = _summarize_item(data)
        summary["signatoryAuthorities"] = [
            auth.get("name") for auth in data.get("signatoryAuthorities", [])
        ]
        summary["documentType"] = (data.get("documentType") or {}).get("name")
        return summary

    def download_pdf(self, eo_number: str, destination: Path) -> dict[str, Any]:
        url = f"{PRAVO_BASE}/File/pdf/{eo_number}"
        response = self._client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
            raise ValueError(
                f"Ответ не похож на PDF (content-type: {content_type}). "
                f"Проверьте eoNumber или откройте {url} в браузере."
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return {
            "eoNumber": eo_number,
            "savedTo": str(destination),
            "sizeBytes": len(response.content),
            "pdfUrl": url,
        }


def format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
