## Plan: Auto-tagging + cron deactivation of stale DT projects

Two coordinated additions to the Dependency-Track tooling:

1. **Auto-tagging** — every project gets four canonical, prefixed tags whenever it's created/updated by this tool: `name:<normalized>`, `version:<normalized>`, `parent:<normalized>` (when applicable), and `lifecycle:<alpha|beta|dev|preview|rc|GA>` derived from the version string. Same logic powers a one-off remediation CLI to back-fill existing projects.
2. **Stale deactivation** — a daily cron workflow marks active projects inactive. Leaf projects are stale when `lastBomImport` is older than 15 days **or null** (never imported). Collection-parent projects (and any project with active children) are protected regardless of age. `lifecycle:GA` and `keep-active` tags protect any project.

**Tagging rules** (single source of truth: `src/services/tagging.py`)
- `name:<n>` — `n = name.lower().replace("-", "_")`.
- `version:<v>` — `v = version.lower().replace("-", "_")` (only when version is set).
- `parent:<p>` — `p = parent_name.lower().replace("-", "_")` (only when project has a parent).
- `lifecycle:<token>` — case-insensitive substring scan over the version string, first-match wins in this order: `alpha`, `beta`, `dev`, `preview`, `rc`. No match (or no version) → `lifecycle:GA`.
- Constants: `LIFECYCLE_PREFIXES = ("alpha", "beta", "dev", "preview", "rc")`, `GA_TAG = "lifecycle:GA"`.
- Pure helper signature: `compute_auto_tags(name: str, version: Optional[str], parent_name: Optional[str]) -> list[str]`.
- A second helper `merge_auto_tags(existing: list[str], auto: list[str]) -> list[str]` performs deduplication and lifecycle replacement: strip any existing `lifecycle:*`, `name:*`, `version:*`, `parent:*` and re-add the freshly computed ones; preserve every other tag.

**Stale deactivation logic** (`src/services/stale_projects.py` + `src/cli/commands.py`)
- `is_stale` skip conditions (leaf projects only): already inactive · tags contain `lifecycle:GA` **or** `keep-active` · `lastBomImport` set and age ≤ threshold. **`isLatest=true` and `null lastBomImport` are NOT protected** — a never-imported project is always stale.
- Before deactivating any project (leaf or parent), `get_project_children` is called; projects with active children are skipped (`has_active_children`) — this prevents DT's 409.
- Two-pass deactivation: **pass 1** — leaf/NONE-logic projects that pass `is_stale` and have no active children; **pass 2** — collection parents with no active children (staleness check skipped for parents).
- Deactivation uses GET-then-PATCH: fetch full project payload, set `active=false`, PATCH — avoids 409 from partial-body rejection.
- 2-second pause between write operations to avoid overloading the API server.

**Phases & Steps**

Phase A — Pure tagging helper (no deps, easy to test)
1. New module `src/services/tagging.py` exposing `compute_auto_tags`, `merge_auto_tags`, and the lifecycle constants.
2. New tests in `tests/test_tagging.py` covering: GA fallback, each lifecycle token (alpha/beta/dev/preview/rc), version with multiple keywords (first-match wins), null version, parent vs no parent, dash normalization, idempotent merge (no duplicates), lifecycle replacement on re-run.

Phase B — Auto-tag on upload (depends on A)
3. Extend `Project` dataclass in `src/domain/models.py` with optional non-API field `parent_name: Optional[str] = None` (excluded from `to_api_dict`).
4. In `src/services/project.py` `ProjectService.create_project`, just before the existing existence check, call `merge_auto_tags(project.tags, compute_auto_tags(project.name, project.version, project.parent_name))` and assign back to `project.tags`. This covers create AND update paths since both flow through this method.
5. Update the three `Project(...)` construction sites in `src/services/sbom.py` (lines ~285, ~313, ~458) to pass `parent_name=` where a parent exists. Also check `src/sbom_uploader/{singular,list,nested,directory}.py` for any direct `Project(...)` construction and pass `parent_name` there too.

Phase C — Stale deactivation service layer (parallel with B)
6. In `src/services/project.py`: add `list_projects(exclude_inactive=True)` (paginated wrapper around `GET /project`), extract a public `get_project_children(uuid)` from `_get_single_project_hierarchy`, and add `deactivate_project(uuid)` which GETs the full project payload, sets `active=false`, and PATCHes (honors `dry_run`).

Phase D — Staleness decision module (depends on A & C)
7. New `src/services/stale_projects.py` exposing `STALE_THRESHOLD_DAYS = 15`, `is_stale(project, now_ms, threshold_days) -> (bool, skip_reason)`, `partition_by_collection(projects)`, and `build_summary(...)`. Tag checks look for both `lifecycle:GA` and `keep-active` in the project's tags list (raw DT tag dicts → `{t["name"] for t in project.get("tags", [])}`).
8. Tests in `tests/test_stale_projects.py` for the full decision matrix.

Phase E — CLI commands (depends on B & D)
9. In `src/cli/commands.py`:
   - `deactivate-stale` with `--days` (default 15), `--dry-run`. Runs the two-pass logic and emits JSON summary + `GITHUB_STEP_SUMMARY` block.
   - `retag-projects` with `--dry-run`. Lists ALL projects (including inactive), and for each computes desired auto-tags, merges with existing tags via `merge_auto_tags` (which strips old `lifecycle:*`, `name:*`, `version:*`, `parent:*` before re-adding fresh ones — preserves everything else). PATCHes only when the tag set actually differs. Parent name resolved from `project.get("parent", {}).get("name")` returned by the list endpoint, or via a follow-up GET if absent.

Phase F — GitHub workflows (depends on E)
10. New `.github/workflows/deactivate-stale-projects.yaml`:
    - `on.schedule: "0 2 * * *"` + `on.workflow_dispatch` with `dry-run` boolean input (default false).
    - `permissions: contents: read`, `concurrency: group: deactivate-stale, cancel-in-progress: false`.
    - Steps: checkout, setup Python 3.13, `pip install -r requirements.txt`, `python3 src/main.py deactivate-stale` with `INPUT_URL`/`INPUT_API_KEY` from secrets and `INPUT_DRY_RUN` from the dispatch input.
11. New `.github/workflows/retag-projects.yaml`:
    - `on.workflow_dispatch` only (one-off remediation), with `dry-run` input (default true for safety).
    - Otherwise identical structure to the deactivation workflow; runs `python3 src/main.py retag-projects`.

Phase G — Docs (minimal)
12. Brief note in `README.md` describing the two new commands and the workflow_dispatch entry point for retagging. (No new docs files per repo convention.)

**Relevant files**
- `src/services/tagging.py` — **new**: pure helpers (`compute_auto_tags`, `merge_auto_tags`, lifecycle constants).
- `src/services/stale_projects.py` — **new**: pure decision helpers.
- `src/services/project.py` — extend with `list_projects`, `get_project_children`, `deactivate_project`; inject auto-tag merge at start of `create_project` (line ~58).
- `src/domain/models.py` — add `parent_name: Optional[str] = None` to `Project` (line ~94), keep it out of `to_api_dict`.
- `src/services/sbom.py` — pass `parent_name` at the three `Project(...)` construction sites (~285, ~313, ~458).
- `src/sbom_uploader/{singular,list,nested,directory}.py` — pass `parent_name` wherever `Project(...)` is constructed (verify during impl).
- `src/cli/commands.py` — add `deactivate-stale` and `retag-projects` commands; reuse `@with_services()` decorator.
- `.github/workflows/deactivate-stale-projects.yaml` — **new** cron + dispatch.
- `.github/workflows/retag-projects.yaml` — **new** dispatch only.
- `tests/test_tagging.py` — **new**.
- `tests/test_stale_projects.py` — **new**.
- `README.md` — append short usage section.

**Verification**
1. `pytest tests/test_tagging.py tests/test_stale_projects.py` — all unit cases pass.
2. Against local DT (`tests/docker/docker-compose.yml`):
   - Upload `tests/single_sbom/nginx_12.9.1.json` and verify the resulting project carries `name:nginx`, `version:12.9.1`, `lifecycle:GA`.
   - Upload one with a `*-rc.1` version and verify `lifecycle:rc`.
   - Upload a nested hierarchy and verify children carry `parent:<normalized>` and the parent does not.
3. Seed a project with stale `lastBomImport` plus `lifecycle:GA`, run `python3 src/main.py deactivate-stale --dry-run` — it must be reported as skipped (reason: GA). Remove the tag, rerun, and confirm it is now reported as stale.
4. Manually clear tags on an existing project, run `python3 src/main.py retag-projects --dry-run`, verify the diff shows the expected four tags added.
5. Re-run `retag-projects` without `--dry-run`; a third invocation must report zero changes (idempotency).
6. `actionlint .github/workflows/deactivate-stale-projects.yaml .github/workflows/retag-projects.yaml`.

**Decisions**
- Tag format: prefixed (`name:`, `version:`, `parent:`, `lifecycle:`) to avoid collisions with arbitrary user tags.
- Tag value normalization: `.lower().replace("-", "_")` for name/version/parent — matches existing `file_discovery.py` convention.
- Lifecycle keywords: `alpha`, `beta`, `dev`, `preview`, `rc`. First-match wins in that order. Default → `GA`.
- Retag scope: preserve arbitrary user tags; only the four managed prefixes (`name:`, `version:`, `parent:`, `lifecycle:`) are replaced.
- Auto-tagging is applied inside `ProjectService.create_project`, so it runs for both new projects and updates of existing ones (back-fills tags on every upload).
- Stale deactivation skip list: `lifecycle:GA` **OR** `keep-active` tag, active children present. `isLatest=true` is **not** protected. `null lastBomImport` is **not** protected (treated as infinitely old → stale).
- Schedule: deactivation daily `0 2 * * *` UTC. Retag: manual dispatch only (one-off remediation; ongoing tagging happens at upload time).

**Further Considerations**
1. **Secret names** — what are the existing repo-level secret names for the DT URL and API key? (`DT_URL`/`DT_API_KEY` vs. `DEPENDENCY_TRACK_URL`/`DEPENDENCY_TRACK_API_KEY` vs. something else)
2. **API key permissions** — reuse the upload key (must hold `PORTFOLIO_MANAGEMENT`) or use a dedicated maintenance key?
3. **Edge case `dev-preview`** — version `1.0.0-dev-preview` will land on `lifecycle:dev` under the chosen precedence. Confirm that's intended (vs. `preview`).
4. **Notifications** — should the deactivation workflow post to Slack / open an issue when projects are deactivated, or is the run log sufficient?
