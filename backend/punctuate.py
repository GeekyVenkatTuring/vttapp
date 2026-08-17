"""Punctuation + capitalization restorer (ONNX, no LLM).

Restores punctuation, capitalization (true-casing) and sentence boundaries on a
raw Whisper transcript using a token-classification model
(`1-800-BAD-CODE/xlm-roberta_punctuation_fullstop_truecase`) run via
`punctuators` on onnxruntime.

Why a token model rather than an LLM: it labels each *existing* word with a
punctuation/case tag — it can never add, drop, paraphrase or "answer" the text.
So it cannot lose context the way a small generative LLM does on long run-on
transcripts. It is also fast (~0.5s) and needs no extra server. (This replaced
an earlier Gemma 3 1B / Ollama formatter that dropped content on long input.)

Graceful degradation: if the package/model is unavailable or inference fails,
the original transcript is returned unchanged.
"""

import os
import re

# Set VTT_FORMAT=0 to disable all formatting (shared with formatter.py).
FORMAT_ENABLED = os.environ.get("VTT_FORMAT", "1") != "0"
PUNCT_MODEL = os.environ.get(
    "VTT_PUNCT_MODEL", "1-800-BAD-CODE/xlm-roberta_punctuation_fullstop_truecase"
)
# Pathologically long input is skipped (the model is robust, but bound it).
_MAX_CHARS = 20000

_model = None
_load_failed = False

# Keep word characters, whitespace and intra-word apostrophes; drop everything
# else so the model restores punctuation from a clean, lowercase slate. This
# also avoids double-punctuation artifacts when Whisper already added some.
_NORMALIZE_RE = re.compile(r"[^\w\s']")


def _get_model():
    """Lazy-load the ONNX model once. Returns None if it can't be loaded."""
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    try:
        from punctuators.models import PunctCapSegModelONNX
        _model = PunctCapSegModelONNX.from_pretrained(PUNCT_MODEL)
    except Exception:
        # Package missing, download failed, etc. — degrade to raw transcript.
        _load_failed = True
        _model = None
    return _model


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", text).strip().lower()


def is_available() -> bool:
    return _get_model() is not None


def restore(text: str) -> str:
    """Return *text* with punctuation/capitalization restored.

    Falls back to the original text if formatting is disabled, the model is
    unavailable, or anything goes wrong. Never drops words.
    """
    text = (text or "").strip()
    if not text or not FORMAT_ENABLED or len(text) > _MAX_CHARS:
        return text

    model = _get_model()
    if model is None:
        return text

    cleaned = _normalize(text)
    if not cleaned:
        return text

    try:
        results = model.infer([cleaned])
        sentences = results[0] if results else []
        out = " ".join(s.strip() for s in sentences if s and s.strip()).strip()
    except Exception:
        return text

    # Safety net: a punctuation model must keep every word. If the word count
    # drifts (it shouldn't), keep the original transcript.
    if not out or abs(len(out.split()) - len(cleaned.split())) > 2:
        return text
    return out
