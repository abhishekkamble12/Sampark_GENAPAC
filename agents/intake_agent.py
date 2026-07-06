"""
agents/intake_agent.py — Intake Agent for the Sampark AI Platform.

Parses multi-modal citizen input (text / audio / image) into a structured
IssueObject.  External dependencies (SpeechTool, VisionTool, Gemini model)
are injected via ``make_intake_node`` so that unit tests can supply mocks
without real API calls.

Logic (per design.md §4.1):
1. Detect input modality from ``state["query"]`` content / prefixes.
2. For audio: call ``SpeechTool.transcribe()`` → text.
3. For image: call ``VisionTool.caption_image()`` → text + Cloud Storage URI.
4. Run language detection; if non-English, translate via Gemini.
5. Call Gemini extraction prompt → ``{type, location, description}``.
6. Classify ``type`` into 8 canonical categories (default ``"other"``).
7. Validate location; set ``extraction_error`` if absent.

SLA enforcement (``asyncio.timeout``):
- Text: ≤5 s
- Audio: ≤15 s
- Image: ≤10 s
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Callable, Coroutine

from agents.state import KNOWN_ISSUE_TYPES, GraphState, IssueObject

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUDIO_PREFIX = "audio:"
_IMAGE_PREFIX = "image:"

_LANG_DETECT_PROMPT = """\
You are a language identification assistant.
Given the following text, respond with a JSON object in this exact format:
{{"language": "<BCP-47 language code>", "is_english": <true|false>, "translated_text": "<English translation or empty string if already English>"}}

Rules:
- "language" must be a valid BCP-47 code (e.g. "en", "hi", "ta", "te").
- "is_english" is true only when the source text is already English.
- "translated_text" must be the English translation when is_english is false; otherwise leave it as an empty string.
- If the language cannot be determined or is unsupported, set "language" to "unknown" and "is_english" to false.

Text:
{text}
"""

_EXTRACT_PROMPT = """\
You are an expert at extracting structured information from citizen issue reports.
Extract the following fields from the report and respond with a JSON object:
{{"type": "<issue category>", "location": "<location string or null>", "description": "<concise description>"}}

Rules:
- "type" should be a short label for the kind of community issue.
- "location" should be the specific location mentioned, or null if no location is present.
- "description" should be a concise one-or-two-sentence summary.

Report:
{text}
"""

_SLA_TEXT_SECONDS = 5
_SLA_AUDIO_SECONDS = 15
_SLA_IMAGE_SECONDS = 10

# ---------------------------------------------------------------------------
# Type alias for the Gemini model (duck-typed)
# ---------------------------------------------------------------------------

# The model must expose:  model.generate_content(prompt: str) -> response
# where response.text gives the string result.

# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def make_intake_node(
    speech_tool: Any,
    vision_tool: Any,
    gemini_model: Any,
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async ``intake_node`` function with the given dependencies injected.

    Args:
        speech_tool:   Instance with ``async transcribe(audio_bytes) -> str | None``.
        vision_tool:   Instance with ``async caption_image(image_bytes) -> str | None``.
        gemini_model:  Gemini model instance (``google.generativeai.GenerativeModel``).
                       Must expose ``generate_content(prompt: str)``.

    Returns:
        An async callable ``intake_node(state) -> state`` suitable for
        LangGraph node registration.
    """

    async def intake_node(state: GraphState) -> GraphState:  # noqa: C901
        """LangGraph node: parse multi-modal input into a structured IssueObject."""
        query: str = state.get("query", "")

        # ------------------------------------------------------------------
        # 1. Modality detection
        # ------------------------------------------------------------------
        modality = _detect_modality(query, state.get("user", {}))

        # ------------------------------------------------------------------
        # 2–3. Modality-specific processing with SLA enforcement
        # ------------------------------------------------------------------
        text: str = ""
        media_ref: str | None = None
        sla_seconds: int

        if modality == "audio":
            sla_seconds = _SLA_AUDIO_SECONDS
            try:
                async with asyncio.timeout(sla_seconds):
                    audio_bytes = _extract_bytes(query, _AUDIO_PREFIX)
                    transcript = await speech_tool.transcribe(audio_bytes)
            except TimeoutError:
                logger.warning("intake_node audio SLA exceeded (%ds)", sla_seconds)
                state["intake_error"] = "timeout"
                return state
            except Exception:
                logger.exception("intake_node audio transcription error")
                state["intake_error"] = "audio_unprocessable"
                return state

            if transcript is None:
                state["intake_error"] = "audio_unprocessable"
                return state
            text = transcript

        elif modality == "image":
            sla_seconds = _SLA_IMAGE_SECONDS
            try:
                async with asyncio.timeout(sla_seconds):
                    image_bytes = _extract_bytes(query, _IMAGE_PREFIX)
                    caption = await vision_tool.caption_image(image_bytes)
            except TimeoutError:
                logger.warning("intake_node image SLA exceeded (%ds)", sla_seconds)
                state["intake_error"] = "timeout"
                return state
            except Exception:
                logger.exception("intake_node image captioning error")
                state["intake_error"] = "image_unclassifiable"
                return state

            if caption is None:
                state["intake_error"] = "image_unclassifiable"
                return state

            text = caption
            # Store the Cloud Storage URI from query metadata if present
            media_ref = _extract_media_ref(query, state.get("user", {}))

        else:
            # Plain text — no modality-specific tool calls needed
            sla_seconds = _SLA_TEXT_SECONDS
            text = query

        # ------------------------------------------------------------------
        # 4–7. Language detection / translation + extraction + classification
        #       All within the text SLA (already inside modality SLA for
        #       audio/image; for text we wrap the full remainder).
        # ------------------------------------------------------------------
        try:
            async with asyncio.timeout(_SLA_TEXT_SECONDS if modality == "text" else sla_seconds):
                # ---- 4. Language detection & translation -----------------
                original_language: str | None = None
                translated_text = text

                lang_result = await _run_gemini(
                    gemini_model,
                    _LANG_DETECT_PROMPT.format(text=text),
                )
                lang_data = _parse_json(lang_result)

                if lang_data is not None:
                    lang_code: str = lang_data.get("language", "unknown")
                    is_english: bool = bool(lang_data.get("is_english", True))
                    translation: str = lang_data.get("translated_text", "")

                    if lang_code == "unknown":
                        state["translation_error"] = True
                        # Still attempt extraction on original text
                    elif not is_english:
                        original_language = lang_code
                        if translation:
                            translated_text = translation
                        else:
                            state["translation_error"] = True
                else:
                    # Gemini returned non-parseable response; treat as English
                    pass

                # ---- 5. Entity extraction --------------------------------
                extract_result = await _run_gemini(
                    gemini_model,
                    _EXTRACT_PROMPT.format(text=translated_text),
                )
                extract_data = _parse_json(extract_result)

                raw_type = "other"
                location: dict | None = None
                description = translated_text

                if extract_data is not None:
                    raw_type = str(extract_data.get("type", "other"))
                    loc_str = extract_data.get("location")
                    description = str(extract_data.get("description", translated_text))

                    if loc_str:
                        location = {"address": loc_str}
                    else:
                        state["extraction_error"] = True
                        location = None
                else:
                    state["extraction_error"] = True

                # ---- 6. Type classification ------------------------------
                canonical_type = _classify_type(raw_type)

                # ---- 7. Build IssueObject --------------------------------
                media_refs: list[str] = []
                if media_ref:
                    media_refs.append(media_ref)

                existing_issue = state.get("issue") or {}
                issue_id_to_use = existing_issue.get("id") or f"iss_{uuid.uuid4().hex[:8]}"

                # Merge existing location (lat, lng, ward_id) with newly extracted address
                merged_location = {}
                existing_loc = existing_issue.get("location")
                if isinstance(existing_loc, dict):
                    merged_location.update(existing_loc)
                if location and isinstance(location, dict):
                    merged_location["address"] = location.get("address") or merged_location.get("address")

                issue: IssueObject = {
                    "id": issue_id_to_use,
                    "type": canonical_type,
                    "location": merged_location,
                    "description": description,
                    "media_refs": media_refs,
                    "original_language": original_language,
                    "severity": None,
                }
                state["issue"] = issue


        except TimeoutError:
            logger.warning("intake_node text-processing SLA exceeded (%ds)", _SLA_TEXT_SECONDS)
            state["intake_error"] = "timeout"

        return state

    return intake_node


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_modality(query: str, user: dict) -> str:  # noqa: ARG001
    """Return ``"audio"``, ``"image"``, or ``"text"`` based on query prefix.

    Priority:
    1. Explicit ``audio:`` / ``image:`` prefix on the query string.
    2. ``user["modality"]`` metadata field.
    3. Falls back to ``"text"``.
    """
    if query.startswith(_AUDIO_PREFIX):
        return "audio"
    if query.startswith(_IMAGE_PREFIX):
        return "image"
    # Optional metadata-based detection
    modality_hint = user.get("modality", "")
    if modality_hint in ("audio", "image"):
        return modality_hint
    return "text"


def _extract_bytes(query: str, prefix: str) -> bytes:
    """Strip the prefix and return the remainder as raw bytes (UTF-8 encoded).

    In production the LangGraph graph would replace the query with actual bytes
    before calling the intake node; this helper exists so that tests can supply
    a simple ``b"audio:<payload>"`` string and have it decoded sensibly.
    """
    payload = query[len(prefix):]
    return payload.encode("utf-8") if isinstance(payload, str) else payload


def _extract_media_ref(query: str, user: dict) -> str | None:  # noqa: ARG001
    """Extract a Cloud Storage URI from the query string or user metadata.

    Looks for a ``gs://…`` URI anywhere in the query or in ``user["media_uri"]``.
    """
    # Look for gs:// URI in query
    match = re.search(r"gs://[^\s]+", query)
    if match:
        return match.group(0)
    return user.get("media_uri")


async def _run_gemini(model: Any, prompt: str) -> str:
    """Call Gemini synchronously (it may be async-capable) and return the text."""
    try:
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else str(response)
    except Exception:
        logger.exception("Gemini call failed")
        return ""


def _parse_json(text: str) -> dict | None:
    """Extract the first JSON object from a string.  Returns ``None`` on failure."""
    if not text:
        return None
    # Try full parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find a JSON object within the text (Gemini sometimes adds prose)
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _classify_type(raw_type: str) -> str:
    """Map an extracted issue type label to one of the 8 canonical categories.

    Matching strategy (case-insensitive):
    1. Exact match against ``KNOWN_ISSUE_TYPES``.
    2. Substring / keyword scan for common synonyms.
    3. Default to ``"other"``.
    """
    normalised = raw_type.strip().lower()

    # 1. Exact match
    if normalised in KNOWN_ISSUE_TYPES:
        return normalised

    # 2. Keyword-based synonyms
    _SYNONYMS: dict[str, list[str]] = {
        "road": ["pothole", "pavement", "street", "highway", "road damage", "road repair", "tarmac"],
        "sanitation": ["garbage", "waste", "trash", "sewage", "drainage", "sewer", "rubbish", "litter"],
        "water": ["pipe", "leak", "supply", "tap", "drinking water", "water shortage"],
        "electricity": ["power", "electric", "light", "outage", "blackout", "transformer", "wiring"],
        "flood": ["flooding", "waterlogging", "inundation", "overflowing"],
        "traffic": ["congestion", "signal", "jam", "accident", "parking"],
        "health": ["hospital", "clinic", "medical", "disease", "hygiene", "epidemic"],
    }

    for canonical, keywords in _SYNONYMS.items():
        if any(kw in normalised for kw in keywords):
            return canonical

    return "other"
