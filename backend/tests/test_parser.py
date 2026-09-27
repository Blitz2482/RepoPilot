from pathlib import Path

from parser import parse_repo
from chunker import chunk_parsed_files


def test_parser_finds_python_symbols(tmp_path: Path):
    file = tmp_path / "example.py"
    file.write_text("class Demo:\n    def work(self):\n        return 1\n", encoding="utf-8")
    parsed = parse_repo(str(tmp_path))
    assert parsed
    assert any(s["name"] == "Demo" for s in parsed[0]["symbols"])
    chunks = chunk_parsed_files(parsed)
    assert chunks
    assert chunks[0]["start_line"] >= 1


def test_parser_includes_readme_as_document_context(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Project\nThis explains the architecture.\n", encoding="utf-8")
    parsed = __import__("parser").parse_repo(str(tmp_path))
    readme = next(item for item in parsed if item["path"] == "README.md")
    assert readme["language"] == "Markdown"
    assert "architecture" in readme["content"]
