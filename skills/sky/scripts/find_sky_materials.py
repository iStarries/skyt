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
MATERIAL_SUFFIXES = {".md", ".html", ".json", ".sql"}
IGNORED_PARTS = {
    ".git",
    ".idea",
    "target",
    "node_modules",
    "node-modules",
    ".validate-deps",
}
DAY_RE = re.compile(r"day\s*0?(\d{1,2})", re.IGNORECASE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
API_PATH_RE = re.compile(r"/[A-Za-z0-9_./{}-]+")


@dataclass(frozen=True)
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
    if match:
        return f"day{int(match.group(1)):02d}"
    lowered = value.lower().strip()
    if re.fullmatch(r"day\d{1,2}", lowered):
        return f"day{int(lowered[3:]):02d}"
    return None


def find_project_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "pom.xml").exists() and (
            (path / "sky-common").exists()
            or (path / "sky-pojo").exists()
            or (path / "sky-server").exists()
        ):
            return path
    return start


def find_course_root(project_root: Path) -> Path:
    for path in [project_root, *project_root.parents]:
        if (path / "讲义").exists() or (path / "资料").exists() or (path / "Readme.md").exists():
            return path
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


def clean_question_wording(term: str) -> str:
    replacements = (
        "分哪几个阶段",
        "分几个阶段",
        "哪几个阶段",
        "几个阶段",
        "分阶段",
        "在哪里",
        "在哪儿",
        "是什么",
        "有什么",
        "有哪些",
        "哪几个",
        "分为",
        "分哪",
        "接口",
        "功能",
        "路径",
        "位置",
    )
    cleaned = term
    for item in replacements:
        cleaned = cleaned.replace(item, "")
    cleaned = re.sub(r"[分问说讲查找]+$", "", cleaned)
    return cleaned.strip()


def query_terms(query: str, day: str | None, module: str | None) -> list[str]:
    terms: set[str] = set()
    query_without_day = DAY_RE.sub(" ", query)

    if module:
        terms.add(module)

    for api_path in API_PATH_RE.findall(query_without_day):
        terms.add(api_path)

    for ident in IDENT_RE.findall(query_without_day):
        if ident.lower() != "day":
            terms.add(ident)

    for cjk in CJK_RE.findall(query_without_day):
        terms.add(cjk)
        cleaned = clean_question_wording(cjk)
        if len(cleaned) >= 2:
            terms.add(cleaned)
        for part in re.split(r"[的是和与及或、，。？?\s]+", cleaned):
            if len(part) >= 2:
                terms.add(part)

    for token in re.split(r"[\s,，。；;：:?？!！()\[\]{}<>《》\"'`]+", query_without_day):
        token = token.strip()
        if len(token) >= 2 and token.lower() != (day or ""):
            terms.add(token)

    return sorted(terms, key=lambda item: (-len(item), item.lower()))


def is_day_overview_query(query: str, day: str | None, module: str | None) -> bool:
    if not day or module:
        return False
    cleaned = DAY_RE.sub(" ", query)
    for word in ("我", "要", "想", "讲", "学习", "学", "开始", "现在", "今天", "一下"):
        cleaned = cleaned.replace(word, "")
    cleaned = re.sub(r"[\s,，。；;：:?？!！()\[\]{}<>《》\"'`]+", "", cleaned)
    return not cleaned


def day_dirs(course_root: Path, day: str | None) -> list[str]:
    if day:
        return [day]

    days: set[str] = set()
    for root_name in ("讲义", "资料"):
        root = course_root / root_name
        if not root.exists():
            continue
        for child in root.iterdir():
            normalized = normalize_day(child.name)
            if child.is_dir() and normalized:
                days.add(normalized)
    return sorted(days)


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def candidate_files(
    project_root: Path,
    course_root: Path,
    day: str | None,
    module: str | None,
    include_java: bool,
    include_readme: bool,
) -> Iterable[Path]:
    if include_readme:
        for name in ("Readme.md", "README.md", "readme.md"):
            readme = course_root / name
            if readme.exists():
                yield readme
                break

    for day_name in day_dirs(course_root, day):
        lecture_dir = course_root / "讲义" / day_name
        if lecture_dir.exists():
            yield from lecture_dir.glob("*.md")

        material_dir = course_root / "资料" / day_name
        if material_dir.exists():
            for suffix in MATERIAL_SUFFIXES:
                yield from material_dir.rglob(f"*{suffix}")

    if include_java:
        for java_file in project_root.rglob("*.java"):
            if not is_ignored(java_file):
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
    except ValueError:
        return path.name

    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "讲义" and parts[1].lower().startswith("day"):
        return f"{parts[1]} / 讲义 / {path.name}"
    if len(parts) >= 3 and parts[0] == "资料" and parts[1].lower().startswith("day"):
        if path.suffix.lower() == ".html":
            kind = "接口文档" if "项目接口文档" in parts or "接口" in path.name else "资料"
        elif path.suffix.lower() == ".sql":
            kind = "SQL"
        else:
            kind = "资料"
        return f"{parts[1]} / {kind} / {path.name}"
    if path.name.lower() == "readme.md":
        return "Readme.md"
    return path.name


def relative_path(path: Path, project_root: Path, course_root: Path) -> str:
    for root in (course_root, project_root):
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def make_snippet(text: str, terms: list[str], width: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text.replace("\ufeff", "")).strip()
    if not compact:
        return ""

    lower = compact.lower()
    best = -1
    for term in terms:
        index = lower.find(term.lower())
        if index >= 0:
            best = index
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
    lower_text = text.lower()
    lower_name = path.name.lower()
    lower_stem = path.stem.lower()
    lower_query = query.lower()

    for term in terms:
        lowered = term.lower()
        if not lowered:
            continue
        if lowered in lower_name:
            score += 45
        if lowered == lower_stem:
            score += 80
        count = lower_text.count(lowered)
        if count:
            score += min(100, count * max(4, min(len(term), 12)))

    suffix = path.suffix.lower()
    if score > 0 and suffix == ".html" and any(word in query for word in ("接口", "路径", "文档")):
        if "项目接口文档" in path.parts or "接口" in path.name:
            score += 240
        else:
            score -= 25
    if score > 0 and suffix == ".sql" and any(word.lower() in lower_query for word in ("sql", "表", "字段", "数据库")):
        score += 70
    if score > 0 and suffix == ".java" and any(
        word in lower_query for word in ("controller", "service", "mapper", "java", "源码", "类", "方法")
    ):
        score += 60
    if score > 0 and "讲义" in path.parts:
        score += 8
    if path.name.lower() == "readme.md":
        score -= 10
    return score


def should_include_java(query: str, terms: list[str]) -> bool:
    lower_query = query.lower()
    if any(word in lower_query for word in ("controller", "service", "mapper", "java", "源码")):
        return True
    if any(word in query for word in ("类", "方法", "代码")):
        return True
    return any(term.endswith(("Controller", "Service", "Mapper", "DTO", "VO")) for term in terms)


def day_overview_matches(project_root: Path, course_root: Path, day: str, limit: int) -> list[Match]:
    matches: list[Match] = []
    lecture_dir = course_root / "讲义" / day
    if lecture_dir.exists():
        for path in sorted(lecture_dir.glob("*.md")):
            text = read_text(path)
            matches.append(
                Match(
                    score=120,
                    source=source_label(path, project_root, course_root),
                    path=path,
                    rel_path=relative_path(path, project_root, course_root),
                    snippet=make_snippet(text, [day, "课程内容", "课程目标"]),
                )
            )

    material_dir = course_root / "资料" / day
    if material_dir.exists():
        for path in sorted(material_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in MATERIAL_SUFFIXES and not is_ignored(path):
                text = read_text(path)
                matches.append(
                    Match(
                        score=80,
                        source=source_label(path, project_root, course_root),
                        path=path,
                        rel_path=relative_path(path, project_root, course_root),
                        snippet=make_snippet(text, [day]),
                    )
                )
    return matches[:limit]


def search(query: str, day: str | None, module: str | None, limit: int) -> tuple[list[Match], dict[str, str]]:
    project_root = find_project_root(Path.cwd().resolve())
    course_root = find_course_root(project_root)
    terms = query_terms(query, day, module)
    include_java = should_include_java(query, terms)
    include_readme = bool(day or module) and any(word in query for word in ("项目", "介绍", "架构", "Readme", "README"))
    matches: list[Match] = []

    seen: set[Path] = set()
    for candidate in candidate_files(project_root, course_root, day, module, include_java, include_readme):
        path = candidate.resolve()
        if path in seen or path.suffix.lower() not in TEXT_SUFFIXES or is_ignored(path):
            continue
        seen.add(path)
        try:
            text = read_text(path)
        except OSError:
            continue
        score = score_text(path, text, terms, query)
        if score <= 0:
            continue
        matches.append(
            Match(
                score=score,
                source=source_label(path, project_root, course_root),
                path=path,
                rel_path=relative_path(path, project_root, course_root),
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
    if is_day_overview_query(query, day, module):
        return day_overview_matches(project_root, course_root, day, limit), meta

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
    module = args.module.strip() if args.module else None

    if not day and not module:
        print("请先确认当前学习的是哪个 day 或哪个模块。")
        return 2

    matches, meta = search(args.query, day, module, args.limit)

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
