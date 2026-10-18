"""
All the switches and constants for SwarmFolio Referee (MASTER 4.2).

Everything that might change between runs lives here, so nobody has to hunt
through the code for a magic number. API keys are NOT here: they come from .env.
"""

import os

from dotenv import load_dotenv

# Load keys and agent seeds from .env (if it exists). Never print them.
load_dotenv()

# --- Wiring switches ---
# True = app and agents use the fake brains in fakes.py (so Devin can build without the real math).
USE_FAKES = False
# False = the Chair's loop calls the brains directly (LocalTransport); True = over Fetch agents.
USE_AGENT_NETWORK = False

# --- LLM settings ---
# Which LLM the analysts and Chair use: "asi1" (default), "gemini" or "anthropic".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "asi1")

# Model ids per provider. Only this file names models.
MODELS = {
    "asi1": {"chair": "asi1", "analyst": "asi1"},
    "anthropic": {"chair": "claude-sonnet-5-5", "analyst": "claude-haiku-5-5"},
    # Gemini model ids get set at the event (check what the free key allows).
    "gemini": {"chair": "gemini-2.5-flash", "analyst": "gemini-2.5-flash"},
}
CHAIR_MODEL = MODELS[LLM_PROVIDER]["chair"]
ANALYST_MODEL = MODELS[LLM_PROVIDER]["analyst"]

# ASI:One's OpenAI-compatible endpoint (from Fetch's docs).
ASI1_BASE_URL = "https://api.asi1.ai/v1"

# --- Agents ---
# One local port per Fetch agent.
AGENT_PORTS = {
    "chair": 8001,
    "referee": 8002,
    "macro": 8003,
    "fundamentals": 8004,
    "risk": 8005,
}
AGENT_TIMEOUT_S = 45  # how long to wait for another agent's reply
AGENT_RETRIES = 1     # retry once, then fall back

# --- Referee math (MASTER 6.2) ---
DUST = 0.005       # weights below 0.5% count as "not held"
TOL = 1e-6         # tolerance for "rule passed"
VOL_MARGIN = 1e-5  # the solver aims this far under a volatility cap (0.001 points) to absorb rounding
RISK_FREE = 0.04   # risk-free rate for Sharpe
LOOKBACK_DAYS = 756  # ~3 years of trading days for returns and risk

# --- Committee ---
MAX_ROUNDS = 3  # debate rounds before giving up and letting the Referee repair
