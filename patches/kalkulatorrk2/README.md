# Синхронизация KalkulatorRK2

Патч рефакторинга калькулятора (коммит `ae50203`):

```bash
git clone https://github.com/KalkulatorRK/KalkulatorRK2.git
cd KalkulatorRK2
git checkout main
git am /path/to/patches/kalkulatorrk2/0001-lib-Tailwind-CI-UX.patch
git push origin main
```

Или из репозитория Карта-НК:

```bash
git am patches/kalkulatorrk2/0001-lib-Tailwind-CI-UX.patch
```

Проверка после применения:

```bash
npm ci && npm run build && npm test
```
