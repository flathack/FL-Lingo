"""Tests for RDL-aware translation in translator_service."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flatlas_translator.translator_service import (
    _is_rdl_text,
    _translate_rdl_aware,
    translate_text,
    translate_text_batch,
)


# ---------------------------------------------------------------------------
# _is_rdl_text detection
# ---------------------------------------------------------------------------

def test_detects_rdl_text():
    rdl = '<?xml version="1.0" encoding="UTF-16"?><RDL><TEXT>hello</TEXT></RDL>'
    assert _is_rdl_text(rdl) is True


def test_plain_text_not_rdl():
    assert _is_rdl_text("Just a normal sentence.") is False


def test_rdl_case_insensitive():
    assert _is_rdl_text("<rdl><text>hi</text></rdl>") is True


# ---------------------------------------------------------------------------
# _translate_rdl_aware preserves XML structure
# ---------------------------------------------------------------------------

_SAMPLE_RDL = (
    '<?xml version="1.0" encoding="UTF-16"?>\r\n'
    "<RDL><PUSH/><TEXT>Connecting to global server ......</TEXT>"
    "<PARA/><POP/></RDL>"
)


def _fake_google(text: str, src: str, tgt: str) -> str:
    """Simulate Google Translate returning German text."""
    mapping = {
        "Connecting to global server ......": "Verbinden mit globalem Server ......",
    }
    return mapping.get(text, f"[translated]{text}")


@patch("flatlas_translator.translator_service._translate_google", side_effect=_fake_google)
def test_rdl_structure_preserved(mock_google):
    result = _translate_rdl_aware(_SAMPLE_RDL, "en", "de", "google")

    # XML declaration must be unchanged (encoding, not kodierung!)
    assert 'encoding="UTF-16"' in result
    assert "kodierung" not in result

    # RDL tags must be preserved verbatim
    assert "<RDL>" in result
    assert "</RDL>" in result
    assert "<PUSH/>" in result
    assert "<PARA/>" in result
    assert "<POP/>" in result

    # Only the text content must be translated
    assert "Verbinden mit globalem Server" in result

    # Google Translate should only have been called with the inner text
    mock_google.assert_called_once_with(
        "Connecting to global server ......", "en", "de"
    )


_MULTI_TEXT_RDL = (
    '<?xml version="1.0" encoding="UTF-16"?>\r\n'
    '<RDL><PUSH/><TEXT>Welcome</TEXT><PARA/>'
    '<TEXT color="#FF0000">Danger zone</TEXT><POP/></RDL>'
)


@patch("flatlas_translator.translator_service._translate_google")
def test_multiple_text_nodes_translated(mock_google):
    mock_google.side_effect = lambda t, s, d: {"Welcome": "Willkommen", "Danger zone": "Gefahrenzone"}.get(t, t)
    result = _translate_rdl_aware(_MULTI_TEXT_RDL, "en", "de", "google")

    assert "Willkommen" in result
    assert "Gefahrenzone" in result
    assert '<TEXT color="#FF0000">' in result
    assert 'encoding="UTF-16"' in result
    assert mock_google.call_count == 2


@patch("flatlas_translator.translator_service._translate_google")
def test_empty_text_node_not_sent_to_api(mock_google):
    rdl = '<RDL><TEXT>   </TEXT><TEXT>Hello</TEXT></RDL>'
    mock_google.return_value = "Hallo"
    result = _translate_rdl_aware(rdl, "en", "de", "google")

    # Only one call – the empty/whitespace TEXT node should be skipped
    mock_google.assert_called_once_with("Hello", "en", "de")
    assert "Hallo" in result


# ---------------------------------------------------------------------------
# translate_text integration (dispatch to RDL-aware path)
# ---------------------------------------------------------------------------

@patch("flatlas_translator.translator_service._translate_google", side_effect=_fake_google)
def test_translate_text_rdl_dispatch(mock_google):
    result = translate_text(_SAMPLE_RDL, "en", "de", "google")
    assert 'encoding="UTF-16"' in result
    assert "Verbinden mit globalem Server" in result


@patch("flatlas_translator.translator_service._translate_google", return_value="Hallo Welt")
def test_translate_text_plain_unchanged(mock_google):
    result = translate_text("Hello World", "en", "de", "google")
    assert result == "Hallo Welt"


# ---------------------------------------------------------------------------
# translate_text_batch with mixed RDL and plain texts
# ---------------------------------------------------------------------------

@patch("flatlas_translator.translator_service._translate_google")
@patch("flatlas_translator.translator_service._translate_google_batch")
def test_batch_separates_rdl_from_plain(mock_batch, mock_single):
    plain = "Hello World"
    rdl = '<RDL><TEXT>Goodbye</TEXT></RDL>'

    mock_single.return_value = "Tschuess"
    mock_batch.return_value = ["Hallo Welt"]

    results = translate_text_batch([plain, rdl], "en", "de", "google")

    # Plain text goes to batch
    mock_batch.assert_called_once_with([plain], "en", "de")
    assert results[0] == "Hallo Welt"

    # RDL text was handled individually, preserving structure
    assert "<RDL>" in results[1]
    assert "Tschuess" in results[1]
