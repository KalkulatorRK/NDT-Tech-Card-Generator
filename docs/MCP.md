# MCP для «Карта-НК»

Настройка [Model Context Protocol](https://cursor.com/docs/mcp) в Cursor: ассистент получает доступ к GitHub, базе Neon, нормативным документам и **API pravo.gov.ru**.

> ЮKassa в MCP **не подключена** (по решению команды).

## Что подключено

| Сервер | Назначение |
|--------|------------|
| **`karta-nk-gateway`** | **Единый gateway:** pravo.gov.ru (поиск/скачивание НПА), далее — деплой, БД, gost.ru |
| `github` | Issues, PR, коммиты, diff репозитория |
| `neon-postgres` | SQL-запросы к PostgreSQL (Neon) |
| `normative-docs` | Чтение файлов в `ndt_web/normative_docs/` |
| `karta-nk-project` | Чтение/запись файлов Django-приложения `ndt_web/` |

Конфигурация: [`.cursor/mcp.json`](../.cursor/mcp.json) (коммитится в git, **без секретов**).

---

## Быстрый старт (5–10 минут)

### 1. Python и Node.js

- **Python 3.10+** — для `karta-nk-gateway`
- **Node.js 18+** — для остальных MCP (`npx`)

```bash
python3 -V
node -v
```

Установка зависимостей gateway:

```bash
pip install -r mcp_gateway/requirements.txt
```

### 2. Переменные окружения

Скопируйте шаблон и заполните значения **локально** (не коммитьте):

```bash
cp .env.mcp.example .env.mcp
```

Загрузите переменные в shell (macOS/Linux):

```bash
set -a && source .env.mcp && set +a
```

Windows PowerShell:

```powershell
Get-Content .env.mcp | ForEach-Object {
  if ($_ -match '^([^#=]+)=(.*)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2] }
}
```

**Важно:** Cursor читает `${env:...}` при **запуске**. После изменения `.env.mcp` полностью **перезапустите Cursor**.

### 3. Проверка в Cursor

1. **Cursor Settings → Tools & MCP**
2. Должны быть серверы: `karta-nk-gateway`, `github`, `neon-postgres`, `normative-docs`, `karta-nk-project`
3. Статус — зелёный / Connected
4. При ошибках: **Output → MCP Logs**

---

## pravo.gov.ru (`karta-nk-gateway`)

Официальный портал правовой информации: приказы Ростехнадзора (НП-038, НП-105 и др.), постановления, PDF.

**API:** `http://publication.pravo.gov.ru` — бесплатный, только чтение, ключ не нужен.

### Инструменты MCP

| Tool | Описание |
|------|----------|
| `pravo_search_documents` | Поиск НПА по названию, номеру, тексту |
| `pravo_get_document` | Метаданные документа по `eoNumber` |
| `pravo_download_pdf` | Скачать PDF в `ndt_web/normative_docs/` |

### Примеры запросов ассистенту

- «Найди на pravo.gov.ru приказы Ростехнадзора с номером 105»
- «Скачай PDF документа с eoNumber 7001202606190004 в normative_docs»
- «Покажи метаданные НП-038-16 на pravo.gov.ru»

### Параметры поиска

- `name` — фрагмент наименования (например, «Ростехнадзор», «НП-105»)
- `number` — номер документа (например, «105»)
- `document_text` — поиск по тексту документа
- `number_search_type`: `0` — точное совпадение, `1` — содержит (по умолчанию), `2` — начинается с
- `page_size`: 10, 30, 100 или 200

PDF скачивается по URL вида `http://publication.pravo.gov.ru/File/pdf/{eoNumber}`.

### Ограничения

- На pravo.gov.ru публикуются **НПА** (приказы, постановления). **ГОСТ** — на gost.ru (отдельный источник, в gateway позже).
- Не все документы имеют PDF; при ошибке проверьте `eoNumber` через `pravo_get_document`.

---

## GitHub (`github`)

### Токен

1. GitHub → **Settings → Developer settings → Personal access tokens**
2. **Fine-grained token** (рекомендуется) или Classic
3. Репозиторий: `KalkulatorRK/NDT-Tech-Card-Generator`
4. Права (минимум):
   - Contents: Read
   - Issues: Read and write
   - Pull requests: Read and write
   - Metadata: Read

```bash
export GITHUB_TOKEN=github_pat_xxxxxxxx
```

### Примеры запросов ассистенту

- «Покажи открытые PR в репозитории»
- «Создай issue: баг в форме регистрации»
- «Какие коммиты были за последнюю неделю?»

---

## Neon PostgreSQL (`neon-postgres`)

### Какой URL использовать

| URL | Где |
|-----|-----|
| **Direct** | MCP, `pg_dump`, миграции |
| **Pooled** (`-pooler` в хосте) | Django на Render |

Для MCP укажите **Direct connection string** из Neon Console:

```
postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

```bash
export NEON_MCP_DATABASE_URL='postgresql://...?sslmode=require'
```

### Безопасность

- MCP-сервер Postgres выполняет **произвольный SQL** — не давайте prod-токен посторонним
- Для осторожности создайте в Neon **read-only** роль (опционально)
- **Не** используйте MCP для `DROP` / массового `DELETE` на production

### Примеры запросов

- «Сколько пользователей в `accounts_customuser`?»
- «Покажи схему таблицы techcards»
- «Есть ли неприменённые миграции в `django_migrations`?»

---

## Нормативные документы (`normative-docs`)

Доступ только к каталогу `ndt_web/normative_docs/`:

- ГОСТ, НП, методики РИД-Se4P
- программы управления ресурсом
- без выхода за пределы папки

### Примеры

- «Найди в normative_docs требования п. 100_6 НП-038-16»
- «Какие DOCX лежат в normative_docs?»

---

## Код проекта (`karta-nk-project`)

Доступ к `ndt_web/` — Django-приложение, шаблоны, генераторы.

> Cursor и так видит файлы репозитория; MCP filesystem полезен для **явных** операций чтения/записи через инструменты MCP.

---

## Что не входит

| Сервис | Почему |
|--------|--------|
| **ЮKassa** | не подключена по запросу |
| **Render** | нет официального MCP; логи — через Dashboard |
| **Почта (Resend/Unisender)** | секреты только на Render |

---

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| Сервер красный в MCP | `Output → MCP Logs`; проверьте Node/npx |
| `GITHUB_TOKEN` не подхватывается | экспорт в shell **до** запуска Cursor или перезапуск |
| Postgres: SSL error | добавьте `?sslmode=require` |
| Postgres: connection failed | Direct URL, не Pooled; Neon не suspended |
| `npx` долго стартует | первый запуск качает пакет — подождите 30–60 сек |

---

## Добавление серверов позже

`karta-nk-gateway` расширяется новыми модулями (Neon SQL, Render deploy, gost.ru). По мере готовности отдельные MCP (`github`, `neon-postgres`, …) можно убрать из `.cursor/mcp.json`.

Дополнительно:

- **Brave Search** — `@modelcontextprotocol/server-brave-search` + `BRAVE_API_KEY`
- **Memory** — `@modelcontextprotocol/server-memory` (заметки между сессиями)
- **ЮKassa** — свой MCP поверх API (когда понадобится)

После правок — перезапуск Cursor.

---

## Файлы

```
.cursor/mcp.json              ← конфиг MCP (в git)
.env.mcp.example              ← шаблон секретов (в git)
.env.mcp                      ← ваши секреты (НЕ в git)
docs/MCP.md                   ← эта инструкция
mcp_gateway/                  ← единый MCP-gateway (Python)
  requirements.txt
  karta_nk_gateway/
    server.py                 ← точка входа MCP
    pravo.py                  ← клиент publication.pravo.gov.ru
```
