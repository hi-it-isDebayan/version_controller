import re
from typing import Any


_NEEDS_QUOTING_RE = re.compile(
    r'^(true|false|null)$'
    r'|^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$'
    r'|^0\d+$'
    r'|^\-$'
    r'|^-'
)
_DOC_DELIMITER = ","


def _needs_quoting(value: str, active_delim: str = _DOC_DELIMITER) -> bool:
    if not value:
        return True
    if value != value.strip():
        return True
    if _NEEDS_QUOTING_RE.match(value):
        return True
    for ch in (":", '"', "\\", "\n", "\r", "\t", "[", "]", "{", "}", "-"):
        if ch in value:
            return True
    if active_delim in value:
        return True
    return False


def _quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _format_primitive(value: Any, active_delim: str = _DOC_DELIMITER) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(value)
    s = str(value)
    if _needs_quoting(s, active_delim):
        return _quote(s)
    return s


def serialize_value(value: Any, indent: int = 0, depth: int = 0, indent_size: int = 2) -> str:
    prefix = " " * (depth * indent_size)
    if isinstance(value, dict):
        return _serialize_object(value, depth, indent_size)
    elif isinstance(value, list):
        return _serialize_array(value, depth, indent_size)
    else:
        return _format_primitive(value)


def _serialize_object(obj: dict, depth: int = 0, indent_size: int = 2) -> str:
    if not obj:
        return ""
    prefix = " " * (depth * indent_size)
    lines = []
    for key, val in obj.items():
        k = _format_primitive(key, _DOC_DELIMITER)
        if isinstance(val, dict):
            if not val:
                lines.append(f"{prefix}{k}:")
            else:
                lines.append(f"{prefix}{k}:")
                lines.append(_serialize_object(val, depth + 1, indent_size))
        elif isinstance(val, list):
            arr_str = _serialize_array(val, depth, indent_size, key)
            lines.append(arr_str)
        else:
            v = _format_primitive(val, _DOC_DELIMITER)
            lines.append(f"{prefix}{k}: {v}")
    return "\n".join(lines)


def _serialize_array(arr: list, depth: int = 0, indent_size: int = 2, key: str = None) -> str:
    prefix = " " * (depth * indent_size)
    n = len(arr)

    if n == 0:
        if key:
            return f"{prefix}{_format_primitive(key)}[0]:"
        return f"{prefix}[0]:"

    all_obj = all(isinstance(x, dict) for x in arr)
    all_prim = all(not isinstance(x, (dict, list)) for x in arr)

    if all_obj:
        keysets = [set(x.keys()) for x in arr]
        uniform = all(ks == keysets[0] for ks in keysets)
        all_prim_vals = all(
            not isinstance(v, (dict, list)) for obj in arr for v in obj.values()
        )
        if uniform and all_prim_vals:
            return _tabular_array(arr, keysets[0], depth, indent_size, key)
        else:
            return _expanded_array(arr, depth, indent_size, key)
    elif all_prim:
        return _inline_array(arr, depth, indent_size, key)
    else:
        return _expanded_array(arr, depth, indent_size, key)


def _inline_array(arr: list, depth: int = 0, indent_size: int = 2, key: str = None) -> str:
    prefix = " " * (depth * indent_size)
    k = _format_primitive(key) if key else ""
    values = [_format_primitive(v, ",") for v in arr]
    return f"{prefix}{k}[{len(arr)}]: {','.join(values)}"


def _tabular_array(arr: list, fields: set, depth: int = 0, indent_size: int = 2, key: str = None) -> str:
    prefix = " " * (depth * indent_size)
    k = _format_primitive(key) if key else ""
    field_names = list(arr[0].keys())
    f_list = ",".join(field_names)
    lines = [f"{prefix}{k}[{len(arr)}]{{{f_list}}}:"]
    row_prefix = " " * ((depth + 1) * indent_size)
    for obj in arr:
        vals = []
        for fname in field_names:
            v = obj.get(fname, "")
            vals.append(_format_primitive(v, ","))
        lines.append(f"{row_prefix}{','.join(vals)}")
    return "\n".join(lines)


def _expanded_array(arr: list, depth: int = 0, indent_size: int = 2, key: str = None) -> str:
    prefix = " " * (depth * indent_size)
    k = _format_primitive(key) if key else ""
    lines = [f"{prefix}{k}[{len(arr)}]:"]
    for item in arr:
        item_prefix = " " * ((depth + 1) * indent_size)
        if isinstance(item, dict):
            first = True
            for fk, fv in item.items():
                kk = _format_primitive(fk, _DOC_DELIMITER)
                if first:
                    if isinstance(fv, (dict, list)):
                        lines.append(f"{item_prefix}- {kk}:")
                        sub = serialize_value(fv, indent=0, depth=depth + 2, indent_size=indent_size)
                        if sub:
                            lines.append(sub)
                    else:
                        vv = _format_primitive(fv, _DOC_DELIMITER)
                        lines.append(f"{item_prefix}- {kk}: {vv}")
                    first = False
                else:
                    if isinstance(fv, (dict, list)):
                        lines.append(f"{item_prefix}  {kk}:")
                        sub = serialize_value(fv, indent=0, depth=depth + 2, indent_size=indent_size)
                        if sub:
                            lines.append(sub)
                    else:
                        vv = _format_primitive(fv, _DOC_DELIMITER)
                        lines.append(f"{item_prefix}  {kk}: {vv}")
        elif isinstance(item, list):
            sub = _serialize_array(item, depth + 1, indent_size)
            lines.append(sub)
        else:
            v = _format_primitive(item, _DOC_DELIMITER)
            lines.append(f"{item_prefix}- {v}")
    return "\n".join(lines)


def serialize_toon_entry(fields: dict) -> str:
    return _serialize_object(fields, 1, 2).lstrip()


def serialize_toon(entries: list) -> str:
    if not entries:
        return ""
    return _serialize_array(entries, 0, 2)
