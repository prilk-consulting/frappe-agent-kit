---
name: add-custom-field
description: Step-by-step workflow to add a custom field to another app's DocType (e.g. Customer, Sales Invoice) from your own app, idempotently via install.py. Use when the user asks to add a field to a standard/ERPNext doctype, extend Customer with X, or store extra data on an existing DocType.
---

# Add a Custom Field to Another App's DocType

For adding fields to a DocType **your own app owns**, just edit its JSON (see frappe-dev) — this workflow is for extending DocTypes owned by frappe/erpnext/another app, where editing their JSON is forbidden.

## Usage

Use this skill when:

- "Add a field to Customer / Sales Invoice / Item / …"
- Your app needs to store its own data on a standard DocType
- Reviewing whether a custom field was added the upgrade-safe way

## Steps

### 1. Check it doesn't already exist — and whether a field is even needed

```bash
bench --site <site> execute frappe.client.get_list --kwargs "{'doctype':'Custom Field','filters':{'dt':'Customer'},'fields':['fieldname','label','insert_after','module']}"
```

- Field already there (maybe under another app)? STOP — never manage another app's custom fields.
- Linking records M:N (contact↔customer, address↔supplier)? Use `Contact.links` / Dynamic Link instead of a new field.
- Several related fields? Consider a separate DocType linked back, not five custom fields.

### 2. Define it in your app's `install.py`

Add to the existing `get_custom_fields()` dict (create the install.py wiring if the app lacks it — frappe-dev skill has the full pattern):

```python
def get_custom_fields():
    return {
        "Customer": [
            {
                "fieldname": "<app_prefix>_<name>",   # prefix avoids collisions: "myapp_risk_score"
                "label": "<Label>",
                "fieldtype": "<Type>",                # Link/Select/Check/Currency > Data
                "insert_after": "<existing_fieldname>",  # pick from the target's JSON, not from memory
                "module": "<Your Module>",            # marks ownership
                # "options": "...", "read_only": 1, "depends_on": "eval:...", as needed
            },
        ],
    }
```

Conventions:
- **Prefix the fieldname with your app name** — `dt + fieldname` must be unique site-wide, and unprefixed names collide with future framework fields.
- `insert_after`: open the target DocType's JSON in apps/frappe or apps/erpnext and choose a real neighbor; a wrong value silently appends to the end.
- Set `module` so the field is attributable (and exportable by module filter) to your app.

### 3. Apply without waiting for a migrate

```bash
bench --site <site> execute <app>.install.after_migrate
```

(Works because `after_migrate` calls `create_custom_fields(get_custom_fields())` — idempotent, safe to run repeatedly.)

### 4. Verify

```bash
bench --site <site> execute frappe.get_meta --args "['Customer']" | grep -o '<app_prefix>_<name>'
```

Then open the form in the desk: field appears in the right place, behaves per its flags. If code reads the field, access it with `doc.get("<fieldname>")` — attribute access raises on sites where the app isn't installed yet.

### 5. If the field needs data on existing records

Backfill via a patch (frappe-upgrade skill) — never in `after_migrate` (it would re-run the backfill logic on every migrate).

## Rules

- One owner per field: your app creates, reads, writes, and (on uninstall) removes ONLY its own custom fields.
- Both `after_install` AND `after_migrate` must call `create_custom_fields` — fields must survive fresh installs and migrations alike.
- Property changes to a standard field (hide it, relabel it) use a **Property Setter** through the same install.py pattern — not editing the other app's JSON.
