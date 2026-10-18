# Deploying SwarmFolio Referee

The public deployment has two parts:

| Part | Where | What it runs |
|---|---|---|
| API | Render (Docker, free plan) | `api.py` + `referee/` only: saved demo runs, the live Referee (`POST /api/referee`) and rule price tags (`GET /api/prices/{id}`) |
| Web app | Vercel | the React app in `frontend/`, built with `VITE_API_URL` pointing at the API |

**No LLM calls and no API keys.** The Docker image installs only `requirements-api.txt` (solver + FastAPI) and copies only `api.py`, `config.py`, `models.py`, `referee/`, `data/` and `eval/results/experiment.json` (see `.dockerignore`). LangChain, the agents, the committee loop, Stripe and `.env` are not in the image, so the public site can't spend LLM quota even by accident. `tests/test_public_api.py` checks this.

The five Fetch agents are not part of this deployment; keep running them with `nohup python -m agents.run_all &` (README, "How to run").

## 0. Check the image locally (optional, ~5 min)

```bash
docker build -t swarmfolio-api .
docker run --rm -p 8000:8000 swarmfolio-api
curl localhost:8000/api/clients          # list of clients
curl localhost:8000/api/prices/C04       # price tags, solved live by SCIP
```

The build fails on purpose if CVXPY can't see the SCIP solver.

## 1. API on Render

1. Push this branch to `main` (Render deploys from GitHub).
2. Go to <https://dashboard.render.com> → **New** → **Blueprint**.
3. Connect GitHub if asked, pick `SwarmFolio-Labs/SwarmFolio---Referee`, branch `main`.
4. Render reads `render.yaml` and shows one web service, `swarmfolio-api` (Docker, free plan). Click **Apply** / **Deploy Blueprint**. No environment variables are needed.
5. Wait for the first build (several minutes: the image installs CVXPY + SCIP). Render marks it live once `/api/clients` answers (the health check).
6. Copy the service URL from the top of the service page, e.g. `https://swarmfolio-api.onrender.com` (Render adds a suffix if the name is taken). Check:
   - `https://<your-api>.onrender.com/api/clients`
   - `https://<your-api>.onrender.com/api/demo/C02`
   - `https://<your-api>.onrender.com/docs` (interactive API docs)

Free Render services go to sleep when idle, and the first request after that takes about a minute while it wakes up. Open the API URL a minute before you demo, or switch the service to a paid instance in **Settings → Instance Type**.

## 2. Web app on Vercel

1. Go to <https://vercel.com/new> and import `SwarmFolio-Labs/SwarmFolio---Referee`.
2. **Root Directory:** click **Edit** and choose `frontend`. Vercel picks up `frontend/vercel.json` (Vite, `npm ci`, `npm run build`, output `dist`).
3. **Environment Variables:** add `VITE_API_URL` = your Render URL from step 1, e.g. `https://swarmfolio-api.onrender.com` (no `/api` at the end; the app adds it).
4. Click **Deploy**. Open the `*.vercel.app` URL: the client list should load, and a run page should show the receipt and price tags.

`VITE_API_URL` is baked in at build time. If you change it later, redeploy (**Deployments** → **⋯** → **Redeploy**).

The app uses hash URLs (`/#/run/C02`), so Vercel needs no rewrite rules. The API already allows requests from any origin (CORS), so no CORS setup is needed either.

## 3. Point swarmfolio.biz at it

1. In Vercel: project → **Settings** → **Domains** → add `swarmfolio.biz`. When Vercel offers it, also add `www.swarmfolio.biz` redirecting to `swarmfolio.biz`.
2. Vercel then shows the DNS records to create. At the registrar where you bought `swarmfolio.biz`, open its DNS settings and:
   - delete any existing `A`/`AAAA`/`CNAME` records for `@` and `www` (often a registrar "parking" page);
   - add the `A` record for `@` with the IP Vercel shows;
   - add the `CNAME` record for `www` with the value Vercel shows.

   Use the exact values from the Vercel screen; they can differ per project. (Alternative: switch the domain's nameservers to the ones Vercel lists, and Vercel manages all DNS.)
3. Wait until Vercel shows **Valid Configuration** (minutes, sometimes up to a few hours). Vercel issues the HTTPS certificate automatically.

### Optional: api.swarmfolio.biz for the API

1. Render: service → **Settings** → **Custom Domains** → add `api.swarmfolio.biz`.
2. At the registrar: `CNAME` `api` → your `*.onrender.com` host (Render shows the exact value). Wait for Render to verify it and issue the certificate.
3. Vercel: change `VITE_API_URL` to `https://api.swarmfolio.biz` and redeploy.

## 4. Forward aisaidtrustmebro.biz to swarmfolio.biz

Easiest with HTTPS included, through Vercel:

1. Vercel project → **Settings** → **Domains** → add `aisaidtrustmebro.biz` (and `www.aisaidtrustmebro.biz`).
2. For each one, choose **Redirect to** `swarmfolio.biz` (permanent, 308) instead of serving the project.
3. At that domain's registrar, add the `A` (`@`) and `CNAME` (`www`) records Vercel shows, exactly as in step 3.

Alternative: many registrars offer "URL forwarding" (301) to `https://swarmfolio.biz` with no DNS records to add. Check that it also works for `https://aisaidtrustmebro.biz`; some registrars only forward plain `http://`.

## 5. Final check

- [ ] `https://swarmfolio.biz` loads the client list.
- [ ] A run page (e.g. Dr. Patel, C02) shows the saved committee run, the receipt and the price tags.
- [ ] "Check a portfolio" on the web app returns a live verdict.
- [ ] `https://aisaidtrustmebro.biz` lands on `https://swarmfolio.biz`.
- [ ] The API URL wakes up in time if it's on the free plan.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Web app loads but shows "Failed to fetch" / no clients | `VITE_API_URL` missing or wrong, or the API is asleep. Open the API URL directly, fix the variable, redeploy on Vercel. |
| Render build fails while installing packages | Check the build log; the image pins Python 3.12 (`python:3.12-slim`), for which CVXPY and PySCIPOpt ship prebuilt wheels. |
| Render deploy times out on the health check | Open `/api/clients` from the service's **Logs** tab; the API must listen on `$PORT` (the Dockerfile already does). |
| Domain stuck on "Invalid Configuration" | An old parking record is still there, or DNS hasn't propagated yet. Compare the records with what Vercel shows. |
