"""Narrow temporary convergence-script replacements, then self-delete."""

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
    raise SystemExit(f"temporary route patch target count: {text.count(old)}")
text = text.replace(old, new, 1)

old_escape = r'        markdown=markdown + "\n\nMise à jour concurrente.",' + "\n"
new_escape = r'        markdown=markdown + "\\n\\nMise à jour concurrente.",' + "\n"
if text.count(old_escape) != 1:
    raise SystemExit(f"temporary newline patch target count: {text.count(old_escape)}")
text = text.replace(old_escape, new_escape, 1)

target.write_text(text, encoding="utf-8")
Path(__file__).unlink()
