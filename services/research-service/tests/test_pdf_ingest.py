from app.pdf_ingest import chunk_text, estimate_tokens, extract_citations, sha256_bytes


def test_chunk_text_overlaps_and_preserves_content():
    text = "Paragraph one. " * 80 + "\n\n" + "Paragraph two. " * 80
    chunks = chunk_text(text, target_chars=500, overlap_chars=50)
    assert len(chunks) > 1
    assert "Paragraph one" in chunks[0]
    assert "Paragraph two" in chunks[-1]


def test_extract_citations_from_reference_block():
    text = "Body text\n\nReferences\n[1] Smith, J. Important Paper. Journal, 2021. doi:10.1000/xyz123\n[2] Doe, A. Web Paper. 2020. https://example.org/paper"
    citations = extract_citations(text)
    assert len(citations) >= 2
    assert citations[0].doi == "10.1000/xyz123"
    assert any(c.year == 2020 for c in citations)


def test_hash_and_estimated_tokens_are_deterministic():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert estimate_tokens("one two three four") >= 5


def test_empty_chunk_and_citations_are_empty():
    assert chunk_text('   ') == []
    assert extract_citations('') == []


def test_extract_citations_handles_blank_boundaries_duplicates_and_limit():
    text = '''References
[1] A long enough citation line. 2021. https://example.org/a

[1] A long enough citation line. 2021. https://example.org/a
2. Another long enough citation line. 2022.
Tiny
'''
    citations = extract_citations(text, limit=1)
    assert len(citations) == 1
    assert citations[0].url == 'https://example.org/a'
