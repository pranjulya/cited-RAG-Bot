from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from cited_rag.domain.exceptions import StorageError


class LocalObjectStorage:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        return self._root.joinpath(*key.split("/"))

    async def put(self, key: str, chunks: AsyncIterator[bytes]) -> str:
        dest = self.path_for(key)
        tmp = dest.with_name(dest.name + ".part")

        def _prepare() -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if tmp.exists():
                tmp.unlink()

        await asyncio.to_thread(_prepare)
        try:
            with tmp.open("wb") as handle:
                async for chunk in chunks:
                    await asyncio.to_thread(handle.write, chunk)
            await asyncio.to_thread(tmp.replace, dest)
        except OSError as exc:
            if tmp.exists():
                await asyncio.to_thread(tmp.unlink)
            raise StorageError("failed to write source PDF") from exc
        return f"local://{key}"

    async def get(self, key: str) -> bytes:
        path = self.path_for(key)

        def _read() -> bytes:
            try:
                return path.read_bytes()
            except FileNotFoundError as exc:
                raise StorageError("source PDF is missing") from exc
            except OSError as exc:
                raise StorageError("failed to read source PDF") from exc

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        path = self.path_for(key)

        def _delete() -> None:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise StorageError("failed to delete source PDF") from exc

        await asyncio.to_thread(_delete)
