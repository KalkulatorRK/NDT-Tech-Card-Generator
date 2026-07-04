# MCP для «Карта-НК»

Настройка [Model Context Protocol](https://cursor.com/docs/mcp) в Cursor: ассистент получает доступ к GitHub, базе Neon и нормативным документам проекта.

> ЮKassa в MCP **не подключена** (по решению команды).

## Что подключено

| Сервер | Назначение |
|--------|------------|
| `github` | Issues, PR, коммиты, diff репозитория |
| `neon-postgres` | SQL-запросы к PostgreSQL (Neon) |
| `normative-docs` | Чтение файлов в `ndt_web/normative_docs/` |
| `karta-nk-project` | Чтение/запись файлов Django-приложения `ndt_web/` |

Конфигурация: [`.cursor/mcp.json`](../.cursor/mcp.json) (коммитится в git, **без секретов**).

---

## Быстрый старт (5–10 минут)

### 1. Node.js

Нужен **Node.js 18+** (для `npx`). Проверка:

```bash
node -v
npx -v
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
2. Должны быть серверы: `github`, `neon-postgres`, `normative-docs`, `karta-nk-project`
3. Статус — зелёный / Connected
4. При ошибках: **Output → MCP Logs**

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

Отредактируйте `.cursor/mcp.json`. Идеи:

- **Brave Search** — `@modelcontextprotocol/server-brave-search` + `BRAVE_API_KEY`
- **Memory** — `@modelcontextprotocol/server-memory` (заметки между сессиями)
- **ЮKassa** — свой MCP поверх API (когда понадобится)

После правок — перезапуск Cursor.

---

## Файлы

```
.cursor/mcp.json      ← конфиг MCP (в git)
.env.mcp.example      ← шаблон секретов (в git)
.env.mcp              ← ваши секреты (НЕ в git)
docs/MCP.md           ← эта инструкция
```
