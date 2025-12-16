from __future__ import annotations

from pathlib import Path

import ffmpeg_wrapper
from ffmpeg_wrapper import FFmpegMerger, merge_segments


def test_create_concat_file_escapes_single_quotes(tmp_path, monkeypatch):
    monkeypatch.setattr(ffmpeg_wrapper.shutil, "which", lambda name: "ffmpeg" if name == "ffmpeg" else None)

    seg = tmp_path / "seg'1.ts"
    seg.write_bytes(b"dummy")

    out = tmp_path / "out.mp4"
    merger = FFmpegMerger(segment_files=[str(seg)], output_file=str(out))

    concat = tmp_path / "concat_list.txt"
    merger._create_concat_file(str(concat))

    content = concat.read_text(encoding="utf-8")
    # The absolute path contains a single quote which must be escaped for ffmpeg concat format.
    assert "\\''" in content
    assert content.startswith("file '")


def test_merge_segments_cleans_up_concat_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ffmpeg_wrapper.shutil, "which", lambda name: "ffmpeg" if name == "ffmpeg" else None)

    # Create dummy segment files.
    seg1 = tmp_path / "segment_00000.ts"
    seg2 = tmp_path / "segment_00001.ts"
    seg1.write_bytes(b"a")
    seg2.write_bytes(b"b")

    output = tmp_path / "out.mp4"

    def _fake_run(command, stdout=None, stderr=None, text=None, timeout=None):
        # Simulate ffmpeg success by writing a non-empty output file.
        Path(command[-1]).write_bytes(b"mp4")

        class _P:
            returncode = 0
            stderr = ""

        return _P()

    monkeypatch.setattr(ffmpeg_wrapper.subprocess, "run", _fake_run)

    ok = merge_segments([str(seg1), str(seg2)], str(output), concat_dir=str(tmp_path), try_re_encode=False)
    assert ok is True
    assert output.exists() and output.stat().st_size > 0
    assert not (tmp_path / "concat_list.txt").exists()
