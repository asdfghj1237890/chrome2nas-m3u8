import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from downloader import SegmentDownloader, TS_PACKET_SIZE, TS_SYNC_BYTE, JPEG_MAGIC, PNG_MAGIC, GIF_MAGIC


def _make_valid_ts_sample(packet_count: int = 5) -> bytes:
    data = bytearray(TS_PACKET_SIZE * packet_count)
    for i in range(packet_count):
        data[i * TS_PACKET_SIZE] = TS_SYNC_BYTE[0]
    # Fill a little noise after sync bytes
    for i in range(1, min(100, len(data))):
        data[i] = (i * 7) % 256
    return bytes(data)


def test_is_valid_ts_content_accepts_sync_bytes_at_expected_positions(tmp_path):
    d = SegmentDownloader(segments=[], output_dir=str(tmp_path), session=object())
    ok, reason = d._is_valid_ts_content(_make_valid_ts_sample())
    assert ok is True
    assert reason == ""


@pytest.mark.parametrize(
    "payload, expected_substring",
    [
        (b"", "Content too small"),
        (b"<!DOCTYPE html><html></html>" + b" " * (TS_PACKET_SIZE + 10), "HTML"),
        (JPEG_MAGIC + b"x" * (TS_PACKET_SIZE + 10), "JPEG"),
        (PNG_MAGIC + b"x" * (TS_PACKET_SIZE + 10), "PNG"),
        (GIF_MAGIC + b"x" * (TS_PACKET_SIZE + 10), "GIF"),
        (b"Error: Forbidden" + b" " * (TS_PACKET_SIZE + 10), "error"),
    ],
)
def test_is_valid_ts_content_rejects_common_block_pages(tmp_path, payload, expected_substring):
    d = SegmentDownloader(segments=[], output_dir=str(tmp_path), session=object())
    ok, reason = d._is_valid_ts_content(payload)
    assert ok is False
    assert expected_substring.lower() in reason.lower()


@pytest.mark.parametrize(
    "payload, content_type, expected_substring",
    [
        (b"", "", "Empty"),
        (b"<html>blocked</html>", "text/html", "text/html"),
        (b"{\"detail\":\"no\"}", "application/json", "application/json"),
        (PNG_MAGIC + b"xxxx", "", "PNG"),
        (b"<?xml version='1.0'?>", "", "HTML/XML"),
        (b"access denied", "", "access denied"),
    ],
)
def test_is_obviously_blocked_response_flags_non_media(tmp_path, payload, content_type, expected_substring):
    d = SegmentDownloader(segments=[], output_dir=str(tmp_path), session=object())
    blocked, reason = d._is_obviously_blocked_response(payload, content_type=content_type)
    assert blocked is True
    assert expected_substring.lower() in reason.lower()


def test_decrypt_segment_with_key_returns_original_ts_when_already_ts(tmp_path):
    d = SegmentDownloader(segments=[], output_dir=str(tmp_path), session=object())
    plain = _make_valid_ts_sample(packet_count=3)
    out = d._decrypt_segment_with_key(
        plain,
        segment_index=0,
        key_bytes=b"0" * 16,
        iv_bytes=b"1" * 16,
        sequence_number=10,
    )
    assert out == plain


def test_decrypt_segment_with_key_prefers_provided_iv(tmp_path):
    d = SegmentDownloader(segments=[], output_dir=str(tmp_path), session=object())

    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    iv = bytes.fromhex("0102030405060708090a0b0c0d0e0f10")

    plaintext = TS_SYNC_BYTE + b"hello-world"  # must start with sync byte
    padded = pad(plaintext, AES.block_size)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded)

    out = d._decrypt_segment_with_key(
        ciphertext,
        segment_index=0,
        key_bytes=key,
        iv_bytes=iv,
        sequence_number=123,
    )
    assert out == plaintext
