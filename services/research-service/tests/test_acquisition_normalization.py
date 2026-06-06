from app.acquisition import SearchResult, dedupe_results, normalize_doi, reconstruct_openalex_abstract


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/ABC"
    assert normalize_doi(None) is None


def test_reconstruct_openalex_abstract():
    abstract = reconstruct_openalex_abstract({"hello": [0], "world": [1]})
    assert abstract == "hello world"


def test_dedupe_results_prefers_first_key():
    one = SearchResult(source="a", title="Same", authors=[], doi="10.1/x")
    two = SearchResult(source="b", title="Other", authors=[], doi="10.1/x")
    assert dedupe_results([one, two]) == [one]
