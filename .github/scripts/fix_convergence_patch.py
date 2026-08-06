"""Narrow one temporary convergence-script replacement, then self-delete."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
target = root / ".github/scripts/apply_a_b_relations_convergence.py"
text = target.read_text(encoding="utf-8")
old = '''    tail = replace_once(
        tail,
        "        )\\n        return {\\n",
        ''' + "'''" + '''        )
        response.status_code = (
            status.HTTP_201_CREATED
            if projection.get("document_link_operation") == "created"
            else status.HTTP_200_OK
        )
        return {
''' + "'''" + ''',
        "dynamic Information link status body",
    )
'''
new = '''    response_boundary = "        )\\n        return {\\n"
    if response_boundary not in tail:
        raise SystemExit("dynamic Information link status body: route boundary missing")
    tail = tail.replace(
        response_boundary,
        ''' + "'''" + '''        )
        response.status_code = (
            status.HTTP_201_CREATED
            if projection.get("document_link_operation") == "created"
            else status.HTTP_200_OK
        )
        return {
''' + "'''" + ''',
        1,
    )
'''
if text.count(old) != 1:
    raise SystemExit(f"temporary patch target count: {text.count(old)}")
target.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink()
