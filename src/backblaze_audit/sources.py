from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator, Protocol
import re
import zipfile


DAILY_CSV_RE = re.compile(r"(?:^|/)(\d{4}-\d{2}-\d{2})\.csv$")


@dataclass(frozen=True)
class Member:
    name: str
    compressed_size: int | None = None
    uncompressed_size: int | None = None
    crc32: str | None = None

    @property
    def date_text(self) -> str:
        match = DAILY_CSV_RE.search(self.name)
        if not match:
            raise ValueError(f"Not a daily CSV name: {self.name}")
        return match.group(1)


class Source(Protocol):
    source_type: str
    source_value: str

    def members(self) -> list[Member]: ...

    @contextmanager
    def open(self, member: Member) -> Iterator[BinaryIO]: ...

    def close(self) -> None: ...

    def reconnect(self) -> None: ...


class DirectorySource:
    source_type = "directory"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.source_value = str(self.path.resolve())

    def members(self) -> list[Member]:
        result = []
        for path in self.path.rglob("*.csv"):
            if DAILY_CSV_RE.search(path.name):
                result.append(Member(str(path.relative_to(self.path)), uncompressed_size=path.stat().st_size))
        return sorted(result, key=lambda item: item.date_text)

    @contextmanager
    def open(self, member: Member) -> Iterator[BinaryIO]:
        with (self.path / member.name).open("rb") as handle:
            yield handle

    def close(self) -> None:
        return None

    def reconnect(self) -> None:
        return None


class LocalZipSource:
    source_type = "local_zip"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.source_value = str(self.path.resolve())
        self.archive = zipfile.ZipFile(self.path)

    def members(self) -> list[Member]:
        result = [
            Member(info.filename, info.compress_size, info.file_size, f"{info.CRC:08x}")
            for info in self.archive.infolist()
            if DAILY_CSV_RE.search(info.filename)
        ]
        return sorted(result, key=lambda item: item.date_text)

    @contextmanager
    def open(self, member: Member) -> Iterator[BinaryIO]:
        with self.archive.open(member.name) as handle:
            yield handle

    def close(self) -> None:
        self.archive.close()

    def reconnect(self) -> None:
        self.archive.close()
        self.archive = zipfile.ZipFile(self.path)


class RemoteZipSource:
    source_type = "remote_zip_range"

    def __init__(self, url: str):
        try:
            from remotezip import RemoteZip
        except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
            raise RuntimeError("remotezip is required for --remote-url") from exc
        self.source_value = url
        self._remote_zip_class = RemoteZip
        self.archive = RemoteZip(url, timeout=60)

    def members(self) -> list[Member]:
        result = [
            Member(info.filename, info.compress_size, info.file_size, f"{info.CRC:08x}")
            for info in self.archive.infolist()
            if DAILY_CSV_RE.search(info.filename)
        ]
        return sorted(result, key=lambda item: item.date_text)

    @contextmanager
    def open(self, member: Member) -> Iterator[BinaryIO]:
        with self.archive.open(member.name) as handle:
            yield handle

    def close(self) -> None:
        self.archive.close()

    def reconnect(self) -> None:
        try:
            self.archive.close()
        finally:
            self.archive = self._remote_zip_class(self.source_value, timeout=60)


def make_source(*, input_dir: str | None = None, zip_path: str | None = None, remote_url: str | None = None) -> Source:
    choices = [input_dir is not None, zip_path is not None, remote_url is not None]
    if sum(choices) != 1:
        raise ValueError("Choose exactly one of input_dir, zip_path, or remote_url")
    if input_dir:
        return DirectorySource(input_dir)
    if zip_path:
        return LocalZipSource(zip_path)
    return RemoteZipSource(str(remote_url))
