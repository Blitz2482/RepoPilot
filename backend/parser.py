from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config import settings

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    import tree_sitter_typescript as tsts
    _TREE_SITTER_AVAILABLE = True
    _ts_language = Language(tsts.language_typescript())
    _tsx_capsule = getattr(tsts, "language_tsx", None)
    _tsx_language = Language(_tsx_capsule()) if _tsx_capsule else _ts_language
    LANGUAGES = {
        ".py": (Language(tspython.language()), "Python"),
        ".ts": (_ts_language, "TypeScript"),
        ".tsx": (_tsx_language, "TypeScript"),
        ".js": (_ts_language, "JavaScript"),
        ".jsx": (_tsx_language, "JavaScript"),
    }
except ImportError:  # local fallback only; production requirements install Tree-sitter
    _TREE_SITTER_AVAILABLE = False
    Language = Parser = None
    LANGUAGES = {
        ".py": (None, "Python"), ".ts": (None, "TypeScript"), ".tsx": (None, "TypeScript"),
        ".js": (None, "JavaScript"), ".jsx": (None, "JavaScript"),
    }
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "__pycache__"}


def _new_parser(language: Language) -> Parser:
    try:
        return Parser(language)
    except TypeError:  # tree-sitter older API
        parser = Parser()
        parser.set_language(language)
        return parser


def _node_name(node, source: bytes) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return source[name_node.start_byte:name_node.end_byte].decode(errors="replace").strip()
    text = source[node.start_byte:node.end_byte].decode(errors="replace").splitlines()[0].strip()
    return text[:120]


def _extract_symbols(node, source: bytes) -> list[dict]:
    symbols = []
    targets = {
        "function_definition", "class_definition", "function_declaration", "method_definition",
        "arrow_function", "class_declaration", "import_statement", "import_from_statement", "export_statement",
    }
    if node.type in targets:
        name = _node_name(node, source)
        symbols.append({
            "name": name or "anonymous",
            "type": node.type,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "content": source[node.start_byte:node.end_byte].decode(errors="replace"),
        })
    for child in node.children:
        symbols.extend(_extract_symbols(child, source))
    return symbols


def _regex_symbols(source: str, language: str) -> list[dict]:
    import re
    patterns = []
    if language == "Python":
        patterns = [(r"^\s*class\s+(\w+)", "class_definition"), (r"^\s*def\s+(\w+)", "function_definition")]
    else:
        patterns = [(r"^\s*(?:export\s+)?class\s+(\w+)", "class_declaration"), (r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function_declaration"), (r"^\s*(?:export\s+)?const\s+(\w+)\s*=.*=>", "arrow_function")]
    lines = source.splitlines()
    results = []
    for i, line in enumerate(lines, 1):
        for pattern, node_type in patterns:
            m = re.search(pattern, line)
            if m:
                results.append({"name": m.group(1), "type": node_type, "start_line": i, "end_line": i, "content": line.strip()})
                break
        if re.search(r"^\s*(?:import|export)\b", line):
            results.append({"name": line.strip()[:120], "type": "import_statement" if line.strip().startswith("import") else "export_statement", "start_line": i, "end_line": i, "content": line.strip()})
    return results

def parse_repo(repo_path: str) -> list[dict]:
    results: list[dict] = []
    base = Path(repo_path)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            path = Path(root) / filename
            spec = LANGUAGES.get(path.suffix.lower())
            is_readme = path.name.lower() in {"readme", "readme.md", "readme.mdx", "readme.rst", "readme.txt"}
            if not spec and not is_readme:
                continue
            rel = str(path.relative_to(base)).replace("\\", "/")
            try:
                if path.is_symlink() or path.stat().st_size > settings.max_parsed_file_mb * 1024 * 1024:
                    continue
                source = path.read_bytes()
                if not source.strip():
                    continue
                if is_readme and not spec:
                    language_name = "Markdown"
                    symbols = []
                else:
                    language, language_name = spec
                    if _TREE_SITTER_AVAILABLE:
                        parser = _new_parser(language)
                        tree = parser.parse(source)
                        symbols = _extract_symbols(tree.root_node, source)
                    else:
                        symbols = _regex_symbols(source.decode(errors="replace"), language_name)
                if symbols or source.strip():
                    results.append({
                        "path": rel,
                        "language": language_name,
                        "symbols": symbols,
                        "content": source.decode(errors="replace"),
                    })
            except Exception as exc:
                print(f"Parse error on {rel}: {exc}")
    return results


if __name__ == "__main__":
    import sys, json
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(parse_repo(repo)[:2], indent=2)[:8000])
