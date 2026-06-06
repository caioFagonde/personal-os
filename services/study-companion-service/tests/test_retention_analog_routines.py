from datetime import datetime, timezone

import pytest

from app.analog import classify_media, process_analog_input, lightweight_ocr_from_text_hint, heuristic_detect_objects, infer_title
from app.retention import ReviewState, desirable_difficulty, interleave_plan, reminder_schedule, retention_probability, sm2_plus
from app.routines import cron_for, recommended_routines


def test_sm2_plus_success_and_failure_paths():
    now = datetime(2026, 6, 6, tzinfo=timezone.utc)
    result = sm2_plus(5, ReviewState(interval_days=6, repetitions=2, stability=3.0), now)
    assert result.interval_days > 6
    assert result.repetitions == 3
    assert result.due_at > now
    failed = sm2_plus(1, ReviewState(interval_days=10, repetitions=4, stability=5.0), now)
    assert failed.interval_days == 1
    assert failed.repetitions == 0
    assert 'reset' in failed.rationale


def test_retention_probability_and_desirable_difficulty():
    assert retention_probability(0, 2) == 1.0
    assert retention_probability(10, 0) == 0.0
    assert desirable_difficulty(1, 0.8) == 'too_hard'
    assert desirable_difficulty(5, 0.9, 10) == 'too_easy'
    assert desirable_difficulty(4, 0.6, 40) == 'productive'


def test_interleaving_and_reminder_schedule():
    plan = interleave_plan(['physics', 'math'], due_count=2, new_count=1)
    assert plan[0] == 'review_due'
    assert 'crosslink:physics' in plan
    reminders = reminder_schedule(datetime(2026, 6, 6, tzinfo=timezone.utc), 'high')
    assert len(reminders) == 5
    assert reminders[0].isoformat() == '2026-06-06T00:00:00+00:00'


def test_media_classification_and_ocr_hint():
    assert classify_media('page.jpg') == 'image'
    assert classify_media('lecture.mp3') == 'audio'
    assert classify_media('paper.pdf') == 'pdf'
    blocks = lightweight_ocr_from_text_hint('Book Title. A first sentence. A second sentence.')
    assert len(blocks) == 3


def test_analog_capture_creates_reading_lookup_and_zettel_candidates():
    result = process_analog_input('book_page.jpg', b'fake-image-bytes', 'image/jpeg', 'Principles of Learning\nChapter 1 page 7. Spaced repetition improves retention.')
    assert result.media_type == 'image'
    assert result.sha256
    assert any(d.label == 'book' for d in result.detections)
    assert result.reading_candidate['kind'] == 'analog_reading'
    assert result.zettel_candidate['title'] == 'Principles of Learning'
    assert 'Principles of Learning' in result.lookup_queries
    assert 'analog' in result.suggested_tags


def test_detection_and_title_fallbacks():
    assert heuristic_detect_objects('unknown.jpg')[0].label == 'image_capture'
    assert infer_title('') is None
    result = process_analog_input('whiteboard.png', b'x', 'image/png', 'whiteboard diagram of Variational Free Energy')
    assert 'diagram' in [d.label for d in result.detections] or 'whiteboard' in [d.label for d in result.detections]


def test_routines_contract():
    routines = recommended_routines()
    ids = {r['id'] for r in routines}
    assert 'study.due_reviews' in ids
    assert 'analog.ocr_backlog' in ids
    assert 'tasks.followups' in ids
    assert cron_for('sync.health') == '*/5 * * * *'
    assert cron_for('missing') is None
    assert any(r['priority'] == 'high' for r in routines)


def test_sm2_rejects_invalid_quality():
    with pytest.raises(ValueError):
        sm2_plus(6)


def test_additional_media_and_empty_ocr_branches():
    assert classify_media('note.md') == 'text'
    assert classify_media('clip.bin', 'video/mp4') == 'video'
    assert classify_media('blob.bin') == 'binary'
    assert lightweight_ocr_from_text_hint(None) == []
    assert lightweight_ocr_from_text_hint('   ') == []


def test_summary_and_non_reading_branches():
    from app.analog import Detection, OCRBlock, summarize_analog_capture, extract_reading_candidate, build_lookup_queries
    assert 'No reliable OCR' in summarize_analog_capture('image', [], [])
    assert extract_reading_candidate([OCRBlock('random grocery list')], []) == {}
    queries = build_lookup_queries([Detection('image_capture', 0.5)], [OCRBlock('')])
    assert 'image_capture' not in queries


def test_title_regex_and_no_detection_binary():
    assert infer_title('page 1\nchapter 2\nTitle: Quantum Biology') == 'Quantum Biology'
    result = process_analog_input('blob.bin', b'x', 'application/octet-stream', None)
    assert result.detections == []
    assert result.reading_candidate == {}
    assert result.zettel_candidate['title'].startswith('Analog capture')


def test_retention_first_and_second_repetition_branches():
    now = datetime(2026, 6, 6, tzinfo=timezone.utc)
    first = sm2_plus(4, ReviewState(repetitions=0), now)
    assert first.interval_days == 1
    second_good = sm2_plus(5, ReviewState(repetitions=1), now)
    assert second_good.interval_days == 6
    second_barely = sm2_plus(3, ReviewState(repetitions=1), now)
    assert second_barely.interval_days == 3
    assert desirable_difficulty(5, 0.9, None) == 'too_easy'


def test_interleave_without_tags_and_experimental_routines():
    assert interleave_plan([], 0, 0) == []
    exp = recommended_routines(include_experimental=True)
    assert any(r['id'] == 'vision.live_video_sampling' for r in exp)
