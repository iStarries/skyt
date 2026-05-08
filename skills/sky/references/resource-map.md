# Sky Resource Map

Use this map only after `$sky` is explicitly invoked.

## Local Roots

- Project root: current `sky-take-out` backend project.
- Course root: nearest parent directory that contains `讲义` or `资料`.

## Searchable Materials

- `讲义/dayXX/*.md`: day lecture notes.
- `资料/dayXX/**/*.md`: day markdown materials.
- `资料/dayXX/**/*.html`: local interface documents.
- `资料/dayXX/**/*.json`: local interface or configuration data.
- `资料/dayXX/**/*.sql`: local SQL scripts.
- `sky-take-out/**/*.java`: backend source code.
- `Readme.md`: top-level project/course readme.

## Ignored Materials

- PPT and PowerPoint files.
- Images and screenshots.
- Excel and spreadsheet files.
- Build output, IDE metadata, and Git internals.

## Answer Rules

- Always start with `出处：...`.
- Explain only after a clear local source is found.
- If no clear local source is found, answer only `本地资料未找到明确出处`.
- If the user did not provide `dayXX` or a module name, ask for the day/module before searching.
