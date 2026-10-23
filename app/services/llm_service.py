import json
import os
import re

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("TARA_LLM_MODEL", "qwen3:4b")

# Hosted mode: if GROQ_API_KEY is set (e.g. on Hugging Face Spaces) use Groq's OpenAI-compatible API instead of Ollama.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("TARA_GROQ_MODEL", "llama-3.3-70b-versatile")


def _call_groq(prompt: str, schema: dict | None) -> str:
    if schema:
        prompt += "\n\nReply with ONLY valid JSON matching this JSON schema:\n" + json.dumps(schema)
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 42,
    }
    if schema:
        payload["response_format"] = {"type": "json_object"}
    response = requests.post(
        GROQ_URL, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=120
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_llm(prompt: str, schema: dict | None = None) -> str:
    """schema: JSON schema passed to Ollama as `format`. Constrained decoding guarantees valid JSON and stops
    the qwen3 model from emitting a long reasoning trace instead of the answer."""
    if GROQ_API_KEY:
        return _call_groq(prompt, schema)
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "seed": 42},  # reproducible outputs for evaluation
        }
        if schema:
            payload["format"] = schema
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data.get("response") or data.get("thinking", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure Ollama is installed and running, "
            f"and that you've pulled the model with: ollama pull {MODEL_NAME}"
        )


def extract_json(text: str):
    """Guardrail: pull valid JSON out of the LLM's reply. Returns None if the LLM didn't give valid JSON,
    instead of guessing or crashing."""
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
