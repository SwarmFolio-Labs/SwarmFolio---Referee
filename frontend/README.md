# SwarmFolio Referee — web app

React + Vite + Tailwind front end for the judges. It talks to `api.py` (FastAPI) at the repo root.

## Run locally

```bash
# 1) API (from the repo root, inside .venv)
uvicorn api:app --reload --port 8000

# 2) Front end (from frontend/)
npm install
npm run dev          # http://localhost:5173  (proxies /api -> :8000)
```

`npm run build` writes a static build to `dist/` (hash routing, so any static host works).

## Where things live

- Styles: `src/index.css` (CSS variables = the whole palette/type/radius) + `tailwind.config.js` (maps them to classes). Restyle here.
- Pages: `src/pages/` (client picker, client run view, experiment). Building blocks: `src/components/`.
- Committee runs are replayed from `data/demo_runs/<id>.json`; regenerate with `python data/demo_runs/save_demo_run.py C02 C91` (needs `ASI1_API_KEY`) or `--fakes` for a dev run.
