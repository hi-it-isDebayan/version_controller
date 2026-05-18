import re
from typing import Any, Optional


def parse_toon_entry(line: str) -> dict:
    """
    Parse a single object-level TOON line(s) into a dict.
    Handles simple 'key: value' pairs.
    """
    fields = {}
    line = line.strip()
    if not line:
        return fields
    for part in line.split(" "):
        if ":" in part:
            key, _, val = part.partition(":")
            key = key.strip()
            val = val.strip()
            if key:
                fields[key] = _parse_value(val)
    return fields


def _parse_value(token: str) -> Any:
    token = token.strip()
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if _is_numeric(token):
        try:
            if "." in token:
                return float(token)
            return int(token)
        except ValueError:
            return token
    if token.startswith('"') and token.endswith('"'):
        return _unescape(token[1:-1])
    return token


def _is_numeric(s: str) -> bool:
    return bool(re.match(r'^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$', s))


def _unescape(s: str) -> str:
    return (
        s.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def parse_toon(content: str) -> Any:
    """
    Parse a full TOON document into a Python value.
    Handles objects, arrays, nested structures.
    """
    if not content or not content.strip():
        return {}
    lines = content.split("\n")
    return _parse_lines(lines, 0, len(lines))[0]


def _parse_lines(lines: list, start: int, end: int, indent_size: int = 2) -> tuple:
    """
    Parse a block of lines at a given indentation level.
    Returns (value, next_line_index).
    """
    if start >= end:
        return None, start

    stripped = lines[start].strip()
    if not stripped:
        return None, start + 1

    indent = _get_indent(lines[start])
    result = {}
    array_items = None
    array_key = None
    i = start

    # Check for array header: key[N]...: or [N]...:
    header_match = _parse_array_header(lines[start], indent, indent_size)
    if header_match:
        key, n, delimiter, has_fields, fields = header_match
        result, i = _parse_array_body(lines, start, end, n, delimiter, has_fields, fields, indent_size)
        return result, i

    while i < end:
        line = lines[i]
        stripped_line = line.strip()
        if not stripped_line or _get_indent(line) < indent:
            break

        current_indent = _get_indent(line)
        if current_indent != indent:
            if current_indent > indent or stripped_line.startswith("- "):
                break
            break

        if stripped_line.startswith("- "):
            if array_items is None:
                array_items = []
            item_val, i = _parse_list_item(lines, i, end, indent, indent_size)
            array_items.append(item_val)
            continue

        colon_pos = _find_colon(stripped_line)
        if colon_pos is None:
            i += 1
            continue

        key = stripped_line[:colon_pos].strip()
        value_str = stripped_line[colon_pos + 1:].strip()

        if not value_str:
            sub_val, i = _parse_lines(lines, i + 1, end, indent + indent_size)
            result[key] = sub_val if sub_val is not None else {}
            continue

        result[key] = _parse_value(value_str)
        i += 1

    if array_items is not None:
        return array_items, i
    return result, i


def _get_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _find_colon(s: str) -> Optional[int]:
    in_quotes = False
    for idx, ch in enumerate(s):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ":" and not in_quotes:
            return idx
    return None


def _parse_array_header(line: str, line_indent: int, indent_size: int) -> Optional[tuple]:
    stripped = line.strip()
    colon_pos = _find_colon(stripped)
    if colon_pos is None:
        return None

    header_part = stripped[:colon_pos].strip()
    bracket_start = header_part.find("[")
    if bracket_start == -1:
        return None

    bracket_end = header_part.find("]", bracket_start)
    if bracket_end == -1:
        return None

    bracket_content = header_part[bracket_start + 1:bracket_end]
    n_str = ""
    delimiter = ","
    for ch in bracket_content:
        if ch.isdigit():
            n_str += ch
        elif ch == "\t":
            delimiter = "\t"
        elif ch == "|":
            delimiter = "|"
    if not n_str:
        return None
    n = int(n_str)

    key_part = header_part[:bracket_start].strip()
    after_bracket = header_part[bracket_end + 1:].strip()

    has_fields = False
    fields = []
    if after_bracket.startswith("{"):
        brace_end = after_bracket.find("}")
        if brace_end != -1:
            fields_str = after_bracket[1:brace_end]
            fields = [f.strip() for f in fields_str.split(delimiter)]
            has_fields = True

    return key_part, n, delimiter, has_fields, fields


def _parse_array_body(
    lines: list, start: int, end: int,
    n: int, delimiter: str, has_fields: bool, fields: list,
    indent_size: int
) -> tuple:
    line = lines[start]
    indent = _get_indent(line)
    colon_pos = _find_colon(line.strip())
    after_colon = line.strip()[colon_pos + 1:].strip() if colon_pos is not None else ""

    # Inline primitive array: key[N]: v1,v2,...
    if after_colon and not has_fields:
        values = [v.strip() for v in after_colon.split(delimiter)]
        return values, start + 1

    # Tabular or expanded
    result = []
    i = start + 1
    row_indent = indent + indent_size

    while i < end and _get_indent(lines[i]) >= row_indent and lines[i].strip():
        line = lines[i]
        current_indent = _get_indent(line)
        if current_indent < row_indent:
            break

        stripped = line.strip()

        if has_fields:
            # Tabular row
            cells = [v.strip() for v in stripped.split(delimiter)]
            if len(cells) == len(fields):
                row_obj = {}
                for idx, fname in enumerate(fields):
                    row_obj[fname] = _parse_value(cells[idx]) if cells[idx] else None
                result.append(row_obj)
            i += 1
        elif stripped.startswith("- "):
            item_val, i = _parse_list_item(lines, i, end, indent, indent_size)
            result.append(item_val)
        else:
            break

    return result, i


def _parse_list_item(lines: list, start: int, end: int, parent_indent: int, indent_size: int) -> tuple:
    line = lines[start]
    indent = _get_indent(line)
    stripped = line.strip()

    if not stripped.startswith("- "):
        return None, start + 1

    content = stripped[2:].strip()
    item_indent = indent
    body_indent = indent + indent_size

    # Check if the list item has an inline object field: - key: value
    colon_pos = _find_colon(content)
    if colon_pos is not None:
        key = content[:colon_pos].strip()
        val_str = content[colon_pos + 1:].strip()
        result = {}
        if val_str:
            result[key] = _parse_value(val_str)
        # Collect sibling fields at body_indent on subsequent lines
        i = start + 1
        while i < end:
            next_line = lines[i]
            if not next_line.strip():
                i += 1
                continue
            next_indent = _get_indent(next_line)
            if next_indent != body_indent:
                if next_indent < body_indent:
                    break
                i += 1
                continue
            sub_stripped = next_line.strip()
            sub_colon = _find_colon(sub_stripped)
            if sub_colon is not None:
                sk = sub_stripped[:sub_colon].strip()
                sv = sub_stripped[sub_colon + 1:].strip()
                if sv:
                    result[sk] = _parse_value(sv)
            i += 1
        return result, i

    # Must be a primitive list item
    return _parse_value(content), start + 1
