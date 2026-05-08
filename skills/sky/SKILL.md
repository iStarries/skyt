---
name: sky
description: Use only when the user explicitly invokes `$sky` in the current sky-take-out project to answer learning questions from local course materials or source code. Do not use implicitly for mentions of 苍穹外卖, day01, interfaces, SQL, class names, module names, or repository files without the explicit `$sky` trigger.
---

# Sky

Answer sky-take-out course questions from local materials only. This skill is project-specific and must not be used unless the user explicitly includes `$sky`.

## Workflow

1. Parse the user question for `dayXX`, module name, class name, interface name, SQL keyword, or learning point.
2. If the question has neither `dayXX` nor a module name, ask which day or module the user is studying. Do not search the whole repository.
3. Search local materials first. Use `scripts/find_sky_materials.py` with the parsed query and day/module scope.
4. Answer with the source first, then the explanation.
5. If no clear local source is found, answer exactly:

```text
本地资料未找到明确出处
```

Do not add general knowledge, guesses, or web-derived content after that sentence.

## Source Format

Start every substantive answer with one concise source line:

```text
出处：day01 / 讲义 / 苍穹外卖-day01.md
出处：源码 / DishController.java
出处：day02 / 接口文档 / 苍穹外卖-管理端接口.html
```

Use the script's `出处：...` label when available. Keep the source line short; put extra path details only if the user asks.

## Search Scope

Search only these local materials:

- `讲义/dayXX/*.md`
- `资料/dayXX/**/*.md`
- `资料/dayXX/**/*.html`
- `资料/dayXX/**/*.json`
- `资料/dayXX/**/*.sql`
- `sky-take-out/**/*.java`
- top-level `Readme.md`

Ignore PPT, images, Excel files, and unrelated generated output.

## Retrieval Command

Run the helper from the project root:

```powershell
py skills\sky\scripts\find_sky_materials.py "day02 新增员工接口在哪里" --day day02 --limit 8
```

For a module-scoped question without a day:

```powershell
py skills\sky\scripts\find_sky_materials.py "员工管理 新增员工接口" --module "员工管理" --limit 8
```

If the script reports `本地资料未找到明确出处`, return that exact sentence and stop.

## Reference

Read `references/resource-map.md` only when you need a quick reminder of searchable locations, ignored file types, or script usage.
