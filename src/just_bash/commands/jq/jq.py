"""Jq command implementation.

Usage: jq [OPTIONS] FILTER [FILE...]

JSON processor.

Options:
  -r, --raw-output    output strings without quotes
  -c, --compact       compact output (no pretty printing)
  -s, --slurp         read all inputs into an array
  -e                  exit with 1 if last output is false or null
  -n, --null-input    don't read any input
  -R, --raw-input     read each line as a string

Filters:
  .                   identity (output input unchanged)
  .foo                object field access
  .foo.bar            nested field access
  .[N]                array index access
  .[]                 array/object iterator
  .[N:M]              array slice
  |                   pipe (chain filters)
  ,                   output multiple values
  select(expr)        filter values
  map(expr)           apply expression to each element
  keys                get object keys
  values              get object values
  length              get length
  type                get type name
  empty               output nothing
  add                 sum/concatenate
  first, last         first/last element
  reverse             reverse array
  sort                sort array
  unique              unique elements
  flatten             flatten nested arrays
  group_by(expr)      group by expression
  min, max            minimum/maximum
  has(key)            check if key exists
  in(object)          check if key is in object
  contains(x)         check if contains x
  split(s)            split string by s
  join(s)             join array by s
  ascii_downcase      lowercase
  ascii_upcase        uppercase
  ltrimstr(s)         remove prefix
  rtrimstr(s)         remove suffix
  startswith(s)       check prefix
  endswith(s)         check suffix
  test(regex)         regex match
  @base64             encode to base64
  @base64d            decode from base64
  @uri                URI encode
  @csv                CSV format
  @json               JSON encode
  @text               convert to text
"""

import json
import math
import re
import base64
from urllib.parse import quote as uri_quote
from dataclasses import dataclass
from typing import Any
from ...types import CommandContext, ExecResult


@dataclass
class JqFilter:
    """A parsed jq filter."""

    type: str  # "identity", "field", "index", "slice", "iterator", "pipe", etc.
    value: Any = None
    left: "JqFilter | None" = None
    right: "JqFilter | None" = None
    args: list["JqFilter"] | None = None


class JqCommand:
    """The jq command."""

    name = "jq"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the jq command."""
        raw_output = False
        compact = False
        slurp = False
        exit_on_false = False
        null_input = False
        raw_input = False
        filter_str: str | None = None
        files: list[str] = []

        # Parse arguments
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--":
                files.extend(args[i + 1:])
                break
            elif arg in ("-r", "--raw-output"):
                raw_output = True
            elif arg in ("-c", "--compact"):
                compact = True
            elif arg in ("-s", "--slurp"):
                slurp = True
            elif arg == "-e":
                exit_on_false = True
            elif arg in ("-n", "--null-input"):
                null_input = True
            elif arg in ("-R", "--raw-input"):
                raw_input = True
            elif arg.startswith("-") and len(arg) > 1:
                # Combined flags
                for c in arg[1:]:
                    if c == "r":
                        raw_output = True
                    elif c == "c":
                        compact = True
                    elif c == "s":
                        slurp = True
                    elif c == "e":
                        exit_on_false = True
                    elif c == "n":
                        null_input = True
                    elif c == "R":
                        raw_input = True
                    else:
                        return ExecResult(
                            stdout="",
                            stderr=f"jq: Unknown option: -{c}\n",
                            exit_code=2,
                        )
            elif filter_str is None:
                # First positional argument is the filter
                filter_str = arg
            else:
                files.append(arg)
            i += 1

        # Default filter if none provided
        if filter_str is None:
            filter_str = "."

        # Parse the filter
        try:
            jq_filter = self._parse_filter(filter_str)
        except ValueError as e:
            return ExecResult(
                stdout="",
                stderr=f"jq: {e}\n",
                exit_code=2,
            )

        # Get input
        inputs: list[Any] = []
        stderr = ""

        if null_input:
            inputs = [None]
        elif not files:
            files = ["-"]

        for f in files:
            try:
                if f == "-":
                    content = ctx.stdin
                else:
                    path = ctx.fs.resolve_path(ctx.cwd, f)
                    content = await ctx.fs.read_file(path)

                if raw_input:
                    # Each line is a string
                    for line in content.split("\n"):
                        if line:
                            inputs.append(line)
                else:
                    # Parse JSON
                    content = content.strip()
                    if content:
                        # Handle multiple JSON objects
                        decoder = json.JSONDecoder()
                        pos = 0
                        while pos < len(content):
                            # Skip whitespace
                            while pos < len(content) and content[pos] in " \t\n\r":
                                pos += 1
                            if pos >= len(content):
                                break
                            try:
                                obj, end = decoder.raw_decode(content, pos)
                                inputs.append(obj)
                                pos = end
                            except json.JSONDecodeError as e:
                                stderr += f"jq: parse error: {e}\n"
                                break

            except FileNotFoundError:
                stderr += f"jq: error: {f}: No such file or directory\n"

        if stderr:
            return ExecResult(stdout="", stderr=stderr, exit_code=2)

        # Apply slurp
        if slurp and not null_input:
            inputs = [inputs]

        # Apply filter
        outputs: list[Any] = []
        for inp in inputs:
            try:
                results = list(self._apply_filter(jq_filter, inp))
                outputs.extend(results)
            except Exception as e:
                stderr += f"jq: error: {e}\n"

        # Format output
        output = ""
        for val in outputs:
            output += self._format_value(val, raw_output, compact) + "\n"

        # Determine exit code
        exit_code = 0
        if exit_on_false and outputs:
            last = outputs[-1]
            if last is None or last is False:
                exit_code = 1

        if stderr:
            return ExecResult(stdout=output, stderr=stderr, exit_code=2)

        return ExecResult(stdout=output, stderr="", exit_code=exit_code)

    def _parse_filter(self, s: str) -> JqFilter:
        """Parse a jq filter expression."""
        s = s.strip()

        if not s or s == ".":
            return JqFilter(type="identity")

        # Handle pipe
        if "|" in s:
            parts = self._split_at_pipe(s)
            if len(parts) > 1:
                left = self._parse_filter(parts[0])
                right = self._parse_filter("|".join(parts[1:]))
                return JqFilter(type="pipe", left=left, right=right)

        # Handle comma (multiple outputs)
        if "," in s and not s.startswith("[") and not s.startswith("{"):
            parts = self._split_at_comma(s)
            if len(parts) > 1:
                filters = [self._parse_filter(p) for p in parts]
                return JqFilter(type="multi", args=filters)

        # Handle array construction
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            if not inner:
                return JqFilter(type="array", args=[])
            inner_filter = self._parse_filter(inner)
            return JqFilter(type="collect", left=inner_filter)

        # Handle object construction
        if s.startswith("{") and s.endswith("}"):
            return self._parse_object_construction(s)

        # Handle parentheses
        if s.startswith("(") and s.endswith(")"):
            return self._parse_filter(s[1:-1])

        # Handle functions
        for func in ["select", "map", "group_by", "sort_by", "unique_by", "max_by", "min_by",
                     "has", "in", "contains", "inside", "split", "join", "test", "match",
                     "ltrimstr", "rtrimstr", "startswith", "endswith", "tostring", "tonumber",
                     "getpath", "with_entries"]:
            if s.startswith(func + "("):
                end = self._find_matching_paren(s, len(func))
                if end != -1:
                    arg = s[len(func) + 1:end]
                    arg_filter = self._parse_filter(arg) if arg else JqFilter(type="identity")
                    return JqFilter(type=func, left=arg_filter)

        # Handle built-in functions without args
        simple_funcs = ["keys", "values", "length", "type", "empty", "add", "first", "last",
                        "reverse", "sort", "unique", "flatten", "min", "max", "not", "null",
                        "true", "false", "ascii_downcase", "ascii_upcase", "keys_unsorted",
                        "to_entries", "from_entries", "floor", "ceil", "round",
                        "sqrt", "fabs", "infinite", "nan", "isnan", "isinfinite", "isfinite",
                        "isnormal", "env", "now", "paths", "leaf_paths"]

        for func in simple_funcs:
            if s == func:
                return JqFilter(type=func)

        # Handle format functions
        if s.startswith("@"):
            format_name = s[1:]
            return JqFilter(type="format", value=format_name)

        # Handle update operators (+=, -=, etc.) - must come before arithmetic
        for op in ["+=", "-=", "*=", "/="]:
            if f" {op} " in s:
                parts = s.split(f" {op} ", 1)
                left = self._parse_filter(parts[0])
                right = self._parse_filter(parts[1])
                return JqFilter(type=op, left=left, right=right)

        # Handle arithmetic and comparison
        for op in ["==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/", "%", "and", "or"]:
            if f" {op} " in s:
                parts = s.split(f" {op} ", 1)
                left = self._parse_filter(parts[0])
                right = self._parse_filter(parts[1])
                return JqFilter(type=op, left=left, right=right)

        # Handle string literal
        if s.startswith('"') and s.endswith('"'):
            return JqFilter(type="string", value=self._parse_string(s))

        # Handle number
        try:
            if "." in s:
                return JqFilter(type="number", value=float(s))
            return JqFilter(type="number", value=int(s))
        except ValueError:
            pass

        # Handle field access
        if s.startswith("."):
            return self._parse_field_access(s)

        # Handle variable or identifier
        if re.match(r"^[a-zA-Z_]\w*$", s):
            return JqFilter(type="var", value=s)

        raise ValueError(f"Invalid filter: {s}")

    def _parse_field_access(self, s: str) -> JqFilter:
        """Parse field access like .foo, .foo.bar, .[0], .[]."""
        if s == ".":
            return JqFilter(type="identity")

        pos = 1  # Skip leading dot
        current = JqFilter(type="identity")

        while pos < len(s):
            # Array index or iterator
            if s[pos] == "[":
                end = self._find_matching_bracket(s, pos)
                if end == -1:
                    raise ValueError(f"Unmatched bracket in: {s}")

                inner = s[pos + 1:end]
                if inner == "":
                    # Iterator .[]
                    current = JqFilter(type="iterator", left=current)
                elif ":" in inner:
                    # Slice .[N:M]
                    parts = inner.split(":", 1)
                    start = int(parts[0]) if parts[0] else None
                    stop = int(parts[1]) if parts[1] else None
                    current = JqFilter(type="slice", left=current, value=(start, stop))
                else:
                    # Index
                    try:
                        idx = int(inner)
                        current = JqFilter(type="index", left=current, value=idx)
                    except ValueError:
                        # Could be a string key
                        if inner.startswith('"') and inner.endswith('"'):
                            key = self._parse_string(inner)
                            current = JqFilter(type="field", left=current, value=key)
                        else:
                            current = JqFilter(type="field", left=current, value=inner)

                pos = end + 1

            # Field name
            elif s[pos] == ".":
                pos += 1
            elif s[pos].isalpha() or s[pos] == "_":
                # Read field name
                start = pos
                while pos < len(s) and (s[pos].isalnum() or s[pos] == "_"):
                    pos += 1
                field_name = s[start:pos]
                current = JqFilter(type="field", left=current, value=field_name)
            elif s[pos] == "?":
                # Optional operator
                current = JqFilter(type="optional", left=current)
                pos += 1
            else:
                raise ValueError(f"Unexpected character at position {pos}: {s[pos]}")

        return current

    def _parse_object_construction(self, s: str) -> JqFilter:
        """Parse object construction like {foo, bar: .baz}."""
        inner = s[1:-1].strip()
        if not inner:
            return JqFilter(type="object", args=[])

        pairs = []
        parts = self._split_at_comma(inner)
        for part in parts:
            part = part.strip()
            if ":" in part:
                key_part, val_part = part.split(":", 1)
                key = key_part.strip().strip('"')
                val_filter = self._parse_filter(val_part.strip())
                pairs.append((key, val_filter))
            else:
                # Shorthand: foo means foo: .foo
                key = part.strip()
                if key.startswith("."):
                    key = key[1:]
                pairs.append((key, self._parse_filter("." + key)))

        return JqFilter(type="object", args=pairs)

    def _split_at_pipe(self, s: str) -> list[str]:
        """Split string at pipe characters, respecting nesting."""
        parts = []
        current = ""
        depth = 0

        for char in s:
            if char in "([{":
                depth += 1
                current += char
            elif char in ")]}":
                depth -= 1
                current += char
            elif char == "|" and depth == 0:
                parts.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        return parts

    def _split_at_comma(self, s: str) -> list[str]:
        """Split string at commas, respecting nesting."""
        parts = []
        current = ""
        depth = 0
        in_string = False

        for char in s:
            if char == '"' and not in_string:
                in_string = True
                current += char
            elif char == '"' and in_string:
                in_string = False
                current += char
            elif in_string:
                current += char
            elif char in "([{":
                depth += 1
                current += char
            elif char in ")]}":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                parts.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        return parts

    def _find_matching_paren(self, s: str, start: int) -> int:
        """Find matching closing parenthesis."""
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _find_matching_bracket(self, s: str, start: int) -> int:
        """Find matching closing bracket."""
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "[":
                depth += 1
            elif s[i] == "]":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _parse_string(self, s: str) -> str:
        """Parse a string literal."""
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        # Handle escape sequences
        result = ""
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                c = s[i + 1]
                if c == "n":
                    result += "\n"
                elif c == "t":
                    result += "\t"
                elif c == "r":
                    result += "\r"
                elif c == "\\":
                    result += "\\"
                elif c == '"':
                    result += '"'
                else:
                    result += c
                i += 2
            else:
                result += s[i]
                i += 1
        return result

    def _apply_filter(self, f: JqFilter, value: Any) -> list[Any]:
        """Apply a filter to a value, yielding results."""
        if f.type == "identity":
            return [value]

        elif f.type == "field":
            base = self._apply_filter(f.left, value) if f.left else [value]
            results = []
            for b in base:
                if isinstance(b, dict) and f.value in b:
                    results.append(b[f.value])
                elif isinstance(b, dict):
                    results.append(None)
            return results

        elif f.type == "index":
            base = self._apply_filter(f.left, value) if f.left else [value]
            results = []
            for b in base:
                if isinstance(b, list) and -len(b) <= f.value < len(b):
                    results.append(b[f.value])
                elif isinstance(b, dict) and str(f.value) in b:
                    results.append(b[str(f.value)])
            return results

        elif f.type == "slice":
            base = self._apply_filter(f.left, value) if f.left else [value]
            results = []
            start, stop = f.value
            for b in base:
                if isinstance(b, list):
                    results.append(b[start:stop])
            return results

        elif f.type == "iterator":
            base = self._apply_filter(f.left, value) if f.left else [value]
            results = []
            for b in base:
                if isinstance(b, list):
                    results.extend(b)
                elif isinstance(b, dict):
                    results.extend(b.values())
            return results

        elif f.type == "optional":
            try:
                return self._apply_filter(f.left, value)
            except Exception:
                return []

        elif f.type == "pipe":
            results = self._apply_filter(f.left, value)
            final = []
            for r in results:
                final.extend(self._apply_filter(f.right, r))
            return final

        elif f.type == "multi":
            results = []
            for sub in f.args:
                results.extend(self._apply_filter(sub, value))
            return results

        elif f.type == "collect":
            results = self._apply_filter(f.left, value)
            return [results]

        elif f.type == "object":
            obj = {}
            for key, val_filter in f.args:
                vals = self._apply_filter(val_filter, value)
                obj[key] = vals[0] if vals else None
            return [obj]

        elif f.type == "string":
            return [f.value]

        elif f.type == "number":
            return [f.value]

        elif f.type == "null":
            return [None]

        elif f.type == "true":
            return [True]

        elif f.type == "false":
            return [False]

        # Functions
        elif f.type == "keys":
            if isinstance(value, dict):
                return [sorted(value.keys())]
            elif isinstance(value, list):
                return [list(range(len(value)))]
            return [[]]

        elif f.type == "keys_unsorted":
            if isinstance(value, dict):
                return [list(value.keys())]
            elif isinstance(value, list):
                return [list(range(len(value)))]
            return [[]]

        elif f.type == "values":
            if isinstance(value, dict):
                return [list(value.values())]
            elif isinstance(value, list):
                return [value]
            return [[]]

        elif f.type == "length":
            if isinstance(value, (str, list, dict)):
                return [len(value)]
            elif value is None:
                return [0]
            return [1]

        elif f.type == "type":
            if value is None:
                return ["null"]
            elif isinstance(value, bool):
                return ["boolean"]
            elif isinstance(value, (int, float)):
                return ["number"]
            elif isinstance(value, str):
                return ["string"]
            elif isinstance(value, list):
                return ["array"]
            elif isinstance(value, dict):
                return ["object"]
            return ["unknown"]

        elif f.type == "empty":
            return []

        elif f.type == "not":
            return [not value]

        elif f.type == "add":
            if isinstance(value, list):
                if not value:
                    return [None]
                result = value[0]
                for v in value[1:]:
                    if isinstance(result, (int, float)) and isinstance(v, (int, float)):
                        result = result + v
                    elif isinstance(result, str) and isinstance(v, str):
                        result = result + v
                    elif isinstance(result, list) and isinstance(v, list):
                        result = result + v
                    elif isinstance(result, dict) and isinstance(v, dict):
                        result = {**result, **v}
                return [result]
            return [value]

        elif f.type == "first":
            if isinstance(value, list) and value:
                return [value[0]]
            return [None]

        elif f.type == "last":
            if isinstance(value, list) and value:
                return [value[-1]]
            return [None]

        elif f.type == "reverse":
            if isinstance(value, list):
                return [list(reversed(value))]
            return [value]

        elif f.type == "sort":
            if isinstance(value, list):
                return [sorted(value, key=lambda x: (x is None, x if isinstance(x, (int, float, str)) else str(x)))]
            return [value]

        elif f.type == "unique":
            if isinstance(value, list):
                seen = []
                for v in value:
                    if v not in seen:
                        seen.append(v)
                return [seen]
            return [value]

        elif f.type == "flatten":
            if isinstance(value, list):
                result = []
                for item in value:
                    if isinstance(item, list):
                        result.extend(item)
                    else:
                        result.append(item)
                return [result]
            return [value]

        elif f.type == "min":
            if isinstance(value, list) and value:
                return [min(value, key=lambda x: (x is None, x if isinstance(x, (int, float)) else float('inf')))]
            return [None]

        elif f.type == "max":
            if isinstance(value, list) and value:
                return [max(value, key=lambda x: (x is None, x if isinstance(x, (int, float)) else float('-inf')))]
            return [None]

        elif f.type == "select":
            results = self._apply_filter(f.left, value)
            if results and results[0]:
                return [value]
            return []

        elif f.type == "map":
            if isinstance(value, list):
                results = []
                for item in value:
                    sub_results = self._apply_filter(f.left, item)
                    results.extend(sub_results)
                return [results]
            return [value]

        elif f.type == "has":
            key_results = self._apply_filter(f.left, value)
            if key_results:
                key = key_results[0]
                if isinstance(value, dict):
                    return [key in value]
                elif isinstance(value, list) and isinstance(key, int):
                    return [0 <= key < len(value)]
            return [False]

        elif f.type == "contains":
            sub_results = self._apply_filter(f.left, value)
            if sub_results:
                sub = sub_results[0]
                return [self._contains(value, sub)]
            return [False]

        elif f.type == "split":
            sep_results = self._apply_filter(f.left, value)
            if sep_results and isinstance(value, str):
                sep = sep_results[0]
                return [value.split(sep)]
            return [[]]

        elif f.type == "join":
            sep_results = self._apply_filter(f.left, value)
            if sep_results and isinstance(value, list):
                sep = str(sep_results[0])
                return [sep.join(str(v) for v in value)]
            return [""]

        elif f.type == "test":
            pattern_results = self._apply_filter(f.left, value)
            if pattern_results and isinstance(value, str):
                pattern = pattern_results[0]
                try:
                    return [bool(re.search(pattern, value))]
                except re.error:
                    return [False]
            return [False]

        elif f.type == "ascii_downcase":
            if isinstance(value, str):
                return [value.lower()]
            return [value]

        elif f.type == "ascii_upcase":
            if isinstance(value, str):
                return [value.upper()]
            return [value]

        elif f.type == "ltrimstr":
            prefix_results = self._apply_filter(f.left, value)
            if prefix_results and isinstance(value, str):
                prefix = prefix_results[0]
                if value.startswith(prefix):
                    return [value[len(prefix):]]
            return [value]

        elif f.type == "rtrimstr":
            suffix_results = self._apply_filter(f.left, value)
            if suffix_results and isinstance(value, str):
                suffix = suffix_results[0]
                if value.endswith(suffix):
                    return [value[:-len(suffix)]]
            return [value]

        elif f.type == "startswith":
            prefix_results = self._apply_filter(f.left, value)
            if prefix_results and isinstance(value, str):
                return [value.startswith(prefix_results[0])]
            return [False]

        elif f.type == "endswith":
            suffix_results = self._apply_filter(f.left, value)
            if suffix_results and isinstance(value, str):
                return [value.endswith(suffix_results[0])]
            return [False]

        elif f.type == "tostring":
            if isinstance(value, str):
                return [value]
            return [json.dumps(value)]

        elif f.type == "tonumber":
            if isinstance(value, (int, float)):
                return [value]
            try:
                return [float(value) if "." in str(value) else int(value)]
            except (ValueError, TypeError):
                return [None]

        elif f.type == "format":
            format_name = f.value
            if format_name == "base64":
                if isinstance(value, str):
                    return [base64.b64encode(value.encode()).decode()]
            elif format_name == "base64d":
                if isinstance(value, str):
                    try:
                        return [base64.b64decode(value).decode()]
                    except Exception:
                        return [value]
            elif format_name == "uri":
                if isinstance(value, str):
                    return [uri_quote(value, safe="")]
            elif format_name == "csv":
                if isinstance(value, list):
                    return [",".join(self._csv_escape(v) for v in value)]
            elif format_name == "json":
                return [json.dumps(value)]
            elif format_name == "text":
                if isinstance(value, str):
                    return [value]
                return [str(value)]
            return [value]

        # Arithmetic and comparison
        elif f.type in ("+", "-", "*", "/", "%"):
            left_results = self._apply_filter(f.left, value)
            right_results = self._apply_filter(f.right, value)
            if left_results and right_results:
                left = left_results[0]
                right = right_results[0]
                try:
                    if f.type == "+":
                        if isinstance(left, str) and isinstance(right, str):
                            return [left + right]
                        if isinstance(left, list) and isinstance(right, list):
                            return [left + right]
                        return [left + right]
                    elif f.type == "-":
                        return [left - right]
                    elif f.type == "*":
                        return [left * right]
                    elif f.type == "/":
                        return [left / right]
                    elif f.type == "%":
                        return [left % right]
                except (TypeError, ZeroDivisionError):
                    return [None]
            return [None]

        elif f.type in ("==", "!=", "<", "<=", ">", ">="):
            left_results = self._apply_filter(f.left, value)
            right_results = self._apply_filter(f.right, value)
            if left_results and right_results:
                left = left_results[0]
                right = right_results[0]
                try:
                    if f.type == "==":
                        return [left == right]
                    elif f.type == "!=":
                        return [left != right]
                    elif f.type == "<":
                        return [left < right]
                    elif f.type == "<=":
                        return [left <= right]
                    elif f.type == ">":
                        return [left > right]
                    elif f.type == ">=":
                        return [left >= right]
                except TypeError:
                    return [False]
            return [False]

        elif f.type == "and":
            left_results = self._apply_filter(f.left, value)
            if left_results and left_results[0]:
                return self._apply_filter(f.right, value)
            return [False]

        elif f.type == "or":
            left_results = self._apply_filter(f.left, value)
            if left_results and left_results[0]:
                return left_results
            return self._apply_filter(f.right, value)

        # Update operators (+=, -=, *=, /=)
        elif f.type in ("+=", "-=", "*=", "/="):
            # Get the field to update (left side should be a field access)
            if f.left and f.left.type == "field" and isinstance(value, dict):
                field_name = f.left.value
                current_val = value.get(field_name)
                right_results = self._apply_filter(f.right, value)
                if right_results and current_val is not None:
                    right_val = right_results[0]
                    try:
                        if f.type == "+=":
                            new_val = current_val + right_val
                        elif f.type == "-=":
                            new_val = current_val - right_val
                        elif f.type == "*=":
                            new_val = current_val * right_val
                        elif f.type == "/=":
                            new_val = current_val / right_val
                        else:
                            new_val = current_val
                        return [{**value, field_name: new_val}]
                    except (TypeError, ZeroDivisionError):
                        return [value]
            return [value]

        elif f.type == "group_by":
            if isinstance(value, list) and f.left:
                groups: dict[str, list[Any]] = {}
                for item in value:
                    key_results = self._apply_filter(f.left, item)
                    key = json.dumps(key_results[0]) if key_results else "null"
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(item)
                return [list(groups.values())]
            return [value]

        # Math functions
        elif f.type == "floor":
            if isinstance(value, (int, float)):
                return [math.floor(value)]
            return [value]

        elif f.type == "ceil":
            if isinstance(value, (int, float)):
                return [math.ceil(value)]
            return [value]

        elif f.type == "round":
            if isinstance(value, (int, float)):
                return [round(value)]
            return [value]

        elif f.type == "sqrt":
            if isinstance(value, (int, float)) and value >= 0:
                result = math.sqrt(value)
                return [int(result) if result == int(result) else result]
            return [value]

        elif f.type == "fabs":
            if isinstance(value, (int, float)):
                return [abs(value)]
            return [value]

        # Entry functions
        elif f.type == "to_entries":
            if isinstance(value, dict):
                return [[{"key": k, "value": v} for k, v in value.items()]]
            return [value]

        elif f.type == "from_entries":
            if isinstance(value, list):
                obj = {}
                for item in value:
                    if isinstance(item, dict):
                        key = item.get("key") or item.get("name") or item.get("k")
                        val = item.get("value") if "value" in item else item.get("v")
                        if key is not None:
                            obj[key] = val
                return [obj]
            return [value]

        elif f.type == "with_entries":
            if isinstance(value, dict) and f.left:
                entries = [{"key": k, "value": v} for k, v in value.items()]
                new_entries = []
                for entry in entries:
                    results = self._apply_filter(f.left, entry)
                    if results:
                        new_entries.append(results[0])
                obj = {}
                for item in new_entries:
                    if isinstance(item, dict):
                        key = item.get("key")
                        val = item.get("value")
                        if key is not None:
                            obj[key] = val
                return [obj]
            return [value]

        # _by functions
        elif f.type == "sort_by":
            if isinstance(value, list) and f.left:
                items_with_keys = []
                for item in value:
                    key_results = self._apply_filter(f.left, item)
                    key = key_results[0] if key_results else None
                    items_with_keys.append((key, item))
                sorted_items = sorted(items_with_keys, key=lambda x: (x[0] is None, x[0]))
                return [[item for _, item in sorted_items]]
            return [value]

        elif f.type == "unique_by":
            if isinstance(value, list) and f.left:
                seen: dict[str, bool] = {}
                result = []
                for item in value:
                    key_results = self._apply_filter(f.left, item)
                    key = json.dumps(key_results[0]) if key_results else "null"
                    if key not in seen:
                        seen[key] = True
                        result.append(item)
                return [result]
            return [value]

        elif f.type == "min_by":
            if isinstance(value, list) and f.left and value:
                min_item = None
                min_key = None
                for item in value:
                    key_results = self._apply_filter(f.left, item)
                    key = key_results[0] if key_results else None
                    if min_item is None or (key is not None and (min_key is None or key < min_key)):
                        min_item = item
                        min_key = key
                return [min_item] if min_item is not None else [None]
            return [value]

        elif f.type == "max_by":
            if isinstance(value, list) and f.left and value:
                max_item = None
                max_key = None
                for item in value:
                    key_results = self._apply_filter(f.left, item)
                    key = key_results[0] if key_results else None
                    if max_item is None or (key is not None and (max_key is None or key > max_key)):
                        max_item = item
                        max_key = key
                return [max_item] if max_item is not None else [None]
            return [value]

        # Path functions
        elif f.type == "getpath":
            path_results = self._apply_filter(f.left, value)
            if path_results and isinstance(path_results[0], list):
                path = path_results[0]
                current = value
                for key in path:
                    if current is None:
                        return [None]
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif isinstance(current, list) and isinstance(key, int):
                        if 0 <= key < len(current):
                            current = current[key]
                        else:
                            return [None]
                    else:
                        return [None]
                return [current]
            return [None]

        elif f.type == "paths":
            def get_paths(obj: Any, current_path: list[Any] | None = None) -> list[list[Any]]:
                if current_path is None:
                    current_path = []
                result: list[list[Any]] = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        new_path = current_path + [k]
                        result.append(new_path)
                        result.extend(get_paths(v, new_path))
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        new_path = current_path + [i]
                        result.append(new_path)
                        result.extend(get_paths(v, new_path))
                return result
            return get_paths(value)

        # Containment
        elif f.type == "inside":
            x_results = self._apply_filter(f.left, value)
            if x_results:
                x = x_results[0]
                return [self._contains(x, value)]
            return [False]

        # Regex
        elif f.type == "match":
            pattern_results = self._apply_filter(f.left, value)
            if pattern_results and isinstance(value, str):
                pattern = pattern_results[0]
                try:
                    match_obj = re.search(pattern, value)
                    if match_obj:
                        return [{
                            "offset": match_obj.start(),
                            "length": match_obj.end() - match_obj.start(),
                            "string": match_obj.group(),
                            "captures": []
                        }]
                except re.error:
                    pass
            return [None]

        return [value]

    def _contains(self, a: Any, b: Any) -> bool:
        """Check if a contains b."""
        if isinstance(b, dict):
            if not isinstance(a, dict):
                return False
            for k, v in b.items():
                if k not in a or not self._contains(a[k], v):
                    return False
            return True
        elif isinstance(b, list):
            if not isinstance(a, list):
                return False
            for item in b:
                if not any(self._contains(x, item) for x in a):
                    return False
            return True
        else:
            return a == b

    def _csv_escape(self, v: Any) -> str:
        """Escape a value for CSV output."""
        s = str(v) if v is not None else ""
        if "," in s or '"' in s or "\n" in s:
            return '"' + s.replace('"', '""') + '"'
        return s

    def _format_value(self, value: Any, raw: bool, compact: bool) -> str:
        """Format a value for output."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            if raw:
                return value
            return json.dumps(value)
        elif isinstance(value, (int, float)):
            return json.dumps(value)
        else:
            if compact:
                return json.dumps(value, separators=(",", ":"))
            return json.dumps(value, indent=2)
