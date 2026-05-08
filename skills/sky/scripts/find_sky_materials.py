#!/usr/bin/env python3
"""Search local sky-take-out learning materials and source files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {".md", ".html", ".json", ".sql", ".java"}
DAY_RE = re.compile(r"day\s*0?(\d{1,2})", re.IGNORECASE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


@dataclass
class Match:
    score: int
    source: str
    path: Path
    rel_path: str
    snippet: str


def normalize_day(value: str | None) -> str | None:
    if not value:
        return None
    match = DAY_RE.search(value)
    if not match:
        return value.lower() if value.lower().startswith("day") else value
    return f"day{int(match.group(1)):02d}"


def find_project_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "pom.xml").exists() and (
            (path / "sky-server").exists()
            or (path / "sky-common").exists()
            or (path / "sky-pojo").exists()
        ):
            return path
    return start


def find_course_root(project_root: Path) -> Path:
    for path in [project_root, *project_root.parents]:
        if (path / "讲义").exists() or (path / "资料").exists():
            return path
    for path in [project_root, *project_root.parents]:
        if path.name in {"讲义", "资料"}:
            return path.parent
    return project_root


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean_cjk_term(term: str) -> str:
    term = re.sub(r"分为?哪?几个阶段", "", term)
    term = re.sub(r"哪几个阶段", "", term)
    replacements = (
        "在哪里",
        "是什么",
        "有哪些",
        "哪几个",
        "几个",
        "什么",
        "分为",
        "分哪",
        "接口",
        "功能",
        "？",
        "?",
    )
    cleaned = term
    for item in replacements:
        cleaned = cleaned.replace(item, "")
    return cleaned.strip()


def query_terms(query: str, day: str | None, module: str | None) -> list[str]:
    terms: set[str] = set()
    query_without_day = DAY_RE.sub(" ", query)

    if module:
        terms.add(module)

    for ident in IDENT_RE.findall(query_without_day):
        if ident.lower() != "day":
            terms.add(ident)

    for cjk in CJK_RE.findall(query_without_day):
        terms.add(cjk)
        cleaned = clean_cjk_term(cjk)
        if len(cleaned) >= 2:
            terms.add(cleaned)
        for part in re.split(r"[的是和与及或、，。？?]", cleaned):
            if len(part) >= 2:
                terms.add(part)

    for token in re.split(r"[\s,，.。:：;；/\\()\[\]{}<>《》\"'`]+", query_without_day):
        token = token.strip()
        if len(token) >= 2 and token.lower() != (day or ""):
            terms.add(token)

    return sorted(terms, key=len, reverse=True)


def candidate_files(
    project_root: Path,
    course_root: Path,
    day: str | None,
    include_java: bool,
    include_readme: bool,
) -> Iterable[Path]:
    readme_names = ("Readme.md", "README.md", "readme.md")
    if include_readme:
        for name in readme_names:
            readme = course_root / name
            if readme.exists():
                yield readme
                break

    days = [day] if day else []

    for day_name in days:
        lecture_dir = course_root / "讲义" / day_name
        if lecture_dir.exists():
            yield from lecture_dir.glob("*.md")

        material_dir = course_root / "资料" / day_name
        if material_dir.exists():
            for suffix in (".md", ".html", ".json", ".sql"):
                yield from material_dir.rglob(f"*{suffix}")

    if include_java:
        for java_file in project_root.rglob("*.java"):
            if any(part in {".git", ".idea", "target"} for part in java_file.parts):
                continue
            yield java_file


def source_label(path: Path, project_root: Path, course_root: Path) -> str:
    try:
        path.relative_to(project_root)
        if path.suffix.lower() == ".java":
            return f"源码 / {path.name}"
    except ValueError:
        pass

    try:
        rel = path.relative_to(course_root)
        parts = rel.parts
        if len(parts) >= 3 and parts[0] == "讲义" and parts[1].lower().startswith("day"):
            return f"{parts[1]} / 讲义 / {path.name}"
        if len(parts) >= 3 and parts[0] == "资料" and parts[1].lower().startswith("day"):
            if path.suffix.lower() == ".html":
                kind = "接口文档"
            elif path.suffix.lower() == ".sql":
                kind = "SQL"
            else:
                kind = "资料"
            return f"{parts[1]} / {kind} / {path.name}"
        if path.name.lower() == "readme.md":
            return f"Readme.md / {path.name}"
    except ValueError:
        pass

    return path.name


def make_snippet(text: str, terms: list[str], width: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text.replace("\ufeff", "")).strip()
    if not compact:
        return ""
    lower = compact.lower()
    best = -1
    for term in terms:
        idx = lower.find(term.lower())
        if idx >= 0:
            best = idx
            break
    if best < 0:
        return compact[:width]
    start = max(0, best - width // 2)
    end = min(len(compact), best + width // 2)
    prefix = "..." if start else ""
    suffix = "..." if end < len(compact) else ""
    return f"{prefix}{compact[start:end]}{suffix}"


def score_text(path: Path, text: str, terms: list[str], query: str) -> int:
    score = 0
    name = path.name.lower()
    lower = text.lower()
    for term in terms:
        t = term.lower()
        if not t:
            continue
        if t in name:
            score += 40
        count = lower.count(t)
        if count:
            score += min(80, count * max(4, len(term)))
    if path.suffix.lower() == ".java" and any(term in path.stem for term in terms):
        score += 60
    if score > 0 and path.suffix.lower() == ".html":
        score += 5
    if score > 0 and "接口" in query and path.suffix.lower() == ".html":
        score += 80
    if score > 0 and any(part.lower().startswith("day") for part in path.parts):
        score += 10
    if path.name.lower() == "readme.md":
        score -= 8
    return score


def search(query: str, day: str | None, module: str | None, limit: int) -> tuple[list[Match], dict[str, str]]:
    project_root = find_project_root(Path.cwd().resolve())
    course_root = find_course_root(project_root)
    terms = query_terms(query, day, module)
    include_java = bool(IDENT_RE.search(DAY_RE.sub(" ", query)))
    include_readme = not day or "readme" in query.lower() or "项目" in query
    matches: list[Match] = []

    seen: set[Path] = set()
    for path in candidate_files(project_root, course_root, day, include_java, include_readme):
        path = path.resolve()
        if path in seen or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        seen.add(path)
        try:
            text = read_text(path)
        except OSError:
            continue
        score = score_text(path, text, terms, query)
        if score <= 0:
            continue
        try:
            rel_path = str(path.relative_to(course_root))
        except ValueError:
            rel_path = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else str(path)
        matches.append(
            Match(
                score=score,
                source=source_label(path, project_root, course_root),
                path=path,
                rel_path=rel_path,
                snippet=make_snippet(text, terms),
            )
        )

    matches.sort(key=lambda item: (-item.score, item.rel_path))
    meta = {
        "project_root": str(project_root),
        "course_root": str(course_root),
        "day": day or "",
        "module": module or "",
        "terms": ", ".join(terms),
    }
    return matches[:limit], meta


def print_text(matches: list[Match], meta: dict[str, str]) -> None:
    if not matches:
        print("本地资料未找到明确出处")
        return

    print(f"project_root: {meta['project_root']}")
    print(f"course_root: {meta['course_root']}")
    if meta["day"]:
        print(f"day: {meta['day']}")
    if meta["module"]:
        print(f"module: {meta['module']}")
    print(f"terms: {meta['terms']}")
    print()

    for index, match in enumerate(matches, start=1):
        print(f"[{index}] score={match.score}")
        print(f"出处：{match.source}")
        print(f"path: {match.path}")
        if match.snippet:
            print(f"snippet: {match.snippet}")
        print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Search local sky-take-out course materials.")
    parser.add_argument("query", help="User question or search terms.")
    parser.add_argument("--day", help="Restrict course materials to dayXX.")
    parser.add_argument("--module", help="Module name supplied by the user.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum matches to print.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    day = normalize_day(args.day) or normalize_day(args.query)
    matches, meta = search(args.query, day, args.module, args.limit)

    if args.json:
        print(
            json.dumps(
                {
                    "meta": meta,
                    "matches": [
                        {
                            "score": match.score,
                            "source": match.source,
                            "path": str(match.path),
                            "relative_path": match.rel_path,
                            "snippet": match.snippet,
                        }
                        for match in matches
                    ],
                    "not_found": not matches,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_text(matches, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
