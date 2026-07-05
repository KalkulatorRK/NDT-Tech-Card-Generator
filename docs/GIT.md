# Git и ветки «Карта-НК»

## Основная ветка (деплой)

| Ветка | Назначение |
|-------|------------|
| **`cursor/ndt-webapp-54ed`** | Prod-код, autodeploy на Render |
| `cursor/<task>-8e9a` | Рабочие ветки Cloud Agent / PR |
| `main` | Не используется для деплоя |

## Правило коммитов

**Все готовые изменения заливаются в `cursor/ndt-webapp-54ed`.**

Типичный поток:

```
cursor/<feature>-8e9a  →  merge  →  cursor/ndt-webapp-54ed  →  Render deploy
```

Cloud Agent после задачи:
1. `git push` feature-ветки (если была)
2. merge в `cursor/ndt-webapp-54ed`
3. `git push origin cursor/ndt-webapp-54ed`

## Локально (Windows / Desktop)

Путь проекта, например:
`C:\Users\...\NDT-Tech-Card-Generator`

```powershell
git fetch origin
git checkout cursor/ndt-webapp-54ed
git pull origin cursor/ndt-webapp-54ed
```

IDE показывает **локальную** копию — без `git pull` код отстаёт от GitHub.

## MCP и prod

- `mcp_gateway/`, `.cursor/mcp.json` — только для Cursor локально, на Render не деплоятся.
- Секреты: `.env.mcp` (не в git), на Render — Dashboard → Environment.

## Связанные файлы

- [`.cursor/rules/git-main-branch.mdc`](../.cursor/rules/git-main-branch.mdc) — правило для агента Cursor
- [`docs/MCP.md`](MCP.md) — настройка MCP
