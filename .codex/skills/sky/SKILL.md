---
name: sky
description: Use only when the user explicitly types `$sky` while working in the current sky-take-out project to answer learning questions or generate day review Markdown documents from local course materials, Java source, and the user's current learning issues. Do not invoke implicitly for mentions of 苍穹外卖, day01/day02/day03, interfaces, SQL, class names, module names, or repository files unless `$sky` is present.
---

# Sky

Answer sky-take-out learning questions and create course-day review notes from local project materials only. This is a project-level skill for the current `sky-take-out` workspace and must be used only after an explicit `$sky` invocation.

## Workflow

1. Parse the question for `dayXX`, module name, class name, interface name, SQL term, or learning point.
2. If the question includes neither `dayXX` nor a module name, ask which day or module the user is studying. Do not search the whole repository.
3. Search local materials before answering. Prefer `scripts/find_sky_materials.py` from the project root.
4. If the user asks for a review Markdown document, follow **Review Markdown Workflow** below.
5. Otherwise, answer with the source first, then the explanation.
6. If no clear local source is found, answer exactly:

```text
本地资料未找到明确出处
```

Do not add general knowledge, guesses, or web-derived explanations after that sentence.

## Review Markdown Workflow

Use this workflow when the user asks to summarize, review, consolidate, or generate a Markdown note for a course day.

1. Require a specific `dayXX`. If absent, ask which day to review.
2. Search the day's local materials first with the helper. Also inspect relevant current Java source when the review needs to reflect code the user wrote.
3. Use the existing root-level `day03-review.md` as the style reference when available: structured headings, concrete code flows, common mistakes, and a final checklist.
4. Create or update a root-level file named `dayXX-review.md` unless the user gives another path.
5. The document must combine:
   - the day's course outline from `D:\DESKTOP\java\苍穹外卖\sky-take-out-main\讲义\dayXX\*.md`
   - key business flows and request paths
   - DTO / Entity / VO / Mapper / XML relationships when relevant
   - important code snippets or pseudocode for recall
   - pitfalls from the user's current conversation, errors, or debugging history
   - a self-test checklist at the end
6. Keep explanations practical and learning-oriented. Explain why the code exists, how classes connect, and what can go wrong.
7. Do not invent content from later days or outside knowledge. If a point is not supported by local materials or current source, omit it or mark it as not found.
8. After writing the file, verify it exists and briefly report the path plus the main sections covered.

Recommended outline:

```markdown
# 苍穹外卖 dayXX 复习笔记：主题

## 1. 当天课程主线
## 2. 核心功能流程
## 3. 关键代码关系
## 4. 重要知识点
## 5. 易错点和排错
## 6. 接口文档阅读要点
## 7. 复习检查清单
```

Adjust section names to the actual day content; do not force irrelevant sections.

## Git Push Workflow

Use this workflow only when the user explicitly asks to push sky-take-out learning notes or skill updates to GitHub.

1. Check repository state before changing Git history or staging files:

```powershell
git status --short --branch
git remote -v
git branch --show-current
```

2. If Git reports `detected dubious ownership`, add only the current project root as a safe directory using the exact path from Git's message.
3. Stage only the files produced or updated for the current request. Do not stage unrelated untracked files, build output, caches, local config, or user work.
4. Commit with a short message describing the learning note or skill update.
5. Push to the current branch's configured remote, normally `origin master` in this project.
6. If GitHub rejects the push for authentication, network, non-fast-forward, or push-protection reasons, stop and report the exact blocker. Do not force push, rewrite history, approve secret bypass links, or switch remotes unless the user explicitly asks.
7. If push protection reports a secret, treat it as leaked: recommend rotating the credential, replacing the config value with an environment-variable placeholder, and cleaning the commit history before retrying.

## Source Format

Start every substantive answer with one concise source line:

```text
出处：day01 / 讲义 / 苍穹外卖-day01.md
出处：源码 / DishController.java
出处：day02 / 接口文档 / 苍穹外卖-管理端接口.html
```

Use the script's `出处：...` value when available. Keep the source line short; include detailed paths only if the user asks.

## Search Scope

Search only these local materials:

- `讲义/dayXX/*.md`
- `资料/dayXX/**/*.md`
- `资料/dayXX/**/*.html`
- `资料/dayXX/**/*.json`
- `资料/dayXX/**/*.sql`
- `sky-take-out/**/*.java`
- top-level `Readme.md`

Ignore PPT, images, Excel files, build output, IDE metadata, Git internals, and generated dependency folders.

## Retrieval

Run the helper from the project root:

```powershell
py skills\sky\scripts\find_sky_materials.py "day02 新增员工接口在哪里？" --day day02 --limit 8
```

For a module-scoped question without a day:

```powershell
py skills\sky\scripts\find_sky_materials.py "员工管理 新增员工接口在哪里？" --module "员工管理" --limit 8
```

For class or source questions:

```powershell
py skills\sky\scripts\find_sky_materials.py "day03 DishController 是什么？" --day day03 --limit 8
```

If the helper reports `本地资料未找到明确出处`, return that exact sentence and stop.

## Reference

Read `references/resource-map.md` only when you need a quick reminder of searchable locations, ignored file types, or helper usage.
