"""Every startup migration must be lock-light, not just the Information one.

`initialize_composed_schema()` replays all of these on each service start. An
unguarded `ALTER TABLE` takes an ACCESS EXCLUSIVE lock even when it has nothing
to change, and a plain `ADD CONSTRAINT ... CHECK` re-scans the whole table every
time, so a boot can block behind — or block — live traffic.

`test_projection_startup_migration_remains_lock_light` already asserted this for
`information_projection` alone. Scoping the rule to one module let the next
migration reintroduce eight unguarded statements. This asserts it for the whole
startup set, discovered from the initializer rather than listed.

Guarded schema evolution stays allowed: an `ALTER TABLE` inside a `DO $$ ... $$`
block that first checks the catalog performs catalog reads only once applied.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPOSED = ROOT / "mvp_vertical" / "cockpit_composed.py"


def _startup_migration_modules() -> list[str]:
    """Modules whose MIGRATION the composed initializer replays on every boot."""
    tree = ast.parse(COMPOSED.read_text(encoding="utf-8"))
    initializer = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "initialize_composed_schema"
    )
    modules = [
        node.value.id
        for node in ast.walk(initializer)
        if isinstance(node, ast.Attribute)
        and node.attr == "MIGRATION"
        and isinstance(node.value, ast.Name)
    ]
    assert modules, "no startup migrations discovered in initialize_composed_schema"
    return modules


def _migration_path(module_name: str) -> Path:
    module = __import__(f"mvp_vertical.{module_name}", fromlist=["MIGRATION"])
    return Path(module.MIGRATION)


def _strip_guarded_blocks(sql: str) -> str:
    """Remove DO $$ ... $$ blocks: their ALTERs run only when the catalog says so."""
    return re.sub(r"DO\s*\$\$.*?\$\$\s*;", "", sql, flags=re.DOTALL | re.IGNORECASE)


@pytest.mark.parametrize("module_name", _startup_migration_modules())
def test_startup_migration_has_no_unguarded_alter_table(module_name: str) -> None:
    sql = _migration_path(module_name).read_text(encoding="utf-8")
    unguarded = _strip_guarded_blocks(sql)

    offenders = [
        line.strip()
        for line in unguarded.splitlines()
        if line.strip().upper().startswith("ALTER TABLE")
    ]
    assert not offenders, (
        f"{module_name}: unguarded ALTER TABLE in a migration replayed on every "
        f"start. Wrap it in a DO $$ block that checks the catalog first:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("module_name", _startup_migration_modules())
def test_startup_migration_adds_no_validating_check_constraint(module_name: str) -> None:
    """A validating CHECK re-scans the table; guarded or NOT VALID, never bare."""
    sql = _strip_guarded_blocks(_migration_path(module_name).read_text(encoding="utf-8"))
    bare = re.findall(
        r"ADD\s+CONSTRAINT\s+\S+\s+CHECK\s*\((?:[^()]|\([^()]*\))*\)\s*;",
        sql,
        flags=re.IGNORECASE,
    )
    assert not bare, f"{module_name}: unguarded validating CHECK constraint: {bare}"


def test_the_guard_recognizes_a_guarded_alter() -> None:
    """The rule must accept the guarded form, or it just bans schema evolution."""
    guarded = """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'x') THEN
            ALTER TABLE t ADD CONSTRAINT x CHECK (c IN (1, 2));
        END IF;
    END;
    $$;
    """
    assert "ALTER TABLE" not in _strip_guarded_blocks(guarded).upper()

    bare = "ALTER TABLE t ADD COLUMN c TEXT;"
    assert "ALTER TABLE" in _strip_guarded_blocks(bare).upper()
