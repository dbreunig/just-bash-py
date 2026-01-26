"""Declare/typeset builtin implementation.

Usage: declare [-aAfFgiIlnrtux] [-p] [name[=value] ...]
       typeset [-aAfFgiIlnrtux] [-p] [name[=value] ...]

Options:
  -a  indexed array
  -A  associative array
  -f  functions only
  -F  function names only
  -g  global scope (in function context)
  -i  integer attribute
  -l  lowercase
  -n  nameref
  -p  print declarations
  -r  readonly
  -t  trace (functions)
  -u  uppercase
  -x  export
"""

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


def _result(stdout: str, stderr: str, exit_code: int) -> "ExecResult":
    """Create an ExecResult."""
    from ...types import ExecResult
    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


async def handle_declare(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the declare/typeset builtin."""
    # Parse options
    options = {
        "array": False,        # -a: indexed array
        "assoc": False,        # -A: associative array
        "function": False,     # -f: functions
        "func_names": False,   # -F: function names only
        "global": False,       # -g: global scope
        "integer": False,      # -i: integer
        "lowercase": False,    # -l: lowercase
        "nameref": False,      # -n: nameref
        "print": False,        # -p: print declarations
        "readonly": False,     # -r: readonly
        "trace": False,        # -t: trace
        "uppercase": False,    # -u: uppercase
        "export": False,       # -x: export
    }

    names: list[str] = []

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--":
            names.extend(args[i + 1:])
            break

        if arg.startswith("-") and len(arg) > 1 and arg[1] != "-":
            # Parse short options
            for c in arg[1:]:
                if c == "a":
                    options["array"] = True
                elif c == "A":
                    options["assoc"] = True
                elif c == "f":
                    options["function"] = True
                elif c == "F":
                    options["func_names"] = True
                elif c == "g":
                    options["global"] = True
                elif c == "i":
                    options["integer"] = True
                elif c == "l":
                    options["lowercase"] = True
                elif c == "n":
                    options["nameref"] = True
                elif c == "p":
                    options["print"] = True
                elif c == "r":
                    options["readonly"] = True
                elif c == "t":
                    options["trace"] = True
                elif c == "u":
                    options["uppercase"] = True
                elif c == "x":
                    options["export"] = True
                else:
                    return _result(
                        "",
                        f"bash: declare: -{c}: invalid option\n",
                        2
                    )
        else:
            names.append(arg)

        i += 1

    # Print mode: show variable declarations
    if options["print"]:
        return _print_declarations(ctx, names, options)

    # No names: list variables with matching attributes
    if not names:
        return _list_variables(ctx, options)

    # Process each name/assignment
    exit_code = 0
    stderr_parts = []

    for name_arg in names:
        # Parse name and optional value
        if "=" in name_arg:
            eq_idx = name_arg.index("=")
            name = name_arg[:eq_idx]
            value_str = name_arg[eq_idx + 1:]
        else:
            name = name_arg
            value_str = None

        # Handle array subscript in name: arr[idx]
        subscript = None
        if "[" in name and name.endswith("]"):
            bracket_idx = name.index("[")
            subscript = name[bracket_idx + 1:-1]
            name = name[:bracket_idx]

        # Validate identifier
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            stderr_parts.append(f"bash: declare: `{name_arg}': not a valid identifier\n")
            exit_code = 1
            continue

        # Handle array declaration
        if options["array"] or options["assoc"]:
            # Initialize array if not already set
            array_key = f"{name}__is_array"
            if array_key not in ctx.state.env:
                ctx.state.env[array_key] = "assoc" if options["assoc"] else "indexed"

            if value_str is not None:
                # Parse array assignment: (a b c) or ([0]=a [1]=b)
                if value_str.startswith("(") and value_str.endswith(")"):
                    inner = value_str[1:-1].strip()
                    _parse_array_assignment(ctx, name, inner, options["assoc"])
                elif subscript is not None:
                    # arr[idx]=value
                    ctx.state.env[f"{name}_{subscript}"] = value_str
                else:
                    # Simple value assignment to array[0]
                    ctx.state.env[f"{name}_0"] = value_str
        else:
            # Regular variable
            if value_str is not None:
                # Apply transformations
                if options["integer"]:
                    # Evaluate as integer
                    try:
                        value_str = str(_eval_integer(value_str, ctx))
                    except Exception:
                        value_str = "0"

                if options["lowercase"]:
                    value_str = value_str.lower()
                elif options["uppercase"]:
                    value_str = value_str.upper()

                if subscript is not None:
                    # Array element
                    ctx.state.env[f"{name}_{subscript}"] = value_str
                else:
                    ctx.state.env[name] = value_str
            elif name not in ctx.state.env:
                # Declare without value - just set type info
                if options["integer"]:
                    ctx.state.env[f"{name}__is_integer"] = "1"
                if options["lowercase"]:
                    ctx.state.env[f"{name}__is_lower"] = "1"
                if options["uppercase"]:
                    ctx.state.env[f"{name}__is_upper"] = "1"

    return _result("", "".join(stderr_parts), exit_code)


def _parse_array_assignment(ctx: "InterpreterContext", name: str, inner: str, is_assoc: bool) -> None:
    """Parse and assign array values from (a b c) or ([key]=value ...) syntax."""
    # Clear existing array elements
    to_remove = [k for k in ctx.state.env if k.startswith(f"{name}_") and not k.startswith(f"{name}__")]
    for k in to_remove:
        del ctx.state.env[k]

    # Simple word splitting for now - doesn't handle all quoting cases
    idx = 0
    i = 0

    while i < len(inner):
        # Skip whitespace
        while i < len(inner) and inner[i] in " \t":
            i += 1

        if i >= len(inner):
            break

        # Check for [key]=value syntax
        if inner[i] == "[":
            # Find closing bracket
            j = i + 1
            while j < len(inner) and inner[j] != "]":
                j += 1
            if j < len(inner) and j + 1 < len(inner) and inner[j + 1] == "=":
                key = inner[i + 1:j]
                # Find value
                value_start = j + 2
                value_end = value_start
                in_quote = None
                while value_end < len(inner):
                    c = inner[value_end]
                    if in_quote:
                        if c == in_quote:
                            in_quote = None
                        value_end += 1
                    elif c in "\"'":
                        in_quote = c
                        value_end += 1
                    elif c in " \t":
                        break
                    else:
                        value_end += 1

                value = inner[value_start:value_end]
                # Remove surrounding quotes if present
                if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                    value = value[1:-1]

                ctx.state.env[f"{name}_{key}"] = value
                i = value_end
                continue

        # Simple value - assign to next index
        value_start = i
        value_end = i
        in_quote = None
        while value_end < len(inner):
            c = inner[value_end]
            if in_quote:
                if c == in_quote:
                    in_quote = None
                value_end += 1
            elif c in "\"'":
                in_quote = c
                value_end += 1
            elif c in " \t":
                break
            else:
                value_end += 1

        value = inner[value_start:value_end]
        # Remove surrounding quotes if present
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]

        ctx.state.env[f"{name}_{idx}"] = value
        idx += 1
        i = value_end


def _eval_integer(expr: str, ctx: "InterpreterContext") -> int:
    """Evaluate an integer expression for declare -i."""
    from ..expansion import evaluate_arithmetic_sync
    from ...parser.parser import Parser

    expr = expr.strip()

    # Try direct integer
    try:
        return int(expr)
    except ValueError:
        pass

    # Try variable reference
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", expr):
        val = ctx.state.env.get(expr, "0")
        try:
            return int(val)
        except ValueError:
            return 0

    # Try arithmetic expression evaluation
    try:
        parser = Parser()
        arith_expr = parser._parse_arith_comma(expr)
        return evaluate_arithmetic_sync(ctx, arith_expr)
    except Exception:
        pass

    return 0


def _print_declarations(ctx: "InterpreterContext", names: list[str], options: dict) -> "ExecResult":
    """Print variable declarations."""
    lines = []

    if not names:
        # Print all matching variables
        for name in sorted(ctx.state.env.keys()):
            if name.startswith("_") or "__" in name:
                continue
            if name in ("?", "#", "$", "!", "-", "*", "@"):
                continue

            val = ctx.state.env[name]
            lines.append(f'declare -- {name}="{val}"')
    else:
        for name in names:
            if name in ctx.state.env:
                val = ctx.state.env[name]
                lines.append(f'declare -- {name}="{val}"')
            else:
                # Check if it's an array
                is_array = ctx.state.env.get(f"{name}__is_array")
                if is_array:
                    lines.append(f'declare -{("A" if is_array == "assoc" else "a")} {name}')

    return _result("\n".join(lines) + "\n" if lines else "", "", 0)


def _list_variables(ctx: "InterpreterContext", options: dict) -> "ExecResult":
    """List variables with matching attributes."""
    lines = []

    for name in sorted(ctx.state.env.keys()):
        if name.startswith("_") or "__" in name:
            continue
        if name in ("?", "#", "$", "!", "-", "*", "@"):
            continue

        val = ctx.state.env[name]
        lines.append(f'declare -- {name}="{val}"')

    return _result("\n".join(lines) + "\n" if lines else "", "", 0)
