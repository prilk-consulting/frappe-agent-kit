# Frappe Agent Kit — Roadmap

A layer-by-layer buildout plan to take frappe-kit from a focused skill+agent pack to a
comprehensive Frappe development platform, modeled on the most mature framework plugin in
the ecosystem (claude-seo: 25 skills, 18 agents, 30 shared scripts, 90 reference files,
39 tests).

**Guiding principle:** the differentiator is not skill *count* — it's the **deterministic
script layer**. Skills should stay thin and orchestrate scripts that actually validate,
generate, and inspect. A skill that says "create a DocType like this" is commodity; a
script that *rejects an invalid DocType JSON before migrate* is not. Build the toolbelt
first; let skills wrap it.

**Non-goals (deliberate, see why inline):**
- No telemetry/phone-home hooks (community trust).
- No bundled MCP server in core (that lane is crowded; if ever, ship as an opt-in extension).
- No third-party-repo content copied; gotchas are written from framework source + experience.

---

## Current state (v0.2.0)

| Layer | Have |
|-------|------|
| Skills | 9 — frappe-dev, frappe-test, frappe-portal, frappe-fixtures, frappe-upgrade, frappe-frontend, frappe-audit, add-portal-page, add-custom-field |
| Agents | 4 — frappe-dev (builder), frappe-security, frappe-schema, frappe-quality (auditors) |
| Commands | 2 — frappe-new-app, frappe-new-doctype |
| Scripts | 3 — resolve_hooks.py, validate_doctype_json.py, sort_nested_fixtures.py |
| References | 1 — jinja-and-print-formats.md |
| Multi-assistant | .claude-plugin / .cursor-plugin / .codex-plugin |
| CI | claudelint + plugin validate --strict + script smoke tests |
| Docs | README, CHANGELOG, sample-audit-report.md |
| Proven | /frappe-audit run natively end-to-end on a production app |

---

## The 9 layers, mapped to deliverables

### Layer 1 — Orchestrator / router skill
**Gap:** no top-level entry skill. claude-seo's `seo` skill is a routing table + global rules.

- [ ] `skills/frappe/SKILL.md` — a `frappe` router: task→skill routing table, "run triage first"
      step, cross-skill workflows (new feature = doctype + api + test), global conventions.
- [ ] Bench/project triage built in: detect bench vs Frappe Manager vs standalone app repo,
      Frappe version, installed apps, dev tooling — so downstream skills apply correctly.

### Layer 2 — Skill ↔ agent pairing
**Gap:** only the 3 auditors are agents. Build skills don't have parallel-execution agents.

- [ ] Pair the heavy skills with same-named agents where parallel/isolated execution helps
      (e.g. a `frappe-migrator` agent for large patch runs, a `frappe-frontend` builder agent).
- [ ] Each agent: pin `model`, `maxTurns`, `tools`/`disallowedTools`, `skills:` preload.

### Layer 3 — Shared script toolbelt  ⭐ HIGHEST LEVERAGE
**Gap:** 3 scripts vs claude-seo's 30. This is the "does things vs advises" line.

**Validators** (extend the pattern we started):
- [x] `validate_doctype_json.py` (frappe-dev)
- [x] `resolve_hooks.py` (frappe-audit)
- [x] `sort_nested_fixtures.py` (frappe-fixtures)
- [ ] `validate_fixtures.py` — schema-check fixture files; flag unfiltered exports, nested-set
      order, per-environment link IDs.
- [ ] `validate_permissions.py` — read DocType JSON perms; flag missing roles, everyone-can-delete,
      submittable-without-cancel, custom roles that duplicate built-ins.
- [ ] `validate_app.py` — orchestrate all validators over a whole app; one pre-release exit code.

**Generators** (scaffold from templates — needs Layer 5):
- [ ] `gen_doctype_json.py` — emit a valid DocType JSON from flags (name/module/flags/fields);
      output passes validate_doctype_json by construction.
- [ ] `gen_custom_field_block.py` — emit an install.py `get_custom_fields()` block.
- [ ] `gen_test_stub.py` — emit a FrappeTestCase/IntegrationTestCase skeleton for a doctype.
- [ ] `gen_portal_page.py` — emit controller get_list_context + hooks entries + row/detail templates.

**Inspectors** (read-only analysis of app source):
- [ ] `list_whitelisted.py` — every @frappe.whitelist + whether it has a has_permission check
      + allow_guest flag. (Feeds the security agent; also useful standalone.)
- [ ] `map_doc_events.py` — all doc_events + scheduler_events handlers and their resolved targets.
- [ ] `find_untranslated.py` — user-facing strings missing _() / __().

**Bench-aware** (shell into a live bench — document the env-python requirement):
- [ ] `triage_bench.py` — detect bench layout, Frappe version, installed apps, dev tooling
      (powers Layer 1 triage).
- [ ] `diff_fixtures.py` — fixtures on disk vs DB, so you know what an export would change.

> Each script: stdlib-only where possible, clear exit codes (0 ok / 1 bad input / N findings),
> `--help`, and a CI smoke test. Skills reference them by relative path.

### Layer 4 — Progressive disclosure via references/
**Gap:** 1 reference file vs 90. Skills should stay <500 lines; depth moves to references/.

- [ ] Split long skills: frappe-dev (permissions deep-dive, qb cookbook), frappe-upgrade
      (patch recipes), frappe-frontend (react vs vue full guides) → `references/*.md`.
- [ ] New reference content for new skills (Layer 6).

### Layer 5 — Shared data / templates
**Gap:** none yet. claude-seo ships `schema/templates.json`.

- [ ] `templates/doctype/` — canonical DocType JSON templates: submittable, child, single,
      tree, naming-series, dynamic-link variants. Consumed by gen_doctype_json.py and the
      /frappe-new-doctype command (deterministic scaffolds even with no sibling to copy).
- [ ] `templates/app-skeleton/` — install.py, custom/ folder, hooks wiring stubs for /frappe-new-app.

### Layer 6 — More content skills (breadth)
**Gap:** missing surfaces both competitors cover.

- [ ] `frappe-server-scripts` — UI-managed Server Scripts: RestrictedPython sandbox (no imports),
      "Before Save"=validate hook mapping, server_script_enabled flag. (Written from source.)
- [ ] `frappe-workflow` — Workflow DocType states/transitions/actions, workflow_state field.
- [ ] `frappe-reports` — Query Reports (SQL), Script Reports (Python+JS), filters, prepared reports.
- [ ] (stretch) `frappe-integrations` — Webhook DocType, Integration Request patterns, OAuth.
- [ ] More task skills (Expo style): `add-doc-event`, `add-scheduled-job`, `add-report`.

### Layer 7 — Tests
**Gap:** CI runs validators but no test suite asserting kit integrity.

- [ ] `test_manifest_consistency.py` — version matches across plugin.json / .cursor / .codex /
      CHANGELOG (claude-seo's exact guard).
- [ ] `test_skill_script_refs.py` — every `scripts/x.py` a skill mentions actually exists.
- [ ] `test_scripts.py` — unit tests for each toolbelt script (valid/invalid fixtures).
- [ ] Wire all into the existing .github/workflows/validate.yml.

### Layer 8 — Docs
**Gap:** README + sample report only.

- [ ] `docs/ARCHITECTURE.md` — the 9-layer model, skill/agent/script relationships.
- [ ] `docs/INSTALLATION.md` — Claude Code / Cursor / Codex, the /reload-plugins gotcha.
- [ ] `docs/COMMANDS.md` — every skill/command/script with usage + exit codes.
- [ ] `docs/CONTRIBUTING.md` — how to add a skill/script, the "write gotchas from source" rule,
      the no-copied-content rule.

### Layer 9 — Repo furniture & distribution
**Gap:** minor.

- [ ] `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`.
- [ ] `screenshots/` + a demo GIF of /frappe-audit running.
- [ ] `requirements.txt` only if any script needs non-stdlib deps (prefer stdlib to avoid it).
- [ ] Submit to ecosystem indexers (claude-plugins.dev, agentskills) once Layer 6 lands.
- [ ] Frappe Forum announcement — lead with the source-verification + native-audit proof.

---

## Suggested sequencing

1. **v0.3 — Script toolbelt** (Layer 3 validators + inspectors) + Layer 7 manifest/ref tests.
   The leverage release: turns advice into enforcement. Wire new scripts into existing skills/agents.
2. **v0.4 — Generators + templates** (Layer 3 generators + Layer 5) + the router/triage skill (Layer 1).
   Makes scaffolding deterministic; /frappe-new-* commands stop relying on "find a sibling".
3. **v0.5 — Breadth** (Layer 6 content skills + paired agents Layer 2) + references split (Layer 4).
4. **v1.0 — Polish** (Layer 8 docs, Layer 9 furniture, demo GIF, indexers, forum launch).

## Maintenance commitments (every Frappe minor release)

- Re-run the agent fact-check pass over all skills against the new framework source.
- Bump version across all manifests + CHANGELOG (enforced by test_manifest_consistency).
- Update version-specific notes (deprecations, renamed APIs).

## Definition of "comprehensive" (the v1.0 bar)

- Every Frappe development surface has a skill.
- Every common mistake has a script that *catches* it, not just a paragraph warning about it.
- A new user can install, scaffold a correct app, and audit it — entirely through the kit.
- Every claim is source-verified; every script is tested in CI.
