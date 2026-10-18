# The public API: saved demo runs + the live Referee and rule price tags (pure math, no LLM calls,
# no API keys). Build and run locally:
#   docker build -t swarmfolio-api .
#   docker run --rm -p 8000:8000 swarmfolio-api      # then open http://localhost:8000/api/clients
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENABLE_LIVE_RUNS=false

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt \
    && python -c "import cvxpy; assert 'SCIP' in cvxpy.installed_solvers(), cvxpy.installed_solvers()"

# Only the files the API reads (see .dockerignore): no committee/, agents/ or LLM code in the image.
COPY api.py config.py models.py ./
COPY referee/ referee/
COPY data/ data/
COPY eval/results/experiment.json eval/results/experiment.json

RUN useradd --create-home app
USER app

EXPOSE 8000
# Render (and most hosts) tell the app which port to use with $PORT.
CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
