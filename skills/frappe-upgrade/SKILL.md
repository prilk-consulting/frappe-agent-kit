---
name: frappe-upgrade
description: Frappe migrations, patches, and version upgrades. Use for writing patches.txt entries, schema/data migration patterns, reload_doc and rename_field, idempotent patch design, and the bench migrate/update lifecycle.
---

# Migrations, Patches & Upgrades

## Usage

Use this skill when:

- Writing a patch (data backfill, field rename, cleanup) or editing patches.txt
- Understanding what `bench migrate` runs and in what order
- Planning a major version upgrade (v14 → v15 → v16)
- Recovering from failed patches or wrong app-uninstall order

## What `bench migrate` actually runs (in order)

1. `before_migrate` hooks
2. **`[pre_model_sync]` patches** — run against the OLD schema
3. **Model sync** — DocType JSON files → database schema
4. **`[post_model_sync]` patches** — run against the NEW schema
5. Fixture sync, dashboards, customizations, translations
6. `after_migrate` hooks

This ordering decides where your patch goes: reading/writing fields that the new code REMOVES → pre; backfilling fields the new code ADDS → post.

## patches.txt

```
[pre_model_sync]
myapp.patches.v1_1.capture_legacy_status_before_field_removal

[post_model_sync]
myapp.patches.v1_1.backfill_new_status_field
myapp.patches.v1_2.rename_warehouse_field
```

**All-or-nothing rule:** either every patch line sits under a section header, or the file has NO headers at all (legacy format — everything runs pre-model-sync). A line above the first header makes the parser fall back to legacy mode for the **whole file**, silently turning your `[post_model_sync]` patches into pre-sync ones.

Two more line forms the parser accepts: `execute:frappe.db.set_value(...)` (inline one-liner, no patch file) and a `finally:` prefix (queues the patch to run after all other patches in the run).

Each line is a dotted path to a module with an `execute()` function:

```
myapp/patches/v1_1/backfill_new_status_field.py
```

```python
import frappe

def execute():
    if not frappe.db.has_column("My DocType", "new_status"):
        return  # schema not there yet on this site — nothing to do
    frappe.db.sql("""
        UPDATE `tabMy DocType`
        SET new_status = CASE WHEN docstatus = 1 THEN 'Active' ELSE 'Draft' END
        WHERE new_status IS NULL
    """)
```

### Execution rules

- Each patch runs **once per site**; completed runs are recorded in `tabPatch Log`.
- To force a re-run, change the line text — the convention is appending a comment: `myapp.patches.v1_1.backfill_x #2025-06-01 re-run after fix`. The whole line is the identity.
- To run one patch manually while developing: `bench --site <site> console` → `frappe.get_attr("myapp.patches.v1_1.backfill_x.execute")()`.
- A failing patch **aborts the migrate** — every site downstream is now stuck until the patch is fixed. Never ship a patch you haven't run against a realistic copy of production data.

## Patch toolbox

```python
# Make new/changed doctype meta available inside a pre-sync patch
frappe.reload_doc("mymodule", "doctype", "my_doctype")
frappe.reload_doctype("Sales Invoice")          # shortcut by DocType name

# Rename a field, preserving data (reload_doc FIRST — rename_field silently
# no-ops with just a printed warning if the new field isn't in meta yet)
from frappe.model.utils.rename_field import rename_field
frappe.reload_doc("mymodule", "doctype", "my_doctype")
rename_field("My DocType", "old_fieldname", "new_fieldname")

# Existence guards — make every patch idempotent
frappe.db.table_exists("My DocType")
frappe.db.has_column("My DocType", "fieldname")
frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "my_field"})

# Rename a document / a doctype
frappe.rename_doc("My DocType", "OLD-NAME", "NEW-NAME", force=True)
```

### Idempotency is non-negotiable

A patch can crash halfway and re-run from the top (after the line-comment bump), and it will run on sites in wildly different states — fresh installs, sites that skipped versions, sites where a user already created the data manually. Every patch must:

- Guard on existence (`has_column`, `table_exists`, `frappe.db.exists`) before acting
- Only touch rows that still need the migration (`WHERE new_field IS NULL`)
- Never assume another app is installed — check `"otherapp" in frappe.get_installed_apps()`

### Don't import app business logic

A patch written today runs against next year's codebase. Importing `myapp.services.calculate_totals` into a patch means the patch breaks when that function's signature changes. Inline the logic the patch needs — patches are frozen history, not live code.

### Large tables

```python
def execute():
    names = frappe.get_all("My DocType", filters={"new_field": ("is", "not set")}, pluck="name")
    for i, name in enumerate(names):
        # ... per-row work ...
        if i % 1000 == 0:
            frappe.db.commit()   # checkpoint so a crash doesn't redo everything
```

Committing inside a patch is acceptable (unlike in tests) — but only with idempotent row selection, since a crash now leaves the patch half-applied.

## New DocTypes & schema changes (no patch needed)

Adding fields, doctypes, or changing field properties in the app's own JSON files needs **no patch** — model sync handles it. Patches exist for **data**: backfills, renames, moving values between fields/doctypes, cleanup.

Reaching for `frappe.database.schema.add_column` (or raw `ALTER TABLE`) in a patch is a smell — change the DocType JSON instead and let model sync do it.

## Version upgrades (e.g. v14 → v15)

```bash
bench --site <site> backup --with-files          # ALWAYS first
bench switch-to-branch version-15 frappe erpnext --upgrade
bench setup requirements                          # rebuild env for new deps
bench --site <site> migrate
bench build
```

- Check every third-party app for a compatible branch BEFORE switching — one incompatible app blocks the whole bench.
- Read the framework's release notes for removed APIs; grep your apps for them before, not after.
- Test the full upgrade on a restored copy of the production database. Patch failures on real data (NULLs, legacy rows, cancelled docs) are the norm, not the exception.
- `bench migrate --skip-failing` marks failed patches `skipped=1` and keeps going — skipped patches are **retried on every subsequent migrate** until they succeed. Use it to unblock, then fix the patch. To permanently mark a patch as done without running it: `bench --site <site> bypass-patch <dotted.path>`.
- `bench migrate --skip-fixtures` skips fixture sync — useful when a deploy must not overwrite UI-managed fixture data.

## Uninstalling apps — order matters

```bash
bench --site <site> uninstall-app myapp     # FIRST: removes doctypes, hooks refs, module defs
bench rm myapp                              # THEN remove from apps/ and apps.txt
```

Removing the app directory before `uninstall-app` leaves orphaned DocTypes, broken hook references cached in Redis, and a site that errors on every request. If you got the order wrong, reinstall the app code first, then uninstall properly. (`uninstall-app` calls `frappe.clear_cache()` itself; run `bench --site <site> clear-cache` manually only if you removed things by hand — hook registries are cached per-site in Redis and stale entries keep erroring until cleared.)
