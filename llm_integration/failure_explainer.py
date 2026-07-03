"""
Task 3 - Option A: Failure Explainer.

Why this option over Option B (Flaky Test Classifier):
The ticket is explicit that the problem is "spending too much time writing
and fixing regression tests" - i.e. time lost *right after* a failure,
reading a stack trace and a screenshot to figure out what happened before
you can even start fixing it. A flaky-test classifier is genuinely useful,
but it needs a history of runs before its real-bug/env/flaky buckets mean
anything - it pays off in week three. A failure explainer pays off on
failure #1, on a laptop, with no run history required. Given the stated
pain point, that's the one worth shipping first. (A flaky classifier is
listed as a "what I'd build next" item in the README.)

This makes a real, non-mocked call to a local Ollama model via Ollama's
REST API (http://localhost:11434 by default). It requires Ollama to be
installed and running locally, with the target model already pulled
(e.g. `ollama pull llama3.1`) - see .env.example and README.md "Running
the LLM integration" for setup.
"""
import os

import requests

# Ollama connection settings - overridable via environment/.env
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")

# How long to wait on the local model before giving up. Local inference on
# a laptop can be slow, especially on a cold start (model not yet loaded
# into memory), so this is generous by API-call standards on purpose.
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT", "60"))

SYSTEM_PROMPT = """You are a senior SDET pairing with a QA engineer on a failed \
automated test. You'll get the raw failure context: error message, traceback, \
and, where available, the page URL, visible page text (UI test), or the raw \
HTTP response (API test).

Reply in exactly this structure, plain text, no markdown headers, no repeating \
the full traceback back to me:

ROOT CAUSE: <one or two sentences, plain English>
LIKELY CATEGORY: <one of: Product Bug | Test Script Issue | Environment/Data Issue | Flaky/Timing>
SUGGESTED FIX: <one concrete, specific next step>

Be concise - three short lines, not an essay."""


def explain_failure(context: dict) -> str:
    """Send a failed test's context to a local Ollama model and return a
    plain-English root cause + suggested fix. Returns a clear placeholder
    string (not an exception) if Ollama isn't reachable or the model isn't
    pulled, so a local-LLM hiccup never breaks the test run itself - it
    just means that one run has no AI analysis."""
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": _format_context(context),
        "stream": False,
        # Keep this tight and deterministic-ish; this is triage text, not creative writing.
        "options": {"temperature": 0.2},
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.ConnectionError:
        return (
            f"_Skipped: couldn't reach Ollama at {OLLAMA_HOST}. Make sure "
            "Ollama is installed and running (`ollama serve`), or set "
            "OLLAMA_HOST in your environment/.env if it's running "
            "elsewhere. See .env.example._"
        )
    except requests.exceptions.Timeout:
        return (
            f"_Skipped: Ollama at {OLLAMA_HOST} didn't respond within "
            f"{REQUEST_TIMEOUT_SECONDS}s. The model may still be loading "
            "into memory on a cold start - try re-running, or raise "
            "OLLAMA_TIMEOUT in your environment/.env._"
        )

    if response.status_code == 404:
        return (
            f"_Skipped: model '{OLLAMA_MODEL}' isn't available on this "
            f"Ollama instance. Pull it first with `ollama pull "
            f"{OLLAMA_MODEL}`, or set OLLAMA_MODEL to a model you already "
            "have. See .env.example._"
        )
    if response.status_code != 200:
        return (
            f"_Skipped: Ollama returned an unexpected {response.status_code} "
            f"response ({response.text[:200]}). No live AI analysis ran "
            "for this failure._"
        )

    body = response.json()
    return body.get("response", "").strip()


def _format_context(context: dict) -> str:
    lines = [
        f"Test: {context.get('test_name', 'unknown')}",
        f"Error: {context.get('error', 'unknown')}",
    ]
    if context.get("traceback"):
        lines.append(f"Traceback:\n{context['traceback'][:2000]}")
    if context.get("url"):
        lines.append(f"Page URL at failure: {context['url']}")
    if context.get("page_text_snippet"):
        lines.append(f"Visible page text (truncated):\n{context['page_text_snippet']}")
    if context.get("api_context"):
        lines.append(f"API context:\n{context['api_context']}")
    return "\n\n".join(lines)