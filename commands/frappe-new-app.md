---
description: Create a new Frappe app with production-grade structure (install.py, custom/ folder, hooks wiring)
argument-hint: "<app_name> [short description]"
---

Create a new Frappe app named from `$ARGUMENTS` and set up the structure used by production apps that extend ERPNext.

## Steps

1. **Generate the app**: run `bench new-app <app_name>` from the bench root. It prompts interactively — if non-interactive generation is needed, pass title/description/publisher via the prompts or ask the user for: App Title, Description, Publisher, Email, License.

2. **Add the extension skeleton** on top of the generated app:

```
apps/<app>/<app>/
├── hooks.py                # generated — wire the lines below into it
├── install.py              # NEW
├── <app>/                  # default module (from modules.txt)
│   ├── custom/             # NEW — doc_events handlers for other apps' DocTypes
│   │   └── __init__.py
│   └── doctype/            # own DocTypes land here
├── shared/                 # NEW — cross-module utilities
│   └── __init__.py
└── public/js/              # client scripts for existing DocTypes
```

3. **install.py**:

```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    create_custom_fields(get_custom_fields())


def after_migrate():
    create_custom_fields(get_custom_fields())


def get_custom_fields():
    """Custom fields this app adds to other apps' DocTypes. This app manages ONLY these."""
    return {}
```

4. **hooks.py** — add (keep the generated header/metadata):

```python
after_install = "<app>.install.after_install"
after_migrate = "<app>.install.after_migrate"

# doc_events = {
#     "Sales Invoice": {"validate": "<app>.<module>.custom.sales_invoice.validate"},
# }
# doctype_js = {"Customer": "public/js/customer.js"}
```

Leave the commented examples in place — they document the app's extension conventions.

5. **Install on a site**: ask which site (check `default_site` in `sites/common_site_config.json`), then `bench --site <site> install-app <app>`.

6. **Verify**: `bench --site <site> list-apps` shows the app; `bench --site <site> migrate` runs clean.

## Rules

- One file per hooked DocType under `custom/`, named after the DocType in snake_case.
- This app only creates/manages its OWN custom fields — never another app's.
- If the app will ship a SPA frontend, scaffold it later with the frappe-frontend skill's canonical structure rather than improvising now.
