# Синхронизация KalkulatorRK2

## Быстрое исправление деплоя на Vercel

Если приложение не запускается после рефакторинга, примените патч **0002** поверх актуального `main`:

```bash
git clone https://github.com/KalkulatorRK/KalkulatorRK2.git
cd KalkulatorRK2
git checkout main
git pull origin main
git am /path/to/patches/kalkulatorrk2/0002-vercel-deploy-fix.patch
npm ci && npm run build && npm test
git push origin main
```

Vercel пересоберёт проект автоматически после push.

### Что исправляет патч 0002

- **`vercel.json`** — `outputDirectory: dist`, SPA rewrites
- **`HashRouter`** вместо `BrowserRouter` (как было до рефакторинга)
- **`npm run build`** — только `vite build` (без `tsc`, который мог ломать сборку на Vercel)
- Полный рефакторинг `lib/`, Tailwind в бандле, тесты

### Проверка локально

```bash
npm ci
npm run build
npx vite preview
```

Откройте http://localhost:4173

## Полный рефакторинг (патч 0001)

Устарел — не применять на текущий `main`. Используйте только **0002**.
