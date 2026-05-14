# Sky Resource Map

Use this map only after `$sky` is explicitly invoked.

## Local Roots

- Project root: the current backend `sky-take-out` directory containing `pom.xml`, `sky-common`, `sky-pojo`, and `sky-server`.
- Course root: the nearest parent directory containing `讲义`, `资料`, or top-level `Readme.md`.

## Searchable Materials

- `讲义/dayXX/*.md`: day lecture notes.
- `资料/dayXX/**/*.md`: day markdown materials.
- `资料/dayXX/**/*.html`: local interface documents.
- `资料/dayXX/**/*.json`: local interface or configuration data.
- `资料/dayXX/**/*.sql`: local SQL scripts.
- `sky-take-out/**/*.java`: backend source code.
- `Readme.md`: top-level course/project readme.

## Ignored Materials

- PPT and PowerPoint files.
- Images and screenshots.
- Excel and spreadsheet files.
- Build output, IDE metadata, Git internals, and generated dependency folders.

## Answer Rules

- Always start with `出处：...` before explaining.
- Explain only after a clear local source is found.
- If no clear local source is found, answer only `本地资料未找到明确出处`.
- If the user did not provide `dayXX` or a module name, ask for the day/module before searching.

## Helper Usage

Run from the project root:

```powershell
py skills\sky\scripts\find_sky_materials.py "day02 新增员工接口在哪里？" --day day02 --limit 8
py skills\sky\scripts\find_sky_materials.py "员工管理 新增员工接口在哪里？" --module "员工管理" --limit 8
```

Use `--json` when structured output is easier to inspect.
