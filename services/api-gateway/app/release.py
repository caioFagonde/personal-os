from __future__ import annotations

import re
from dataclasses import dataclass

SEMVER_RE = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+(?P<meta>[0-9A-Za-z.-]+))?$")


@dataclass(frozen=True, order=True)
class ReleaseVersion:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    metadata: str | None = None

    @property
    def channel(self) -> str:
        if not self.prerelease:
            return "stable"
        head = self.prerelease.split(".", 1)[0]
        return head if head in {"alpha", "beta", "rc", "nightly"} else "preview"

    @property
    def is_production(self) -> bool:
        return self.channel == "stable"

    def public(self) -> str:
        suffix = f"-{self.prerelease}" if self.prerelease else ""
        meta = f"+{self.metadata}" if self.metadata else ""
        return f"{self.major}.{self.minor}.{self.patch}{suffix}{meta}"


def parse_release_version(value: str) -> ReleaseVersion:
    match = SEMVER_RE.match(value.strip())
    if not match:
        raise ValueError("release version must be valid semver")
    return ReleaseVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=match.group("pre"),
        metadata=match.group("meta"),
    )


def release_manifest(version: str, commit_sha: str, channel: str | None = None) -> dict[str, str | bool]:
    parsed = parse_release_version(version)
    sha = commit_sha.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        raise ValueError("commit_sha must be a git sha prefix or full sha")
    effective_channel = channel or parsed.channel
    return {
        "version": parsed.public(),
        "channel": effective_channel,
        "commit_sha": sha.lower(),
        "production": effective_channel == "stable" and parsed.is_production,
    }
