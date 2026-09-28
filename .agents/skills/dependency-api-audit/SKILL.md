---
name: dependency-api-audit
description: "Use when checking whether this project uses current package APIs, imports, models, or dependency versions; auditing deprecated HeroUI/Next.js usage; upgrading frontend or backend dependencies; or validating a dependency-related change."
user-invocable: true
---

# Dependency and API Audit

Run the deterministic audit first. It produces the smallest useful output and avoids broad codebase inspection:

```powershell
.\.agents\skills\dependency-api-audit\scripts\audit-project.ps1
```

To update package versions and apply safe legacy HeroUI import replacements for a fresh clone, run:

```powershell
.\.agents\skills\dependency-api-audit\scripts\update-modules.ps1
```

This updates the frontend lockfile and the active Python environment, then reruns the audit. It intentionally does not rewrite semantic component migrations such as `CardBody` to `Card.Content`; those require a focused code change and build check.

The audit checks:

- deprecated HeroUI and Next.js imports/component APIs in `frontend/`
- frontend dependency freshness with `npm outdated`
- the production Next.js build
- backend Python compilation
- installed Python dependency consistency with `pip check`

## Triage Rules

1. Fix reported deprecated imports or API patterns before changing behavior.
2. Treat `npm outdated` and network failures as informational unless the task explicitly requests upgrades.
3. Read the installed package typings or local package documentation only for a reported API mismatch.
4. After a fix, rerun the same audit. Do not perform a broad repository reread.
5. Do not upgrade packages automatically. Check the changelog and run the build before changing version ranges.

## Manual Targeted Checks

For a specific library, inspect the installed package rather than relying on model memory:

```powershell
Push-Location frontend
npm ls <package-name>
Get-ChildItem node_modules\<package-name> -Recurse -Include *.d.ts,README.md | Select-Object -First 20
Pop-Location
```

For backend packages:

```powershell
Push-Location backend
python -m pip show <package-name>
Pop-Location
```

The source of truth is the installed package version and its local types/docs, followed by a focused build or import check.
