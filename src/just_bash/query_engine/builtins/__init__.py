"""Builtin functions for the query engine.

This module provides all the builtin functions available in jq expressions.
"""

import base64
import json
import math
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import quote as uri_quote

from ..types import AstNode, EvalContext

# Type for the evaluate function passed from evaluator
EvalFunc = Callable[[Any, AstNode, EvalContext], list[Any]]


def call_builtin(
    value: Any,
    name: str,
    args: list[AstNode],
    ctx: EvalContext,
    eval_fn: EvalFunc,
) -> list[Any]:
    """Call a builtin function.

    Args:
        value: The current input value
        name: The function name
        args: The function arguments (as AST nodes)
        ctx: The evaluation context
        eval_fn: Function to evaluate AST nodes

    Returns:
        A list of result values

    Raises:
        ValueError: If the function is unknown
    """
    # Core functions
    if name == "keys":
        if isinstance(value, list):
            return [list(range(len(value)))]
        if isinstance(value, dict):
            return [sorted(value.keys())]
        return [None]

    if name == "keys_unsorted":
        if isinstance(value, list):
            return [list(range(len(value)))]
        if isinstance(value, dict):
            return [list(value.keys())]
        return [None]

    if name == "values":
        if isinstance(value, list):
            return [value]
        if isinstance(value, dict):
            return [list(value.values())]
        return [None]

    if name == "length":
        if isinstance(value, str):
            return [len(value)]
        if isinstance(value, (list, dict)):
            return [len(value)]
        if value is None:
            return [0]
        return [None]

    if name == "utf8bytelength":
        if isinstance(value, str):
            return [len(value.encode("utf-8"))]
        return [None]

    if name == "type":
        if value is None:
            return ["null"]
        if isinstance(value, bool):
            return ["boolean"]
        if isinstance(value, (int, float)):
            return ["number"]
        if isinstance(value, str):
            return ["string"]
        if isinstance(value, list):
            return ["array"]
        if isinstance(value, dict):
            return ["object"]
        return ["null"]

    if name == "empty":
        return []

    if name == "error":
        msg = eval_fn(value, args[0], ctx)[0] if args else value
        raise ValueError(str(msg))

    if name == "not":
        return [not _is_truthy(value)]

    if name == "null":
        return [None]

    if name == "true":
        return [True]

    if name == "false":
        return [False]

    if name == "first":
        if args:
            results = eval_fn(value, args[0], ctx)
            return [results[0]] if results else []
        if isinstance(value, list) and value:
            return [value[0]]
        return [None]

    if name == "last":
        if args:
            results = eval_fn(value, args[0], ctx)
            return [results[-1]] if results else []
        if isinstance(value, list) and value:
            return [value[-1]]
        return [None]

    if name == "nth":
        if not args:
            return [None]
        ns = eval_fn(value, args[0], ctx)
        n = ns[0] if ns else 0
        if len(args) > 1:
            results = eval_fn(value, args[1], ctx)
            return [results[n]] if isinstance(n, int) and 0 <= n < len(results) else []
        if isinstance(value, list):
            return [value[n]] if isinstance(n, int) and 0 <= n < len(value) else [None]
        return [None]

    if name == "range":
        if not args:
            return []
        starts = eval_fn(value, args[0], ctx)
        if len(args) == 1:
            n = starts[0] if starts else 0
            return list(range(int(n)))
        ends = eval_fn(value, args[1], ctx)
        start = int(starts[0]) if starts else 0
        end = int(ends[0]) if ends else 0
        return list(range(start, end))

    if name == "reverse":
        if isinstance(value, list):
            return [list(reversed(value))]
        if isinstance(value, str):
            return [value[::-1]]
        return [None]

    if name == "sort":
        if isinstance(value, list):
            return [sorted(value, key=_jq_sort_key)]
        return [None]

    if name == "sort_by":
        if not isinstance(value, list) or not args:
            return [None]
        items = [(eval_fn(item, args[0], ctx), item) for item in value]
        sorted_items = sorted(items, key=lambda x: _jq_sort_key(x[0][0] if x[0] else None))
        return [[item for _, item in sorted_items]]

    if name == "unique":
        if isinstance(value, list):
            seen = set()
            result = []
            for item in value:
                key = json.dumps(item, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return [result]
        return [None]

    if name == "unique_by":
        if not isinstance(value, list) or not args:
            return [None]
        seen = set()
        result = []
        for item in value:
            key_vals = eval_fn(item, args[0], ctx)
            key = json.dumps(key_vals[0] if key_vals else None, sort_keys=True)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return [result]

    if name == "group_by":
        if not isinstance(value, list) or not args:
            return [None]
        groups: dict[str, list[Any]] = {}
        for item in value:
            key_vals = eval_fn(item, args[0], ctx)
            key = json.dumps(key_vals[0] if key_vals else None, sort_keys=True)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return [list(groups.values())]

    if name == "max":
        if isinstance(value, list) and value:
            return [max(value, key=_jq_sort_key)]
        return [None]

    if name == "max_by":
        if not isinstance(value, list) or not value or not args:
            return [None]
        items = [(eval_fn(item, args[0], ctx), item) for item in value]
        max_item = max(items, key=lambda x: _jq_sort_key(x[0][0] if x[0] else None))
        return [max_item[1]]

    if name == "min":
        if isinstance(value, list) and value:
            return [min(value, key=_jq_sort_key)]
        return [None]

    if name == "min_by":
        if not isinstance(value, list) or not value or not args:
            return [None]
        items = [(eval_fn(item, args[0], ctx), item) for item in value]
        min_item = min(items, key=lambda x: _jq_sort_key(x[0][0] if x[0] else None))
        return [min_item[1]]

    if name == "flatten":
        if not isinstance(value, list):
            return [None]
        depth = float("inf")
        if args:
            depth_vals = eval_fn(value, args[0], ctx)
            depth = depth_vals[0] if depth_vals else float("inf")
        result = _flatten(value, int(depth) if depth != float("inf") else None)
        return [result]

    if name == "add":
        if isinstance(value, list):
            if not value:
                return [None]
            if all(isinstance(x, (int, float)) for x in value):
                return [sum(value)]
            if all(isinstance(x, str) for x in value):
                return ["".join(value)]
            if all(isinstance(x, list) for x in value):
                result = []
                for x in value:
                    result.extend(x)
                return [result]
            if all(isinstance(x, dict) for x in value):
                result = {}
                for x in value:
                    result.update(x)
                return [result]
        return [None]

    if name == "any":
        if args:
            if isinstance(value, list):
                return [
                    any(
                        _is_truthy(eval_fn(item, args[0], ctx)[0])
                        for item in value
                        if eval_fn(item, args[0], ctx)
                    )
                ]
            return [False]
        if isinstance(value, list):
            return [any(_is_truthy(x) for x in value)]
        return [False]

    if name == "all":
        if args:
            if isinstance(value, list):
                return [
                    all(
                        _is_truthy(eval_fn(item, args[0], ctx)[0])
                        for item in value
                        if eval_fn(item, args[0], ctx)
                    )
                ]
            return [True]
        if isinstance(value, list):
            return [all(_is_truthy(x) for x in value)]
        return [True]

    if name == "select":
        if not args:
            return [value]
        conds = eval_fn(value, args[0], ctx)
        return [value] if any(_is_truthy(c) for c in conds) else []

    if name == "map":
        if not args or not isinstance(value, list):
            return [None]
        results = []
        for item in value:
            results.extend(eval_fn(item, args[0], ctx))
        return [results]

    if name == "map_values":
        if not args:
            return [None]
        if isinstance(value, list):
            results = []
            for item in value:
                item_results = eval_fn(item, args[0], ctx)
                results.extend(item_results)
            return [results]
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                mapped = eval_fn(v, args[0], ctx)
                if mapped:
                    result[k] = mapped[0]
            return [result]
        return [None]

    if name == "has":
        if not args:
            return [False]
        keys = eval_fn(value, args[0], ctx)
        key = keys[0] if keys else None
        if isinstance(value, list) and isinstance(key, int):
            return [0 <= key < len(value)]
        if isinstance(value, dict) and isinstance(key, str):
            return [key in value]
        return [False]

    if name == "in":
        if not args:
            return [False]
        objs = eval_fn(value, args[0], ctx)
        obj = objs[0] if objs else None
        if isinstance(obj, list) and isinstance(value, int):
            return [0 <= value < len(obj)]
        if isinstance(obj, dict) and isinstance(value, str):
            return [value in obj]
        return [False]

    if name == "contains":
        if not args:
            return [False]
        others = eval_fn(value, args[0], ctx)
        other = others[0] if others else None
        return [_contains_deep(value, other)]

    if name == "inside":
        if not args:
            return [False]
        others = eval_fn(value, args[0], ctx)
        other = others[0] if others else None
        return [_contains_deep(other, value)]

    if name == "getpath":
        if not args:
            return [None]
        paths = eval_fn(value, args[0], ctx)
        path = paths[0] if paths else []
        current = value
        for key in path:
            if current is None:
                return [None]
            if isinstance(current, list) and isinstance(key, int):
                current = current[key] if 0 <= key < len(current) else None
            elif isinstance(current, dict) and isinstance(key, str):
                current = current.get(key)
            else:
                return [None]
        return [current]

    if name == "setpath":
        if len(args) < 2:
            return [None]
        paths = eval_fn(value, args[0], ctx)
        path = paths[0] if paths else []
        vals = eval_fn(value, args[1], ctx)
        new_val = vals[0] if vals else None
        return [_set_path(value, path, new_val)]

    if name == "delpaths":
        if not args:
            return [value]
        path_lists = eval_fn(value, args[0], ctx)
        paths = path_lists[0] if path_lists else []
        result = value
        # Delete longest paths first to avoid index shifting issues
        for path in sorted(paths, key=len, reverse=True):
            result = _delete_path(result, path)
        return [result]

    if name == "path":
        if not args:
            return [[]]
        # Collect all paths that match the expression
        paths = []
        _collect_paths(value, args[0], ctx, eval_fn, [], paths)
        return paths

    if name == "del":
        if not args:
            return [value]
        return [_apply_del(value, args[0], ctx, eval_fn)]

    if name == "paths":
        paths = _get_all_paths(value, [])
        if args:
            # Filter paths by predicate
            filtered = []
            for p in paths:
                v = _get_value_at_path(value, p)
                results = eval_fn(v, args[0], ctx)
                if any(_is_truthy(r) for r in results):
                    filtered.append(p)
            return filtered
        return paths

    if name == "leaf_paths":
        return [_get_leaf_paths(value, [])]

    if name == "to_entries":
        if isinstance(value, dict):
            return [[{"key": k, "value": v} for k, v in value.items()]]
        return [None]

    if name == "from_entries":
        if isinstance(value, list):
            result = {}
            for item in value:
                if isinstance(item, dict):
                    key = item.get("key") or item.get("name") or item.get("k")
                    val = item.get("value") if "value" in item else item.get("v")
                    if key is not None:
                        result[str(key)] = val
            return [result]
        return [None]

    if name == "with_entries":
        if not args:
            return [value]
        if isinstance(value, dict):
            entries = [{"key": k, "value": v} for k, v in value.items()]
            new_entries = []
            for entry in entries:
                results = eval_fn(entry, args[0], ctx)
                new_entries.extend(results)
            result = {}
            for item in new_entries:
                if isinstance(item, dict):
                    key = item.get("key") or item.get("name") or item.get("k")
                    val = item.get("value") if "value" in item else item.get("v")
                    if key is not None:
                        result[str(key)] = val
            return [result]
        return [None]

    # String functions
    if name == "join":
        if not isinstance(value, list):
            return [None]
        seps = eval_fn(value, args[0], ctx) if args else [""]
        sep = str(seps[0]) if seps else ""
        return [sep.join(v if isinstance(v, str) else json.dumps(v) for v in value)]

    if name == "split":
        if not isinstance(value, str) or not args:
            return [None]
        seps = eval_fn(value, args[0], ctx)
        sep = str(seps[0]) if seps else ""
        return [value.split(sep)]

    if name == "test":
        if not isinstance(value, str) or not args:
            return [False]
        patterns = eval_fn(value, args[0], ctx)
        pattern = str(patterns[0]) if patterns else ""
        try:
            flags = eval_fn(value, args[1], ctx)[0] if len(args) > 1 else ""
            re_flags = _get_re_flags(flags)
            return [bool(re.search(pattern, value, re_flags))]
        except re.error:
            return [False]

    if name == "match":
        if not isinstance(value, str) or not args:
            return [None]
        patterns = eval_fn(value, args[0], ctx)
        pattern = str(patterns[0]) if patterns else ""
        try:
            flags = eval_fn(value, args[1], ctx)[0] if len(args) > 1 else ""
            re_flags = _get_re_flags(flags)
            m = re.search(pattern, value, re_flags)
            if not m:
                return []
            return [
                {
                    "offset": m.start(),
                    "length": len(m.group()),
                    "string": m.group(),
                    "captures": [
                        {
                            "offset": m.start(i + 1) if m.group(i + 1) else None,
                            "length": len(m.group(i + 1)) if m.group(i + 1) else 0,
                            "string": m.group(i + 1) or "",
                            "name": None,
                        }
                        for i in range(m.lastindex or 0)
                    ],
                }
            ]
        except re.error:
            return [None]

    if name == "capture":
        if not isinstance(value, str) or not args:
            return [None]
        patterns = eval_fn(value, args[0], ctx)
        pattern = str(patterns[0]) if patterns else ""
        try:
            flags = eval_fn(value, args[1], ctx)[0] if len(args) > 1 else ""
            re_flags = _get_re_flags(flags)
            m = re.search(pattern, value, re_flags)
            if not m or not m.groupdict():
                return [{}]
            return [m.groupdict()]
        except re.error:
            return [None]

    if name == "sub":
        if not isinstance(value, str) or len(args) < 2:
            return [None]
        patterns = eval_fn(value, args[0], ctx)
        replacements = eval_fn(value, args[1], ctx)
        pattern = str(patterns[0]) if patterns else ""
        replacement = str(replacements[0]) if replacements else ""
        try:
            flags = eval_fn(value, args[2], ctx)[0] if len(args) > 2 else ""
            re_flags = _get_re_flags(flags)
            return [re.sub(pattern, replacement, value, count=1, flags=re_flags)]
        except re.error:
            return [value]

    if name == "gsub":
        if not isinstance(value, str) or len(args) < 2:
            return [None]
        patterns = eval_fn(value, args[0], ctx)
        replacements = eval_fn(value, args[1], ctx)
        pattern = str(patterns[0]) if patterns else ""
        replacement = str(replacements[0]) if replacements else ""
        try:
            flags = eval_fn(value, args[2], ctx)[0] if len(args) > 2 else "g"
            re_flags = _get_re_flags(flags)
            return [re.sub(pattern, replacement, value, flags=re_flags)]
        except re.error:
            return [value]

    if name == "ascii_downcase":
        if isinstance(value, str):
            return [value.lower()]
        return [None]

    if name == "ascii_upcase":
        if isinstance(value, str):
            return [value.upper()]
        return [None]

    if name == "ltrimstr":
        if not isinstance(value, str) or not args:
            return [value]
        prefixes = eval_fn(value, args[0], ctx)
        prefix = str(prefixes[0]) if prefixes else ""
        return [value[len(prefix) :] if value.startswith(prefix) else value]

    if name == "rtrimstr":
        if not isinstance(value, str) or not args:
            return [value]
        suffixes = eval_fn(value, args[0], ctx)
        suffix = str(suffixes[0]) if suffixes else ""
        return [value[: -len(suffix)] if value.endswith(suffix) and suffix else value]

    if name == "trim":
        if isinstance(value, str):
            return [value.strip()]
        return [value]

    if name == "startswith":
        if not isinstance(value, str) or not args:
            return [False]
        prefixes = eval_fn(value, args[0], ctx)
        prefix = str(prefixes[0]) if prefixes else ""
        return [value.startswith(prefix)]

    if name == "endswith":
        if not isinstance(value, str) or not args:
            return [False]
        suffixes = eval_fn(value, args[0], ctx)
        suffix = str(suffixes[0]) if suffixes else ""
        return [value.endswith(suffix)]

    if name == "index":
        if not args:
            return [None]
        needles = eval_fn(value, args[0], ctx)
        needle = needles[0] if needles else None
        if isinstance(value, str) and isinstance(needle, str):
            idx = value.find(needle)
            return [idx if idx >= 0 else None]
        if isinstance(value, list):
            for i, item in enumerate(value):
                if _deep_equal(item, needle):
                    return [i]
            return [None]
        return [None]

    if name == "rindex":
        if not args:
            return [None]
        needles = eval_fn(value, args[0], ctx)
        needle = needles[0] if needles else None
        if isinstance(value, str) and isinstance(needle, str):
            idx = value.rfind(needle)
            return [idx if idx >= 0 else None]
        if isinstance(value, list):
            for i in range(len(value) - 1, -1, -1):
                if _deep_equal(value[i], needle):
                    return [i]
            return [None]
        return [None]

    if name == "indices":
        if not args:
            return [[]]
        needles = eval_fn(value, args[0], ctx)
        needle = needles[0] if needles else None
        result = []
        if isinstance(value, str) and isinstance(needle, str):
            idx = value.find(needle)
            while idx != -1:
                result.append(idx)
                idx = value.find(needle, idx + 1)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if _deep_equal(item, needle):
                    result.append(i)
        return [result]

    # Math functions
    if name == "floor":
        if isinstance(value, (int, float)):
            return [math.floor(value)]
        return [None]

    if name == "ceil":
        if isinstance(value, (int, float)):
            return [math.ceil(value)]
        return [None]

    if name == "round":
        if isinstance(value, (int, float)):
            return [round(value)]
        return [None]

    if name == "sqrt":
        if isinstance(value, (int, float)):
            return [math.sqrt(value)]
        return [None]

    if name in ("fabs", "abs"):
        if isinstance(value, (int, float)):
            return [abs(value)]
        return [None]

    if name == "log":
        if isinstance(value, (int, float)):
            return [math.log(value)]
        return [None]

    if name == "log10":
        if isinstance(value, (int, float)):
            return [math.log10(value)]
        return [None]

    if name == "log2":
        if isinstance(value, (int, float)):
            return [math.log2(value)]
        return [None]

    if name == "exp":
        if isinstance(value, (int, float)):
            return [math.exp(value)]
        return [None]

    if name == "exp10":
        if isinstance(value, (int, float)):
            return [10**value]
        return [None]

    if name == "exp2":
        if isinstance(value, (int, float)):
            return [2**value]
        return [None]

    if name == "pow":
        if not isinstance(value, (int, float)) or not args:
            return [None]
        exps = eval_fn(value, args[0], ctx)
        exp = exps[0] if exps else 1
        return [value**exp]

    if name == "sin":
        if isinstance(value, (int, float)):
            return [math.sin(value)]
        return [None]

    if name == "cos":
        if isinstance(value, (int, float)):
            return [math.cos(value)]
        return [None]

    if name == "tan":
        if isinstance(value, (int, float)):
            return [math.tan(value)]
        return [None]

    if name == "asin":
        if isinstance(value, (int, float)):
            return [math.asin(value)]
        return [None]

    if name == "acos":
        if isinstance(value, (int, float)):
            return [math.acos(value)]
        return [None]

    if name == "atan":
        if isinstance(value, (int, float)):
            return [math.atan(value)]
        return [None]

    if name == "tostring":
        if isinstance(value, str):
            return [value]
        return [json.dumps(value)]

    if name == "tonumber":
        if isinstance(value, (int, float)):
            return [value]
        if isinstance(value, str):
            try:
                return [float(value) if "." in value else int(value)]
            except ValueError:
                return [None]
        return [None]

    if name == "infinite":
        return [not math.isfinite(value) if isinstance(value, (int, float)) else False]

    if name == "nan":
        return [math.isnan(value) if isinstance(value, (int, float)) else False]

    if name == "isnan":
        return [isinstance(value, (int, float)) and math.isnan(value)]

    if name == "isinfinite":
        return [isinstance(value, (int, float)) and not math.isfinite(value)]

    if name == "isfinite":
        return [isinstance(value, (int, float)) and math.isfinite(value)]

    if name == "isnormal":
        return [isinstance(value, (int, float)) and math.isfinite(value) and value != 0]

    # Type filters
    if name == "numbers":
        # In Python, bool is a subclass of int, so we need to exclude bools
        return [value] if isinstance(value, (int, float)) and not isinstance(value, bool) else []

    if name == "strings":
        return [value] if isinstance(value, str) else []

    if name == "booleans":
        return [value] if isinstance(value, bool) else []

    if name == "nulls":
        return [value] if value is None else []

    if name == "arrays":
        return [value] if isinstance(value, list) else []

    if name == "objects":
        return [value] if isinstance(value, dict) else []

    if name == "iterables":
        return [value] if isinstance(value, (list, dict)) else []

    if name == "scalars":
        return [value] if not isinstance(value, (list, dict)) else []

    if name == "now":
        import time

        return [time.time()]

    if name == "env":
        return [ctx.env]

    if name == "recurse":
        if not args:
            results = []
            _walk_recurse(value, results)
            return results
        results = []
        seen = set()

        def walk(v: Any) -> None:
            key = json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else str(v)
            if key in seen:
                return
            seen.add(key)
            results.append(v)
            nexts = eval_fn(v, args[0], ctx)
            for n in nexts:
                if n is not None:
                    walk(n)

        walk(value)
        return results

    if name == "recurse_down":
        return call_builtin(value, "recurse", args, ctx, eval_fn)

    if name == "walk":
        if not args:
            return [value]
        seen: set[int] = set()

        def walk_fn(v: Any) -> Any:
            if isinstance(v, (dict, list)):
                obj_id = id(v)
                if obj_id in seen:
                    return v
                seen.add(obj_id)

            if isinstance(v, list):
                transformed = [walk_fn(item) for item in v]
            elif isinstance(v, dict):
                transformed = {k: walk_fn(val) for k, val in v.items()}
            else:
                transformed = v

            results = eval_fn(transformed, args[0], ctx)
            return results[0] if results else transformed

        return [walk_fn(value)]

    if name == "transpose":
        if not isinstance(value, list):
            return [None]
        if not value:
            return [[]]
        max_len = max((len(row) if isinstance(row, list) else 0) for row in value)
        result = []
        for i in range(max_len):
            row = [r[i] if isinstance(r, list) and i < len(r) else None for r in value]
            result.append(row)
        return [result]

    if name == "ascii":
        if isinstance(value, str) and value:
            return [ord(value[0])]
        return [None]

    if name == "explode":
        if isinstance(value, str):
            return [[ord(c) for c in value]]
        return [None]

    if name == "implode":
        if isinstance(value, list):
            try:
                return ["".join(chr(c) for c in value)]
            except (TypeError, ValueError):
                return [None]
        return [None]

    if name in ("tojson", "tojsonstream"):
        return [json.dumps(value)]

    if name == "fromjson":
        if isinstance(value, str):
            try:
                return [json.loads(value)]
            except json.JSONDecodeError:
                return [None]
        return [None]

    if name == "limit":
        if len(args) < 2:
            return []
        ns = eval_fn(value, args[0], ctx)
        n = ns[0] if ns else 0
        results = eval_fn(value, args[1], ctx)
        return results[: int(n)]

    if name == "until":
        if len(args) < 2:
            return [value]
        current = value
        max_iterations = ctx.limits.max_iterations
        for _ in range(max_iterations):
            conds = eval_fn(current, args[0], ctx)
            if any(_is_truthy(c) for c in conds):
                return [current]
            nexts = eval_fn(current, args[1], ctx)
            if not nexts:
                return [current]
            current = nexts[0]
        raise ValueError(f"jq until: too many iterations ({max_iterations})")

    if name == "while":
        if len(args) < 2:
            return [value]
        results = []
        current = value
        max_iterations = ctx.limits.max_iterations
        for _ in range(max_iterations):
            conds = eval_fn(current, args[0], ctx)
            if not any(_is_truthy(c) for c in conds):
                break
            results.append(current)
            nexts = eval_fn(current, args[1], ctx)
            if not nexts:
                break
            current = nexts[0]
        return results

    if name == "repeat":
        if not args:
            return [value]
        results = []
        current = value
        max_iterations = ctx.limits.max_iterations
        for _ in range(max_iterations):
            results.append(current)
            nexts = eval_fn(current, args[0], ctx)
            if not nexts:
                break
            current = nexts[0]
        return results

    if name == "debug":
        return [value]

    if name == "input_line_number":
        return [1]

    # Format strings
    if name == "@base64":
        if isinstance(value, str):
            return [base64.b64encode(value.encode("utf-8")).decode("utf-8")]
        return [None]

    if name == "@base64d":
        if isinstance(value, str):
            try:
                return [base64.b64decode(value).decode("utf-8")]
            except Exception:
                return [None]
        return [None]

    if name == "@uri":
        if isinstance(value, str):
            return [uri_quote(value, safe="")]
        return [None]

    if name == "@csv":
        if not isinstance(value, list):
            return [None]
        escaped = []
        for v in value:
            s = str(v) if v is not None else ""
            if "," in s or '"' in s or "\n" in s:
                escaped.append(f'"{s.replace(chr(34), chr(34) + chr(34))}"')
            else:
                escaped.append(s)
        return [",".join(escaped)]

    if name == "@tsv":
        if not isinstance(value, list):
            return [None]
        escaped = []
        for v in value:
            s = str(v) if v is not None else ""
            escaped.append(s.replace("\t", "\\t").replace("\n", "\\n"))
        return ["\t".join(escaped)]

    if name == "@json":
        return [json.dumps(value)]

    if name == "@html":
        if isinstance(value, str):
            return [
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            ]
        return [None]

    if name == "@sh":
        if isinstance(value, str):
            return [f"'{value.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"]
        return [None]

    if name == "@text":
        if isinstance(value, str):
            return [value]
        if value is None:
            return [""]
        return [str(value)]

    # Navigation operators
    if name == "parent":
        if ctx.root is None or not ctx.current_path:
            return []
        path = ctx.current_path
        if not path:
            return []
        levels = 1
        if args:
            levels_vals = eval_fn(value, args[0], ctx)
            levels = levels_vals[0] if levels_vals else 1

        if levels >= 0:
            if levels > len(path):
                return []
            parent_path = path[: len(path) - levels]
        else:
            target_len = -levels - 1
            if target_len >= len(path):
                return [value]
            parent_path = path[:target_len]
        return [_get_value_at_path(ctx.root, parent_path)]

    if name == "parents":
        if ctx.root is None or not ctx.current_path:
            return [[]]
        path = ctx.current_path
        parents = []
        for i in range(len(path) - 1, -1, -1):
            parents.append(_get_value_at_path(ctx.root, path[:i]))
        return [parents]

    if name == "root":
        return [ctx.root] if ctx.root is not None else []

    raise ValueError(f"Unknown function: {name}")


def _is_truthy(v: Any) -> bool:
    """Check if a value is truthy in jq terms."""
    return v is not None and v is not False


def _deep_equal(a: Any, b: Any) -> bool:
    """Deep equality check."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _jq_sort_key(v: Any) -> tuple[int, Any]:
    """Generate a sort key for jq-style sorting."""
    if v is None:
        return (0, 0)
    if isinstance(v, bool):
        return (1, int(v))
    if isinstance(v, (int, float)):
        return (2, v)
    if isinstance(v, str):
        return (3, v)
    if isinstance(v, list):
        return (4, json.dumps(v, sort_keys=True))
    if isinstance(v, dict):
        return (5, json.dumps(v, sort_keys=True))
    return (6, str(v))


def _flatten(lst: list[Any], depth: int | None) -> list[Any]:
    """Flatten a list to a given depth."""
    if depth == 0:
        return lst
    result = []
    for item in lst:
        if isinstance(item, list):
            new_depth = None if depth is None else depth - 1
            result.extend(_flatten(item, new_depth))
        else:
            result.append(item)
    return result


def _contains_deep(a: Any, b: Any) -> bool:
    """Check if a contains b (deep containment)."""
    if _deep_equal(a, b):
        return True
    if isinstance(a, list) and isinstance(b, list):
        return all(any(_contains_deep(a_item, b_item) for a_item in a) for b_item in b)
    if isinstance(a, dict) and isinstance(b, dict):
        return all(k in a and _contains_deep(a[k], v) for k, v in b.items())
    return False


def _set_path(value: Any, path: list[str | int], new_val: Any) -> Any:
    """Set a value at a path."""
    if not path:
        return new_val
    head, *rest = path
    if isinstance(head, int):
        arr = list(value) if isinstance(value, list) else []
        while len(arr) <= head:
            arr.append(None)
        arr[head] = _set_path(arr[head], rest, new_val)
        return arr
    else:
        obj = dict(value) if isinstance(value, dict) else {}
        obj[head] = _set_path(obj.get(head), rest, new_val)
        return obj


def _delete_path(value: Any, path: list[str | int]) -> Any:
    """Delete a value at a path."""
    if not path:
        return None
    if len(path) == 1:
        head = path[0]
        if isinstance(value, list) and isinstance(head, int):
            arr = list(value)
            if 0 <= head < len(arr):
                arr.pop(head)
            return arr
        if isinstance(value, dict) and isinstance(head, str):
            obj = dict(value)
            obj.pop(head, None)
            return obj
        return value
    head, *rest = path
    if isinstance(value, list) and isinstance(head, int):
        arr = list(value)
        if 0 <= head < len(arr):
            arr[head] = _delete_path(arr[head], rest)
        return arr
    if isinstance(value, dict) and isinstance(head, str):
        obj = dict(value)
        if head in obj:
            obj[head] = _delete_path(obj[head], rest)
        return obj
    return value


def _get_all_paths(value: Any, current: list[str | int]) -> list[list[str | int]]:
    """Get all paths in a value."""
    paths = []
    if isinstance(value, dict):
        for k, v in value.items():
            new_path = current + [k]
            paths.append(new_path)
            paths.extend(_get_all_paths(v, new_path))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            new_path = current + [i]
            paths.append(new_path)
            paths.extend(_get_all_paths(v, new_path))
    return paths


def _get_leaf_paths(value: Any, current: list[str | int]) -> list[list[str | int]]:
    """Get all leaf paths (paths to non-container values)."""
    paths = []
    if value is None or not isinstance(value, (dict, list)):
        return [current] if current else []
    if isinstance(value, dict):
        if not value:
            return [current] if current else []
        for k, v in value.items():
            paths.extend(_get_leaf_paths(v, current + [k]))
    elif isinstance(value, list):
        if not value:
            return [current] if current else []
        for i, v in enumerate(value):
            paths.extend(_get_leaf_paths(v, current + [i]))
    return paths


def _get_value_at_path(value: Any, path: list[str | int]) -> Any:
    """Get the value at a path."""
    current = value
    for key in path:
        if isinstance(current, dict) and isinstance(key, str):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key] if 0 <= key < len(current) else None
        else:
            return None
    return current


def _collect_paths(
    value: Any,
    expr: AstNode,
    ctx: EvalContext,
    eval_fn: EvalFunc,
    current_path: list[str | int],
    paths: list[list[str | int]],
) -> None:
    """Collect paths that match an expression."""
    results = eval_fn(value, expr, ctx)
    if results:
        paths.append(current_path)


def _apply_del(value: Any, path_expr: AstNode, ctx: EvalContext, eval_fn: EvalFunc) -> Any:
    """Apply deletion at a path."""
    if path_expr.type == "Identity":
        return None
    if path_expr.type == "Field":
        field_node = path_expr
        if isinstance(value, dict):
            result = dict(value)
            result.pop(field_node.name, None)
            return result
        return value
    if path_expr.type == "Index":
        index_node = path_expr
        indices = eval_fn(value, index_node.index, ctx)
        idx = indices[0] if indices else None
        if isinstance(idx, int) and isinstance(value, list):
            arr = list(value)
            i = idx if idx >= 0 else len(arr) + idx
            if 0 <= i < len(arr):
                arr.pop(i)
            return arr
        if isinstance(idx, str) and isinstance(value, dict):
            result = dict(value)
            result.pop(idx, None)
            return result
        return value
    if path_expr.type == "Iterate":
        if isinstance(value, list):
            return []
        if isinstance(value, dict):
            return {}
        return value
    return value


def _walk_recurse(value: Any, results: list[Any]) -> None:
    """Walk recursively through a value."""
    results.append(value)
    if isinstance(value, list):
        for item in value:
            _walk_recurse(item, results)
    elif isinstance(value, dict):
        for v in value.values():
            _walk_recurse(v, results)


def _get_re_flags(flags: str) -> int:
    """Convert jq regex flag string to Python re flags."""
    result = 0
    if "i" in flags:
        result |= re.IGNORECASE
    if "m" in flags:
        result |= re.MULTILINE
    if "s" in flags:
        result |= re.DOTALL
    if "x" in flags:
        result |= re.VERBOSE
    return result
