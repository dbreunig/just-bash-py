"""Word Expansion System.

Handles shell word expansion including:
- Variable expansion ($VAR, ${VAR})
- Command substitution $(...)
- Arithmetic expansion $((...))
- Tilde expansion (~)
- Brace expansion {a,b,c}
- Glob expansion (*, ?, [...])
- Parameter operations (${VAR:-default}, ${VAR:+alt}, ${#VAR}, etc.)
"""

import fnmatch
import re
from typing import TYPE_CHECKING, Optional

from ..ast.types import (
    WordNode,
    WordPart,
    LiteralPart,
    SingleQuotedPart,
    DoubleQuotedPart,
    EscapedPart,
    ParameterExpansionPart,
    CommandSubstitutionPart,
    ArithmeticExpansionPart,
    TildeExpansionPart,
    GlobPart,
    BraceExpansionPart,
)
from .errors import BadSubstitutionError, ExecutionLimitError, ExitError, NounsetError

if TYPE_CHECKING:
    from .types import InterpreterContext


def get_variable(ctx: "InterpreterContext", name: str, check_nounset: bool = True) -> str:
    """Get a variable value from the environment.

    Handles special parameters like $?, $#, $@, $*, $0-$9, etc.
    Also handles array subscript syntax: arr[idx], arr[@], arr[*]
    """
    env = ctx.state.env

    # Check for array subscript syntax: name[subscript]
    array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', name)
    if array_match:
        arr_name = array_match.group(1)
        subscript = array_match.group(2)

        # Handle arr[@] and arr[*] - all elements
        if subscript in ("@", "*"):
            elements = get_array_elements(ctx, arr_name)
            return " ".join(val for _, val in elements)

        # Handle numeric or variable subscript
        try:
            # Try to evaluate subscript as arithmetic expression
            idx = _eval_array_subscript(ctx, subscript)
            # Negative indices count from end
            if idx < 0:
                elements = get_array_elements(ctx, arr_name)
                if elements:
                    max_idx = max(i for i, _ in elements)
                    idx = max_idx + 1 + idx
            key = f"{arr_name}_{idx}"
            if key in env:
                return env[key]
            elif check_nounset and ctx.state.options.nounset:
                raise NounsetError(name)
            return ""
        except (ValueError, TypeError):
            # Invalid subscript - return empty
            return ""

    # Special parameters
    if name == "?":
        return str(ctx.state.last_exit_code)
    elif name == "#":
        # Number of positional parameters
        count = 0
        while str(count + 1) in env:
            count += 1
        return str(count)
    elif name == "@" or name == "*":
        # All positional parameters
        params = []
        i = 1
        while str(i) in env:
            params.append(env[str(i)])
            i += 1
        return " ".join(params)
    elif name == "0":
        return env.get("0", "bash")
    elif name == "$":
        return str(env.get("$", "1"))  # PID (simulated)
    elif name == "!":
        return str(ctx.state.last_background_pid)
    elif name == "_":
        return ctx.state.last_arg
    elif name == "LINENO":
        return str(ctx.state.current_line)
    elif name == "RANDOM":
        import random
        return str(random.randint(0, 32767))
    elif name == "SECONDS":
        import time
        return str(int(time.time() - ctx.state.start_time))

    # Check for array subscript: arr[idx]
    array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', name)
    if array_match:
        array_name, subscript = array_match.groups()
        if subscript == "@" or subscript == "*":
            # Get all array elements
            elements = get_array_elements(ctx, array_name)
            return " ".join(v for _, v in elements)
        else:
            # Single element
            try:
                idx = int(subscript)
            except ValueError:
                # Try to evaluate as variable
                idx_val = env.get(subscript, "0")
                try:
                    idx = int(idx_val)
                except ValueError:
                    idx = 0
            return env.get(f"{array_name}_{idx}", "")

    # Regular variable
    value = env.get(name)

    if value is None:
        # Check nounset (set -u)
        if check_nounset and ctx.state.options.nounset:
            raise NounsetError(name, "", f"bash: {name}: unbound variable\n")
        return ""

    return value


def get_array_elements(ctx: "InterpreterContext", name: str) -> list[tuple[int, str]]:
    """Get all elements of an array as (index, value) pairs."""
    elements = []
    env = ctx.state.env

    # Look for name_0, name_1, etc.
    prefix = f"{name}_"
    for key, value in env.items():
        if key.startswith(prefix) and not key.endswith("__length"):
            try:
                idx = int(key[len(prefix):])
                elements.append((idx, value))
            except ValueError:
                pass

    # Sort by index
    elements.sort(key=lambda x: x[0])
    return elements


def is_array(ctx: "InterpreterContext", name: str) -> bool:
    """Check if a variable is an array."""
    prefix = f"{name}_"
    for key in ctx.state.env:
        if key.startswith(prefix) and not key.endswith("__length"):
            return True
    return False


def _eval_array_subscript(ctx: "InterpreterContext", subscript: str) -> int:
    """Evaluate an array subscript to an integer index.

    Supports:
    - Literal integers: arr[0], arr[42]
    - Variable references: arr[i], arr[idx], arr[$i]
    - Simple arithmetic: arr[i+1], arr[n-1]
    """
    subscript = subscript.strip()

    # First, expand any $VAR references in the subscript
    expanded = _expand_subscript_vars(ctx, subscript)

    # Try direct integer
    try:
        return int(expanded)
    except ValueError:
        pass

    # Try variable reference (bare name without $)
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', expanded):
        val = ctx.state.env.get(expanded, "0")
        try:
            return int(val)
        except ValueError:
            return 0

    # Try arithmetic expression - expand bare variables first
    arith_expanded = _expand_arith_vars(ctx, expanded)
    try:
        # Use Python eval with restricted builtins for safety
        result = eval(arith_expanded, {"__builtins__": {}}, {})
        return int(result)
    except Exception:
        return 0


def _expand_arith_vars(ctx: "InterpreterContext", expr: str) -> str:
    """Expand bare variable names in arithmetic expression."""
    # Replace variable names with their values
    result = []
    i = 0
    while i < len(expr):
        # Check for variable name (not preceded by digit)
        if (expr[i].isalpha() or expr[i] == '_'):
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            var_name = expr[i:j]
            val = ctx.state.env.get(var_name, "0")
            try:
                result.append(str(int(val)))
            except ValueError:
                result.append("0")
            i = j
        else:
            result.append(expr[i])
            i += 1
    return ''.join(result)


def _expand_subscript_vars(ctx: "InterpreterContext", subscript: str) -> str:
    """Expand $VAR and ${VAR} references in array subscript."""
    result = []
    i = 0
    while i < len(subscript):
        if subscript[i] == '$':
            if i + 1 < len(subscript):
                if subscript[i + 1] == '{':
                    # ${VAR} syntax
                    j = subscript.find('}', i + 2)
                    if j != -1:
                        var_name = subscript[i + 2:j]
                        val = ctx.state.env.get(var_name, "0")
                        result.append(val)
                        i = j + 1
                        continue
                elif subscript[i + 1].isalpha() or subscript[i + 1] == '_':
                    # $VAR syntax
                    j = i + 1
                    while j < len(subscript) and (subscript[j].isalnum() or subscript[j] == '_'):
                        j += 1
                    var_name = subscript[i + 1:j]
                    val = ctx.state.env.get(var_name, "0")
                    result.append(val)
                    i = j
                    continue
        result.append(subscript[i])
        i += 1
    return ''.join(result)


def get_array_keys(ctx: "InterpreterContext", name: str) -> list[str]:
    """Get all keys of an array (indices for indexed arrays, keys for associative)."""
    keys = []
    env = ctx.state.env
    prefix = f"{name}_"

    for key in env:
        if key.startswith(prefix) and not key.startswith(f"{name}__"):
            idx_part = key[len(prefix):]
            keys.append(idx_part)

    # Sort numerically if all indices are numbers
    try:
        keys.sort(key=int)
    except ValueError:
        keys.sort()

    return keys


def expand_word(ctx: "InterpreterContext", word: WordNode) -> str:
    """Expand a word synchronously (no command substitution)."""
    parts = []
    for part in word.parts:
        parts.append(expand_part_sync(ctx, part))
    return "".join(parts)


async def expand_word_async(ctx: "InterpreterContext", word: WordNode) -> str:
    """Expand a word asynchronously (supports command substitution)."""
    parts = []
    for part in word.parts:
        parts.append(await expand_part(ctx, part))
    return "".join(parts)


def expand_part_sync(ctx: "InterpreterContext", part: WordPart, in_double_quotes: bool = False) -> str:
    """Expand a word part synchronously."""
    if isinstance(part, LiteralPart):
        return part.value
    elif isinstance(part, SingleQuotedPart):
        return part.value
    elif isinstance(part, EscapedPart):
        return part.value
    elif isinstance(part, DoubleQuotedPart):
        # Recursively expand parts inside double quotes
        result = []
        for p in part.parts:
            result.append(expand_part_sync(ctx, p, in_double_quotes=True))
        return "".join(result)
    elif isinstance(part, ParameterExpansionPart):
        return expand_parameter(ctx, part, in_double_quotes)
    elif isinstance(part, TildeExpansionPart):
        if in_double_quotes:
            # Tilde is literal inside double quotes
            return "~" if part.user is None else f"~{part.user}"
        if part.user is None:
            return ctx.state.env.get("HOME", "/home/user")
        elif part.user == "root":
            return "/root"
        else:
            return f"~{part.user}"
    elif isinstance(part, GlobPart):
        return part.pattern
    elif isinstance(part, ArithmeticExpansionPart):
        # Evaluate arithmetic synchronously
        # Unwrap ArithmeticExpressionNode to get the actual ArithExpr
        expr = part.expression.expression if part.expression else None
        return str(evaluate_arithmetic_sync(ctx, expr))
    elif isinstance(part, BraceExpansionPart):
        # Expand brace items
        results = []
        for item in part.items:
            if item.type == "Range":
                expanded = expand_brace_range(item.start, item.end, item.step)
                results.extend(expanded)
            else:
                results.append(expand_word(ctx, item.word))
        return " ".join(results)
    elif isinstance(part, CommandSubstitutionPart):
        # Command substitution requires async
        raise RuntimeError("Command substitution requires async expansion")
    else:
        return ""


async def expand_part(ctx: "InterpreterContext", part: WordPart, in_double_quotes: bool = False) -> str:
    """Expand a word part asynchronously."""
    if isinstance(part, LiteralPart):
        return part.value
    elif isinstance(part, SingleQuotedPart):
        return part.value
    elif isinstance(part, EscapedPart):
        return part.value
    elif isinstance(part, DoubleQuotedPart):
        result = []
        for p in part.parts:
            result.append(await expand_part(ctx, p, in_double_quotes=True))
        return "".join(result)
    elif isinstance(part, ParameterExpansionPart):
        return await expand_parameter_async(ctx, part, in_double_quotes)
    elif isinstance(part, TildeExpansionPart):
        if in_double_quotes:
            return "~" if part.user is None else f"~{part.user}"
        if part.user is None:
            return ctx.state.env.get("HOME", "/home/user")
        elif part.user == "root":
            return "/root"
        else:
            return f"~{part.user}"
    elif isinstance(part, GlobPart):
        return part.pattern
    elif isinstance(part, ArithmeticExpansionPart):
        # Unwrap ArithmeticExpressionNode to get the actual ArithExpr
        expr = part.expression.expression if part.expression else None
        return str(await evaluate_arithmetic(ctx, expr))
    elif isinstance(part, BraceExpansionPart):
        results = []
        for item in part.items:
            if item.type == "Range":
                expanded = expand_brace_range(item.start, item.end, item.step)
                results.extend(expanded)
            else:
                results.append(await expand_word_async(ctx, item.word))
        return " ".join(results)
    elif isinstance(part, CommandSubstitutionPart):
        # Execute the command substitution
        try:
            result = await ctx.execute_script(part.body)
            ctx.state.last_exit_code = result.exit_code
            ctx.state.env["?"] = str(result.exit_code)
            # Remove trailing newlines
            return result.stdout.rstrip("\n")
        except ExecutionLimitError:
            raise
        except ExitError as e:
            ctx.state.last_exit_code = e.exit_code
            ctx.state.env["?"] = str(e.exit_code)
            return e.stdout.rstrip("\n")
    else:
        return ""


def expand_parameter(ctx: "InterpreterContext", part: ParameterExpansionPart, in_double_quotes: bool = False) -> str:
    """Expand a parameter expansion synchronously."""
    parameter = part.parameter
    operation = part.operation

    # Handle variable indirection: ${!var}
    if parameter.startswith("!"):
        indirect_name = parameter[1:]

        # ${!arr[@]} or ${!arr[*]} - get array keys
        array_keys_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[[@*]\]$', indirect_name)
        if array_keys_match:
            arr_name = array_keys_match.group(1)
            keys = get_array_keys(ctx, arr_name)
            return " ".join(keys)

        # ${!prefix*} or ${!prefix@} - get variable names starting with prefix
        prefix_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)[@*]$', indirect_name)
        if prefix_match:
            prefix = prefix_match.group(1)
            matching = [k for k in ctx.state.env.keys()
                       if k.startswith(prefix) and not "__" in k]
            return " ".join(sorted(matching))

        # ${!var} - variable indirection
        ref_name = get_variable(ctx, indirect_name, False)
        if ref_name:
            return get_variable(ctx, ref_name, False)
        return ""

    # Check if operation handles unset variables
    skip_nounset = operation and operation.type in (
        "DefaultValue", "AssignDefault", "UseAlternative", "ErrorIfUnset"
    )

    value = get_variable(ctx, parameter, not skip_nounset)

    if not operation:
        return value

    is_unset = parameter not in ctx.state.env
    is_empty = value == ""

    if operation.type == "DefaultValue":
        use_default = is_unset or (operation.check_empty and is_empty)
        if use_default and operation.word:
            return expand_word(ctx, operation.word)
        return value

    elif operation.type == "AssignDefault":
        use_default = is_unset or (operation.check_empty and is_empty)
        if use_default and operation.word:
            default_value = expand_word(ctx, operation.word)
            ctx.state.env[parameter] = default_value
            return default_value
        return value

    elif operation.type == "ErrorIfUnset":
        should_error = is_unset or (operation.check_empty and is_empty)
        if should_error:
            message = expand_word(ctx, operation.word) if operation.word else f"{parameter}: parameter null or not set"
            raise ExitError(1, "", f"bash: {message}\n")
        return value

    elif operation.type == "UseAlternative":
        use_alt = not (is_unset or (operation.check_empty and is_empty))
        if use_alt and operation.word:
            return expand_word(ctx, operation.word)
        return ""

    elif operation.type == "Length":
        # Check for array length
        array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[[@*]\]$', parameter)
        if array_match:
            elements = get_array_elements(ctx, array_match.group(1))
            return str(len(elements))
        return str(len(value))

    elif operation.type == "Substring":
        offset = operation.offset if hasattr(operation, 'offset') else 0
        length = operation.length if hasattr(operation, 'length') else None

        # Handle negative offset
        if offset < 0:
            offset = max(0, len(value) + offset)

        if length is not None:
            if length < 0:
                end_pos = len(value) + length
                return value[offset:max(offset, end_pos)]
            return value[offset:offset + length]
        return value[offset:]

    elif operation.type == "PatternRemoval":
        pattern = expand_word(ctx, operation.pattern) if operation.pattern else ""
        greedy = operation.greedy
        from_end = operation.side == "suffix"

        # Convert glob pattern to regex
        regex_pattern = glob_to_regex(pattern, greedy, from_end)

        if from_end:
            # Remove from end: ${var%pattern} or ${var%%pattern}
            match = re.search(regex_pattern + "$", value)
            if match:
                return value[:match.start()]
        else:
            # Remove from start: ${var#pattern} or ${var##pattern}
            match = re.match(regex_pattern, value)
            if match:
                return value[match.end():]
        return value

    elif operation.type == "PatternReplace":
        pattern = expand_word(ctx, operation.pattern) if operation.pattern else ""
        replacement = expand_word(ctx, operation.replacement) if operation.replacement else ""
        replace_all = operation.replace_all

        regex_pattern = glob_to_regex(pattern, greedy=False)

        if replace_all:
            return re.sub(regex_pattern, replacement, value)
        else:
            return re.sub(regex_pattern, replacement, value, count=1)

    elif operation.type == "CaseModification":
        # ${var^^} or ${var,,} for case conversion
        if operation.direction == "upper":
            if operation.all:
                return value.upper()
            return value[0].upper() + value[1:] if value else ""
        else:
            if operation.all:
                return value.lower()
            return value[0].lower() + value[1:] if value else ""

    elif operation.type == "Transform":
        # ${var@Q}, ${var@P}, ${var@a}, ${var@A}, ${var@E}, ${var@K}
        op = operation.operator
        if op == "Q":
            # Quoted form - escape special chars and wrap in quotes
            if not value:
                return "''"
            # Simple quoting - use single quotes if no single quotes in value
            if "'" not in value:
                return f"'{value}'"
            # Use $'...' quoting with escapes
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"$'{escaped}'"
        elif op == "E":
            # Expand escape sequences like $'...'
            result = []
            i = 0
            while i < len(value):
                if value[i] == '\\' and i + 1 < len(value):
                    c = value[i + 1]
                    if c == 'n':
                        result.append('\n')
                    elif c == 't':
                        result.append('\t')
                    elif c == 'r':
                        result.append('\r')
                    elif c == '\\':
                        result.append('\\')
                    elif c == "'":
                        result.append("'")
                    elif c == '"':
                        result.append('"')
                    else:
                        result.append(value[i:i+2])
                    i += 2
                else:
                    result.append(value[i])
                    i += 1
            return ''.join(result)
        elif op == "P":
            # Prompt expansion - for now just return value
            # Full implementation would expand \u, \h, \w, etc.
            return value
        elif op == "A":
            # Assignment statement form
            return f"{parameter}={_shell_quote(value)}"
        elif op == "a":
            # Attributes - check if array, readonly, etc.
            attrs = []
            if ctx.state.env.get(f"{parameter}__is_array") == "indexed":
                attrs.append("a")
            elif ctx.state.env.get(f"{parameter}__is_array") == "associative":
                attrs.append("A")
            readonly_set = ctx.state.env.get("__readonly__", "").split()
            if parameter in readonly_set:
                attrs.append("r")
            return "".join(attrs)
        elif op == "K":
            # Key-value pairs for associative arrays
            # For indexed arrays, show index=value pairs
            elements = get_array_elements(ctx, parameter)
            if elements:
                pairs = [f"[{idx}]=\"{val}\"" for idx, val in elements]
                return " ".join(pairs)
            return value

    return value


def _shell_quote(s: str) -> str:
    """Quote a string for shell use."""
    if not s:
        return "''"
    if "'" not in s:
        return f"'{s}'"
    return f"$'{s.replace(chr(92), chr(92)+chr(92)).replace(chr(39), chr(92)+chr(39))}'"


async def expand_parameter_async(ctx: "InterpreterContext", part: ParameterExpansionPart, in_double_quotes: bool = False) -> str:
    """Expand a parameter expansion asynchronously."""
    # For now, use sync version - async needed for command substitution in default values
    return expand_parameter(ctx, part, in_double_quotes)


def expand_brace_range(start: int, end: int, step: int = 1) -> list[str]:
    """Expand a brace range like {1..10} or {a..z}."""
    results = []

    if step == 0:
        step = 1

    if start <= end:
        i = start
        while i <= end:
            results.append(str(i))
            i += abs(step)
    else:
        i = start
        while i >= end:
            results.append(str(i))
            i -= abs(step)

    return results


def glob_to_regex(pattern: str, greedy: bool = True, from_end: bool = False) -> str:
    """Convert a glob pattern to a regex pattern."""
    result = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if greedy:
                result.append(".*")
            else:
                result.append(".*?")
        elif c == "?":
            result.append(".")
        elif c == "[":
            # Character class
            j = i + 1
            if j < len(pattern) and pattern[j] == "!":
                result.append("[^")
                j += 1
            else:
                result.append("[")
            while j < len(pattern) and pattern[j] != "]":
                result.append(pattern[j])
                j += 1
            result.append("]")
            i = j
        elif c in r"\^$.|+(){}":
            result.append("\\" + c)
        else:
            result.append(c)
        i += 1
    return "".join(result)


async def expand_word_with_glob(
    ctx: "InterpreterContext",
    word: WordNode,
) -> dict:
    """Expand a word with glob expansion support.

    Returns dict with 'values' (list of strings) and 'quoted' (bool).
    """
    # Check if word contains any quoted parts
    has_quoted = any(
        isinstance(p, (SingleQuotedPart, DoubleQuotedPart, EscapedPart))
        for p in word.parts
    )

    # Special handling for "$@" and "$*" in double quotes
    # "$@" expands to multiple words (one per positional parameter)
    # "$*" expands to single word (params joined by IFS)
    if len(word.parts) == 1 and isinstance(word.parts[0], DoubleQuotedPart):
        dq = word.parts[0]
        if len(dq.parts) == 1 and isinstance(dq.parts[0], ParameterExpansionPart):
            param_part = dq.parts[0]
            if param_part.parameter == "@" and param_part.operation is None:
                # "$@" - return each positional parameter as separate word
                params = _get_positional_params(ctx)
                if not params:
                    return {"values": [], "quoted": True}
                return {"values": params, "quoted": True}
            elif param_part.parameter == "*" and param_part.operation is None:
                # "$*" - return all params joined by first char of IFS
                params = _get_positional_params(ctx)
                ifs = ctx.state.env.get("IFS", " \t\n")
                sep = ifs[0] if ifs else ""
                return {"values": [sep.join(params)] if params else [""], "quoted": True}

    # Handle more complex cases with "$@" embedded in other content
    # e.g., "prefix$@suffix" -> ["prefix$1", "$2", ..., "$nsuffix"]
    values = await _expand_word_with_at(ctx, word)
    if values is not None:
        return {"values": values, "quoted": True}

    # Expand the word
    value = await expand_word_async(ctx, word)

    # For unquoted words, perform IFS word splitting
    if not has_quoted:
        # Check for glob patterns first
        if any(c in value for c in "*?["):
            matches = await glob_expand(ctx, value)
            if matches:
                return {"values": matches, "quoted": False}

        # Perform IFS word splitting
        if value == "":
            return {"values": [], "quoted": False}

        # Check if the word contained parameter/command expansion that should be split
        has_expansion = any(
            isinstance(p, (ParameterExpansionPart, CommandSubstitutionPart, ArithmeticExpansionPart))
            for p in word.parts
        )
        if has_expansion:
            ifs = ctx.state.env.get("IFS", " \t\n")
            if ifs:
                # Split on IFS characters
                words = _split_on_ifs(value, ifs)
                return {"values": words, "quoted": False}

    return {"values": [value], "quoted": has_quoted}


def _split_on_ifs(value: str, ifs: str) -> list[str]:
    """Split a string on IFS characters.

    IFS whitespace (space, tab, newline) is treated specially:
    - Leading/trailing IFS whitespace is trimmed
    - Consecutive IFS whitespace is treated as one delimiter
    Non-whitespace IFS characters produce empty fields.
    """
    if not value:
        return []

    # Identify which IFS chars are whitespace
    ifs_whitespace = "".join(c for c in ifs if c in " \t\n")
    ifs_nonws = "".join(c for c in ifs if c not in " \t\n")

    # If all IFS chars are whitespace, simple split
    if not ifs_nonws:
        return value.split()

    # Complex case: mix of whitespace and non-whitespace IFS
    result = []
    current = []
    i = 0
    while i < len(value):
        c = value[i]
        if c in ifs_whitespace:
            # Skip leading/consecutive whitespace
            if current:
                result.append("".join(current))
                current = []
            # Skip all consecutive whitespace
            while i < len(value) and value[i] in ifs_whitespace:
                i += 1
        elif c in ifs_nonws:
            # Non-whitespace delimiter produces field
            result.append("".join(current))
            current = []
            i += 1
        else:
            current.append(c)
            i += 1

    if current:
        result.append("".join(current))

    return result


def _get_positional_params(ctx: "InterpreterContext") -> list[str]:
    """Get all positional parameters ($1, $2, ...) as a list."""
    params = []
    i = 1
    while str(i) in ctx.state.env:
        params.append(ctx.state.env[str(i)])
        i += 1
    return params


async def _expand_word_with_at(ctx: "InterpreterContext", word: WordNode) -> list[str] | None:
    """Expand a word that may contain $@ in double quotes.

    Returns None if the word doesn't contain $@ in double quotes.
    Returns list of expanded values if it does.
    """
    # Check if any part contains $@ in double quotes
    has_at_in_quotes = False
    for part in word.parts:
        if isinstance(part, DoubleQuotedPart):
            for inner in part.parts:
                if (isinstance(inner, ParameterExpansionPart) and
                    inner.parameter == "@" and inner.operation is None):
                    has_at_in_quotes = True
                    break

    if not has_at_in_quotes:
        return None

    # Get positional parameters
    params = _get_positional_params(ctx)
    if not params:
        # No positional params - expand without $@
        result = []
        for part in word.parts:
            if isinstance(part, DoubleQuotedPart):
                inner_result = []
                for inner in part.parts:
                    if (isinstance(inner, ParameterExpansionPart) and
                        inner.parameter == "@" and inner.operation is None):
                        pass  # Skip $@ - produces nothing
                    else:
                        inner_result.append(await expand_part(ctx, inner, in_double_quotes=True))
                result.append("".join(inner_result))
            else:
                result.append(await expand_part(ctx, part))
        return ["".join(result)] if "".join(result) else []

    # Complex case: expand $@ to multiple words
    # For "prefix$@suffix", produce ["prefix$1", "$2", ..., "$n-1", "$nsuffix"]
    # Build prefix (everything before $@) and suffix (everything after $@)
    prefix_parts = []
    suffix_parts = []
    found_at = False

    for part in word.parts:
        if isinstance(part, DoubleQuotedPart):
            for inner in part.parts:
                if (isinstance(inner, ParameterExpansionPart) and
                    inner.parameter == "@" and inner.operation is None):
                    found_at = True
                elif not found_at:
                    prefix_parts.append(await expand_part(ctx, inner, in_double_quotes=True))
                else:
                    suffix_parts.append(await expand_part(ctx, inner, in_double_quotes=True))
        elif not found_at:
            prefix_parts.append(await expand_part(ctx, part))
        else:
            suffix_parts.append(await expand_part(ctx, part))

    prefix = "".join(prefix_parts)
    suffix = "".join(suffix_parts)

    # Build result: first param gets prefix, last param gets suffix
    if len(params) == 1:
        return [prefix + params[0] + suffix]
    else:
        result = [prefix + params[0]]
        result.extend(params[1:-1])
        result.append(params[-1] + suffix)
        return result


async def glob_expand(ctx: "InterpreterContext", pattern: str) -> list[str]:
    """Expand a glob pattern against the filesystem."""
    import os

    cwd = ctx.state.cwd
    fs = ctx.fs

    # Handle absolute vs relative paths
    if pattern.startswith("/"):
        base_dir = "/"
        pattern = pattern[1:]
    else:
        base_dir = cwd

    # Split pattern into parts
    parts = pattern.split("/")

    async def expand_parts(current_dir: str, remaining_parts: list[str]) -> list[str]:
        if not remaining_parts:
            return [current_dir]

        part = remaining_parts[0]
        rest = remaining_parts[1:]

        # Check if this part has glob characters
        if not any(c in part for c in "*?["):
            # No glob - just check if path exists
            new_path = os.path.join(current_dir, part)
            if await fs.exists(new_path):
                return await expand_parts(new_path, rest)
            return []

        # Glob expansion needed
        try:
            entries = await fs.readdir(current_dir)
        except (FileNotFoundError, NotADirectoryError):
            return []

        matches = []
        for entry in entries:
            if fnmatch.fnmatch(entry, part):
                new_path = os.path.join(current_dir, entry)
                if rest:
                    # More parts to match - entry must be a directory
                    if await fs.is_directory(new_path):
                        matches.extend(await expand_parts(new_path, rest))
                else:
                    matches.append(new_path)

        return sorted(matches)

    results = await expand_parts(base_dir, parts)

    # Return relative paths if pattern was relative
    if not pattern.startswith("/") and results:
        results = [os.path.relpath(r, cwd) if r.startswith(cwd) else r for r in results]

    return results


def _parse_base_n_value(value_str: str, base: int) -> int:
    """Parse a value in base N (2-64).

    Digits:
    - 0-9 = values 0-9
    - a-z = values 10-35
    - A-Z = values 36-61 (or 10-35 if base <= 36)
    - @ = 62, _ = 63
    """
    result = 0
    for char in value_str:
        if char.isdigit():
            digit = int(char)
        elif 'a' <= char <= 'z':
            digit = ord(char) - ord('a') + 10
        elif 'A' <= char <= 'Z':
            if base <= 36:
                # Case insensitive for bases <= 36
                digit = ord(char.lower()) - ord('a') + 10
            else:
                # A-Z are 36-61 for bases > 36
                digit = ord(char) - ord('A') + 36
        elif char == '@':
            digit = 62
        elif char == '_':
            digit = 63
        else:
            raise ValueError(f"Invalid digit {char} for base {base}")

        if digit >= base:
            raise ValueError(f"Digit {char} out of range for base {base}")

        result = result * base + digit
    return result


def evaluate_arithmetic_sync(ctx: "InterpreterContext", expr) -> int:
    """Evaluate an arithmetic expression synchronously."""
    # Simple implementation for basic arithmetic
    if hasattr(expr, 'type'):
        if expr.type == "ArithNumber":
            return expr.value
        elif expr.type == "ArithVariable":
            name = expr.name
            # Handle dynamic base constants like $base#value or base#value where base is a variable
            if "#" in name:
                hash_pos = name.index("#")
                base_part = name[:hash_pos]
                value_part = name[hash_pos + 1:]
                # Check if base_part is a variable reference
                if base_part.startswith("$"):
                    base_var = base_part[1:]
                    if base_var.startswith("{") and base_var.endswith("}"):
                        base_var = base_var[1:-1]
                    base_str = get_variable(ctx, base_var, False)
                else:
                    # Try treating base_part as a variable name
                    base_str = get_variable(ctx, base_part, False)
                    if not base_str:
                        # Fall back to treating as literal
                        base_str = base_part
                try:
                    base = int(base_str)
                    if 2 <= base <= 64:
                        return _parse_base_n_value(value_part, base)
                except (ValueError, TypeError):
                    pass
            val = get_variable(ctx, name, False)
            try:
                return int(val) if val else 0
            except ValueError:
                return 0
        elif expr.type == "ArithBinary":
            left = evaluate_arithmetic_sync(ctx, expr.left)
            right = evaluate_arithmetic_sync(ctx, expr.right)
            op = expr.operator
            if op == "+":
                return left + right
            elif op == "-":
                return left - right
            elif op == "*":
                return left * right
            elif op == "/":
                return left // right if right != 0 else 0
            elif op == "%":
                return left % right if right != 0 else 0
            elif op == "**":
                return left ** right
            elif op == "<":
                return 1 if left < right else 0
            elif op == ">":
                return 1 if left > right else 0
            elif op == "<=":
                return 1 if left <= right else 0
            elif op == ">=":
                return 1 if left >= right else 0
            elif op == "==":
                return 1 if left == right else 0
            elif op == "!=":
                return 1 if left != right else 0
            elif op == "&&":
                return 1 if left and right else 0
            elif op == "||":
                return 1 if left or right else 0
            elif op == "&":
                return left & right
            elif op == "|":
                return left | right
            elif op == "^":
                return left ^ right
            elif op == "<<":
                return left << right
            elif op == ">>":
                return left >> right
            elif op == ",":
                # Comma operator: evaluate both, return right
                return right
        elif expr.type == "ArithUnary":
            op = expr.operator
            # Handle increment/decrement specially (need variable name)
            if op in ("++", "--"):
                if hasattr(expr.operand, 'name'):
                    var_name = expr.operand.name
                    val = get_variable(ctx, var_name, False)
                    try:
                        current = int(val) if val else 0
                    except ValueError:
                        current = 0
                    new_val = current + 1 if op == "++" else current - 1

                    # Handle array element syntax: arr[idx]
                    array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', var_name)
                    if array_match:
                        arr_name = array_match.group(1)
                        subscript = array_match.group(2)
                        idx = _eval_array_subscript(ctx, subscript)
                        ctx.state.env[f"{arr_name}_{idx}"] = str(new_val)
                    else:
                        ctx.state.env[var_name] = str(new_val)

                    # Prefix returns new value, postfix returns old value
                    return new_val if expr.prefix else current
                else:
                    # Operand is not a variable - just evaluate
                    operand = evaluate_arithmetic_sync(ctx, expr.operand)
                    return operand + 1 if op == "++" else operand - 1
            operand = evaluate_arithmetic_sync(ctx, expr.operand)
            if op == "-":
                return -operand
            elif op == "+":
                return operand
            elif op == "!":
                return 0 if operand else 1
            elif op == "~":
                return ~operand
        elif expr.type == "ArithTernary":
            cond = evaluate_arithmetic_sync(ctx, expr.condition)
            if cond:
                return evaluate_arithmetic_sync(ctx, expr.consequent)
            else:
                return evaluate_arithmetic_sync(ctx, expr.alternate)
        elif expr.type == "ArithAssignment":
            # Handle compound assignments: = += -= *= /= %= <<= >>= &= |= ^=
            op = getattr(expr, 'operator', '=')
            var_name = getattr(expr, 'variable', None) or getattr(expr, 'name', None)
            rhs = evaluate_arithmetic_sync(ctx, expr.value)

            if op == '=':
                value = rhs
            else:
                # Get current value for compound operators
                current = 0
                if var_name:
                    val = get_variable(ctx, var_name, False)
                    try:
                        current = int(val) if val else 0
                    except ValueError:
                        current = 0

                if op == '+=':
                    value = current + rhs
                elif op == '-=':
                    value = current - rhs
                elif op == '*=':
                    value = current * rhs
                elif op == '/=':
                    value = current // rhs if rhs != 0 else 0
                elif op == '%=':
                    value = current % rhs if rhs != 0 else 0
                elif op == '<<=':
                    value = current << rhs
                elif op == '>>=':
                    value = current >> rhs
                elif op == '&=':
                    value = current & rhs
                elif op == '|=':
                    value = current | rhs
                elif op == '^=':
                    value = current ^ rhs
                else:
                    value = rhs

            if var_name:
                ctx.state.env[var_name] = str(value)
            return value
        elif expr.type == "ArithGroup":
            return evaluate_arithmetic_sync(ctx, expr.expression)
    return 0


async def evaluate_arithmetic(ctx: "InterpreterContext", expr) -> int:
    """Evaluate an arithmetic expression asynchronously."""
    # For now, use sync version
    return evaluate_arithmetic_sync(ctx, expr)
