import pytest

from app.runtime import (
    OCRBlock,
    Detection,
    TranscriptSegment,
    classify_asset,
    detect_runtime_health,
    extension_for,
    heuristic_detect,
    heuristic_ocr,
    heuristic_transcribe,
    lookup_queries,
    process_asset,
    summarize_modal_result,
)


def test_classify_asset_all_paths():
    assert extension_for("no_extension") == ""
    assert classify_asset("page.jpg", "") == "image"
    assert classify_asset("any.bin", "image/png") == "image"
    assert classify_asset("lecture.mp3", "") == "audio"
    assert classify_asset("any.bin", "audio/wav") == "audio"
    assert classify_asset("clip.mp4", "") == "video"
    assert classify_asset("any.bin", "video/mp4") == "video"
    assert classify_asset("paper.pdf", "") == "pdf"
    assert classify_asset("any.bin", "application/pdf") == "pdf"
    assert classify_asset("note.md", "") == "text"
    assert classify_asset("any.bin", "text/plain") == "text"
    assert classify_asset("blob.bin", "") == "binary"


def test_heuristic_ocr_from_hint_payload_and_empty():
    ocr = heuristic_ocr("chapter.jpg", b"", "Chapter 1. Retrieval practice improves memory.")
    assert any("Retrieval" in block.text for block in ocr)
    from_payload = heuristic_ocr("note.txt", b"Line one. Line two.", None)
    assert len(from_payload) == 2
    assert heuristic_ocr("image.jpg", b"", None) == []


def test_heuristic_detection_catalog_and_visual_fallback():
    detections = heuristic_detect("chapter-book.jpg", b"", "This page contains abstract theorem diagram whiteboard contract")
    labels = {d.label for d in detections}
    assert {"book", "paper", "equation", "diagram", "whiteboard", "document"} <= labels
    fallback = heuristic_detect("random.jpg", b"", None)
    assert fallback[0].label == "visual_capture"
    assert heuristic_detect("random.bin", b"", None) == []


def test_transcribe_from_hint_payload_and_empty():
    segments = heuristic_transcribe("audio.wav", b"", "remember to review spaced repetition")
    assert segments[0].end_seconds > 0
    assert "review" in segments[0].text
    text_segments = heuristic_transcribe("audio.txt", b"transcribed payload", None)
    assert text_segments[0].confidence == 0.75
    assert heuristic_transcribe("audio.wav", b"", None) == []


def test_summary_and_lookup_query_branches():
    assert "No readable" in summarize_modal_result("image.jpg", [], [], [])
    ocr = [OCRBlock("Retrieval Practice improves Memory.", 0.9)]
    det = [Detection("book", 0.8)]
    summary = summarize_modal_result("book.jpg", det, ocr, [])
    assert "Retrieval" in summary
    queries = lookup_queries("book.jpg", det, ocr, [])
    assert any("book" in q for q in queries)
    assert any("Retrieval" in q for q in queries)
    plain = lookup_queries("note.txt", [], [OCRBlock("lowercase concept without titlecase", 0.8)], [])
    assert any("Summarize" in q for q in plain)
    fallback = lookup_queries("blob.bin", [], [], [])
    assert fallback == ["Classify and summarize blob.bin"]
    transcript_query = lookup_queries("audio.wav", [], [], [TranscriptSegment("Named Concept", 0, 1, 0.9)])
    assert any("Named" in q for q in transcript_query)


def test_process_asset_result_shape_and_size_limit(monkeypatch):
    result = process_asset("book-page.jpg", b"abc", "image/jpeg", "A diagram of retrieval practice and spaced repetition.")
    assert result["sha256"]
    assert result["media_type"] == "image"
    assert result["detections"]
    assert result["ocr_blocks"]
    assert result["summary"].startswith("Captured")
    assert result["lookup_queries"]
    monkeypatch.setenv("MODEL_RUNTIME_MAX_BYTES", "1")
    with pytest.raises(ValueError):
        process_asset("large.bin", b"ab")


def test_runtime_health_modes(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "disabled")
    monkeypatch.setenv("VISION_PROVIDER", "externalx")
    monkeypatch.delenv("EXTERNALX_READY", raising=False)
    health = detect_runtime_health()
    assert health["status"] == "degraded"
    assert any(r["mode"] == "external" for r in health["runtimes"])
    monkeypatch.setenv("OCR_PROVIDER", "heuristic")
    monkeypatch.setenv("VISION_PROVIDER", "heuristic")
    monkeypatch.setenv("AUDIO_PROVIDER", "heuristic")
    health = detect_runtime_health()
    assert health["status"] == "ok"
    assert any(r["name"] == "ocr" and r["available"] for r in health["runtimes"])
    monkeypatch.setenv("VISION_PROVIDER", "externalx")
    monkeypatch.setenv("EXTERNALX_READY", "true")
    health = detect_runtime_health()
    assert any(r["name"] == "object_detection" and r["available"] for r in health["runtimes"])
