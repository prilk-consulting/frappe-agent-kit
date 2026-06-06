---
name: frappe-test
description: Writing and running tests for Frappe and ERPNext apps. Use for FrappeTestCase patterns, test_records.json fixtures, test dependencies, permission testing, bench run-tests invocations, and test isolation gotchas.
---

# Testing Frappe Apps

## Usage

Use this skill when:

- Writing unit/integration tests for DocTypes, controllers, or whitelisted methods
- Choosing test base classes and fixtures (test records, dependencies)
- Debugging test isolation problems (leaked records, permission state, naming collisions)
- Setting up `bench run-tests` locally or in CI

## One-time site setup

Tests refuse to run until the site allows them:

```bash
bench --site <site> set-config allow_tests true
```

(CI bypass: when the `CI` environment variable is set, this check is skipped.)

Use a dedicated dev/test site, never a site with data you care about — `before_tests` hooks (ERPNext's wipes and re-runs the setup wizard on some versions) and test records write real rows.

## Running tests

```bash
bench --site <site> run-tests --app myapp                  # whole app
bench --site <site> run-tests --doctype "Sales Invoice"    # one doctype's tests
bench --site <site> run-tests --module myapp.mymodule.doctype.thing.test_thing
bench --site <site> run-tests --module ...test_thing --case TestThing
bench --site <site> run-tests --module ...test_thing --test test_validation_fails
bench --site <site> run-tests --app myapp --failfast       # stop on first failure
bench --site <site> run-tests --app myapp --coverage       # coverage report
```

(Don't use `--skip-test-records` — deprecated; on v16 it exits without running any tests.)

## Writing tests

Test file lives next to the doctype: `doctype/<name>/test_<name>.py`.

```python
import frappe
from frappe.tests import IntegrationTestCase   # v16+
# v15: from frappe.tests.utils import FrappeTestCase  (v16 keeps it as a deprecated alias, removed in v17)

# DocTypes whose test_records must exist before these tests run
EXTRA_TEST_RECORD_DEPENDENCIES = ["Customer", "Item"]   # v16 name
# v15: test_dependencies = ["Customer", "Item"]  (deprecated alias on v16)


class TestMyDocType(IntegrationTestCase):
    def setUp(self):
        self.doc = frappe.get_doc({
            "doctype": "My DocType",
            "title": "Test Record",
            "customer": "_Test Customer",
        }).insert()

    def test_validation_fails_without_customer(self):
        doc = frappe.get_doc({"doctype": "My DocType", "title": "X"})
        self.assertRaises(frappe.ValidationError, doc.insert)

    def test_submit_creates_ledger_entry(self):
        self.doc.submit()
        self.assertTrue(frappe.db.exists("My Ledger", {"voucher": self.doc.name}))
```

`IntegrationTestCase` (v15's `FrappeTestCase`; v16 also adds `UnitTestCase` for tests that don't need the DB) wraps the **class** in a transaction and rolls everything back when the class finishes — individual tests see each other's data, but nothing leaks across classes.

### Useful assertions and helpers

```python
self.assertDocumentEqual({"status": "Open", "qty": 5}, doc)   # compares only given keys

from frappe.tests import change_settings   # v16 canonical path; v15: frappe.tests.utils

@change_settings("System Settings", {"allow_guests_to_upload_files": 1})
def test_guest_upload(self): ...        # setting restored after the test
```

### Testing permissions

```python
def test_user_cannot_read_others_docs(self):
    frappe.set_user("test@example.com")
    self.addCleanup(frappe.set_user, "Administrator")   # ALWAYS reset
    self.assertRaises(frappe.PermissionError,
        frappe.get_doc("My DocType", self.other_users_doc).check_permission, "read")
```

`frappe.set_user()` changes the session user for permission evaluation. Forgetting to reset poisons every test that runs after — use `addCleanup`, not a manual call at the end.

## Test records (fixtures)

`test_records.json` next to the doctype (v16 also accepts `test_records.toml`) provides records auto-created when another test declares the doctype in its dependencies:

```json
[
    {"doctype": "Supplier", "supplier_name": "_Test Supplier", "supplier_group": "_Test Supplier Group"}
]
```

- Prefix names with `_Test ` — the Frappe/ERPNext convention; many core tests filter on it.
- Create programmatically when JSON can't express it: `frappe.tests.utils.make_test_records("Customer")`.
- For records that may already exist: `.insert(ignore_if_duplicate=True)`.

## Isolation rules & gotchas

- **Never call `frappe.db.commit()` in a test** — it breaks the class-level rollback and leaks records into the site. If the code under test commits internally, test it through a higher-level entry point or refactor.
- **`frappe.enqueue` does NOT run your job during tests** — the job is still pushed to Redis, and no worker is consuming it. To exercise a background code path, pass `now=True` (runs inline) or call the task function directly. Don't assert on the effects of a plain `enqueue` — they'll never materialize.
- **`frappe.in_test`** — guard test-hostile behavior in app code (e.g., skip real outbound HTTP) with this flag rather than environment checks. (`frappe.flags.in_test` is the older alias; v16 prefers the module-level `frappe.in_test`.)
- **Scheduler events don't run in tests** — call the task function directly: `from myapp.tasks import daily_cleanup; daily_cleanup()`.
- **Date-dependent logic**: pass dates explicitly into the functions under test instead of relying on `nowdate()` — keeps tests deterministic without freezing time.
- **Naming collisions across runs**: repeated runs against the same site can collide on unique fields in `setUp` inserts. Use `frappe.generate_hash(length=8)` suffixes for uniqueness.
- **Creating DocTypes inside tests needs no `developer_mode`** — the developer-mode check is bypassed when `frappe.in_test` is set, so meta-creating tests run fine on any site.

## CI pattern

```bash
bench --site <site> set-config allow_tests true
bench --site <site> migrate
bench --site <site> run-tests --app myapp --failfast --junit-xml-output report.xml
```

For large suites Frappe core uses `bench --site <site> run-parallel-tests --app <app>` with `--build-number`/`--total-builds` for sharding.
