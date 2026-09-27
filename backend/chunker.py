from __future__ import annotations

from typing import TypedDict


class Chunk(TypedDict):
    path: str
    start_line: int
    end_line: int
    content: str
    chunk_type: str


def _window(lines: list[str], start: int, end: int, header_type: str, path: str) -> Chunk:
    start = max(1, start)
    end = min(len(lines), end)
    body = "\n".join(lines[start - 1:end])
    header = f"File: {path} | Lines: {start}-{end} | Type: {header_type}"
    return {"path": path, "start_line": start, "end_line": end, "content": header + "\n" + body, "chunk_type": header_type}


def chunk_parsed_files(parsed_files: list[dict], max_chunks: int = 500) -> list[Chunk]:
    chunks: list[Chunk] = []
    for parsed in parsed_files:
        if len(chunks) >= max_chunks:
            break
        path = parsed["path"]
        lines = parsed.get("content", "").splitlines()
        if not lines:
            continue
        symbols = sorted(parsed.get("symbols", []), key=lambda s: (s["start_line"], s["end_line"]))
        if not symbols:
            for start in range(1, len(lines) + 1, 100):
                chunks.append(_window(lines, start, start + 99, "file_window", path))
                if len(chunks) >= max_chunks:
                    break
            continue
        for symbol in symbols:
            start, end = symbol["start_line"], symbol["end_line"]
            if end - start + 1 <= 500:
                chunks.append(_window(lines, start, end, symbol["type"], path))
            else:
                cursor = start
                while cursor <= end:
                    chunks.append(_window(lines, cursor, min(end, cursor + 199), symbol["type"], path))
                    if len(chunks) >= max_chunks:
                        break
                    if cursor + 199 >= end:
                        break
                    cursor += 200 - 40
            if len(chunks) >= max_chunks:
                break
    return chunks[:max_chunks]
