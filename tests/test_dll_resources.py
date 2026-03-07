from flatlas_translator.dll_resources import decode_resource_text_blob


def test_decode_resource_text_blob_utf16le_with_bom() -> None:
    payload = "Hallo Welt".encode("utf-16")
    assert decode_resource_text_blob(payload) == "Hallo Welt"


def test_decode_resource_text_blob_single_byte_fallback() -> None:
    payload = b"Random Mission Resources"
    assert decode_resource_text_blob(payload) == "Random Mission Resources"
