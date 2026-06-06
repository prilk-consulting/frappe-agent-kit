---
name: frappe-audit
description: Full audit of a Frappe app with parallel specialist delegation. Reviews security (permissions, injection, guest endpoints), schema quality (DocType JSON), and code conventions (hooks, patches, client scripts). Use when the user says audit my app, review this Frappe app, app health check, or pre-release review.
argument-hint: "[app name or path]"
---

# Frappe App Audit

Audit a Frappe app end-to-end by delegating to specialist subagents, then aggregate a prioritized report.

## Usage

Use this skill when:

- User asks to audit, review, or health-check a Frappe app
- Pre-release or pre-handover review of a custom app
- Inheriting an unfamiliar codebase and needing a risk map

## Process

1. **Locate the app**: resolve `[app name]` to `apps/<app>/` in the current bench. If no argument, list apps in `apps/` (minus frappe/erpnext core unless explicitly requested) and ask which to audit.
2. **Inventory** (inline, fast):
   - `hooks.py` — verify every registered handler path resolves by running the bundled script from the bench root: `./env/bin/python <this skill's dir>/scripts/resolve_hooks.py <app>` (exit 3 = broken hooks; each is automatically a High finding)
   - `modules.txt`, `patches.txt` — modules and patch history
   - `**/doctype/*/` — DocType JSON + controllers
   - `public/js/`, `www/`, `templates/` — client and web surface
   - `install.py` / `setup.py` — install/migrate wiring
3. **Delegate to specialist agents** (run in parallel; if subagents are unavailable, run the same checklists inline sequentially):
   - `frappe-security` — permission enforcement, injection, guest surface
   - `frappe-schema` — DocType JSON quality and data-model design
   - `frappe-quality` — code conventions, hooks correctness, patch safety
4. **Verify findings**: drop anything a specialist flagged that doesn't reproduce on a second read of the cited file/line. No speculative findings in the final report.
5. **Aggregate** into `AUDIT-REPORT.md` with severity buckets.

## Report format

```markdown
# Audit: <app> @ <git rev>

## Summary
<3-5 sentences: overall health, the one thing to fix first>

## Critical   <!-- security holes, data-loss risks, migrate-breaking -->
- [ ] <finding> — `file.py:123` — <why it matters> — <fix>

## High       <!-- permission gaps, broken hooks, non-idempotent installs -->
## Medium     <!-- convention violations, missing tests, perf smells -->
## Low        <!-- style, naming, minor cleanups -->
```

Every finding cites `file:line`, states the concrete impact, and proposes the specific fix — not "consider improving."

## Severity guide

| Severity | Examples |
|----------|----------|
| Critical | `allow_guest=True` on state-changing method; f-string SQL with user input; `get_all` in a whitelisted method leaking rows across users; patch that destroys data on re-run |
| High | Whitelisted method without `has_permission` check; `ignore_permissions=True` without justification; hook path that doesn't resolve; `after_install` not idempotent; secrets committed in code |
| Medium | `get_list`/`get_all` confusion in non-leaking spots; missing `queue=` on enqueue; client-side-only validation; untranslated user-facing strings; missing tests for submittable doctypes |
| Low | Naming conventions, file organization, two doctypes' scripts in one JS file, print()-instead-of-log_error |

## Scope discipline

- Audit the app as it is — do NOT edit files during the audit.
- Report only what's actually broken or risky; this is not a rewrite proposal.
- If the app extends other apps' DocTypes, check it only manages its OWN custom fields.
