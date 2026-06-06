import pytest

from app.release import parse_release_version, release_manifest


def test_parse_release_version_channels():
    assert parse_release_version("1.2.3").channel == "stable"
    assert parse_release_version("1.2.3-beta.1").channel == "beta"
    assert parse_release_version("1.2.3-feature.foo").channel == "preview"
    assert parse_release_version("1.2.3+abc123").public() == "1.2.3+abc123"


def test_release_manifest_validates_sha_and_production():
    manifest = release_manifest("1.2.3", "ABCDEF1")
    assert manifest == {"version": "1.2.3", "channel": "stable", "commit_sha": "abcdef1", "production": True}
    assert release_manifest("1.2.3-rc.1", "abcdef1")["production"] is False


def test_invalid_release_values_fail():
    with pytest.raises(ValueError):
        parse_release_version("v1.2.3")
    with pytest.raises(ValueError):
        release_manifest("1.2.3", "not-a-sha")
