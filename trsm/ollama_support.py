"""Safe, local-only Ollama availability checks and lazy client creation."""

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


def ollama_host():
    return os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")


def think_kwargs():
    """``TRSM_LLM_THINK=false`` turns off thinking for models such as qwen3.5.

    Thinking models otherwise spend most of a slow CPU server's time on hidden
    reasoning or return empty content. Unset keeps the previous behaviour.
    """
    value = os.getenv("TRSM_LLM_THINK", "").strip().lower()
    if value in {"0", "false", "no", "hayir"}:
        return {"think": False}
    return {}


def get_ollama_client(timeout=None):
    """Return a configured client or ``None`` when its Python package is absent."""
    if timeout is None:
        timeout = float(os.getenv("TRSM_OLLAMA_TIMEOUT", "60"))
    try:
        from ollama import Client
    except ImportError:
        return None
    try:
        return Client(host=ollama_host(), timeout=timeout)
    except TypeError:
        # Older client versions do not accept a timeout keyword. They remain
        # usable; the interface will still keep the feature optional.
        return Client(host=ollama_host())


def qwen_status(model_name, timeout=2):
    """Check the local Ollama tag endpoint without delaying the main analysis."""
    try:
        with urlopen(f"{ollama_host()}/api/tags", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError):
        return {"kullanilabilir": False, "model_yuklu": False}
    model_names = {row.get("name") for row in payload.get("models", [])}
    return {
        "kullanilabilir": True,
        "model_yuklu": model_name in model_names,
    }
