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
    from ..types import InterpreterContext, VariableStore
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

    # Handle -f or -F options (functions)
    if options["function"] or options["func_names"]:
        return _handle_functions(ctx, names, options)

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

        # Handle nameref declaration
        from ..types import VariableStore
        if options["nameref"] and isinstance(ctx.state.env, VariableStore):
            if value_str is not None:
                ctx.state.env.set_nameref(name, value_str)
            else:
                # declare -n without value just marks as nameref type
                ctx.state.env.set_attribute(name, "n")
            continue

        # Handle readonly attribute
        if options["readonly"] and isinstance(ctx.state.env, VariableStore):
            ctx.state.env.set_attribute(name, "r")
            ctx.state.readonly_vars.add(name) if hasattr(ctx.state, 'readonly_vars') else None
            if value_str is not None:
                ctx.state.env[name] = value_str
            continue

        # Handle export attribute
        if options["export"]:
            if isinstance(ctx.state.env, VariableStore):
                ctx.state.env.set_attribute(name, "x")
            if value_str is not None:
                ctx.state.env[name] = value_str
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
            # Set attributes via metadata
            from ..types import VariableStore
            if isinstance(ctx.state.env, VariableStore):
                if options["integer"]:
                    ctx.state.env.set_attribute(name, "i")
                if options["lowercase"]:
                    ctx.state.env.set_attribute(name, "l")
                if options["uppercase"]:
                    ctx.state.env.set_attribute(name, "u")

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
                # Declare without value - just set type info (legacy compat)
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


def _get_attr_flags(env, name: str, ctx: "InterpreterContext") -> str:
    """Get the declare attribute flags for a variable."""
    from ..types import VariableStore
    flags = ""
    if isinstance(env, VariableStore):
        attrs = env.get_attributes(name)
        for attr in "rxilunt":
            if attr in attrs:
                flags += attr
    elif name in ctx.state.readonly_vars:
        flags += "r"
    # Check array type
    is_array = env.get(f"{name}__is_array")
    if is_array == "assoc":
        flags += "A"
    elif is_array:
        flags += "a"
    return flags


def _format_array_decl(env, name: str, flags: str) -> str:
    """Format an array variable declaration."""
    is_assoc = env.get(f"{name}__is_array") == "assoc"
    prefix = f"{name}_"
    elements = []
    for key in sorted(env.keys()):
        if key.startswith(prefix) and not key.startswith(f"{name}__"):
            idx_part = key[len(prefix):]
            val = env[key]
            elements.append((idx_part, val))

    if not is_assoc:
        # Sort indexed arrays by numeric index
        try:
            elements.sort(key=lambda x: int(x[0]))
        except ValueError:
            pass

    flag_str = f"-{flags}" if flags else "-a"
    pairs = " ".join(f'[{idx}]="{val}"' for idx, val in elements)
    if elements:
        return f"declare {flag_str} {name}=({pairs})"
    else:
        return f"declare {flag_str} {name}=()"


def _format_var_decl(env, name: str, ctx: "InterpreterContext") -> str | None:
    """Format a single variable declaration. Returns None if not found."""
    from ..types import VariableStore
    flags = _get_attr_flags(env, name, ctx)

    # Check for nameref
    if isinstance(env, VariableStore) and env.is_nameref(name):
        meta = env._metadata.get(name)
        target = meta.nameref_target if meta else ""
        flag_str = f"-{flags}" if flags else "-n"
        return f'declare {flag_str} {name}="{target}"'

    # Check for array
    is_array = env.get(f"{name}__is_array")
    if is_array:
        return _format_array_decl(env, name, flags)

    # Regular variable
    if name in env:
        val = env[name]
        flag_str = f"-{flags}" if flags else "--"
        return f'declare {flag_str} {name}="{val}"'

    return None


def _print_declarations(ctx: "InterpreterContext", names: list[str], options: dict) -> "ExecResult":
    """Print variable declarations."""
    lines = []
    env = ctx.state.env
    exit_code = 0

    if not names:
        # Print all variables
        # Collect unique variable names (skip internal keys)
        seen = set()
        for key in sorted(env.keys()):
            if "__" in key:
                # Extract base name from array keys like arr_0, arr__is_array
                continue
            if key.startswith("_"):
                continue
            if key in ("?", "#", "$", "!", "-", "*", "@"):
                continue
            # Skip positional params and single-digit keys
            if key.isdigit():
                continue

            seen.add(key)

        # Also add arrays
        for key in env.keys():
            if key.endswith("__is_array"):
                arr_name = key[:-len("__is_array")]
                if not arr_name.startswith("_"):
                    seen.add(arr_name)

        for name in sorted(seen):
            decl = _format_var_decl(env, name, ctx)
            if decl:
                lines.append(decl)
    else:
        for name in names:
            decl = _format_var_decl(env, name, ctx)
            if decl:
                lines.append(decl)
            else:
                # Variable not found
                lines_err = f"bash: declare: {name}: not found\n"
                exit_code = 1

    stdout = "\n".join(lines) + "\n" if lines else ""
    stderr = ""
    if exit_code != 0 and not lines:
        stderr = f"bash: declare: {names[0]}: not found\n" if names else ""
    return _result(stdout, stderr, exit_code)


def _handle_functions(ctx: "InterpreterContext", names: list[str], options: dict) -> "ExecResult":
    """Handle declare -f (list function bodies) and -F (list function names)."""
    functions = ctx.state.functions
    lines = []
    exit_code = 0

    if options["func_names"]:
        # -F: list function names only
        if names:
            for name in names:
                if name in functions:
                    lines.append(f"declare -f {name}")
                else:
                    exit_code = 1
        else:
            for name in sorted(functions.keys()):
                lines.append(f"declare -f {name}")
    else:
        # -f: list function definitions
        if names:
            for name in names:
                if name in functions:
                    lines.append(_format_function_def(name, functions[name]))
                else:
                    exit_code = 1
        else:
            for name in sorted(functions.keys()):
                lines.append(_format_function_def(name, functions[name]))

    # If also -p, treat as print mode for functions
    if options["print"] and not options["func_names"]:
        # declare -fp: same as declare -f
        pass

    stdout = "\n".join(lines) + "\n" if lines else ""
    return _result(stdout, "", exit_code)


def _format_function_def(name: str, func_node) -> str:
    """Format a function definition for output."""
    # Try to reconstruct the function body from the AST
    # For simplicity, output a placeholder that matches bash format
    body = _ast_to_source(func_node.body) if func_node.body else "    :"
    return f"{name} () \n{{\n{body}\n}}"


def _ast_to_source(node) -> str:
    """Best-effort AST to source code conversion."""
    # This is a simplified reconstruction - bash's declare -f does perfect roundtrip
    # but we can't easily reconstruct from AST without storing the original source
    from ...ast.types import GroupNode, SimpleCommandNode, StatementNode
    parts = []

    body_stmts = []
    if hasattr(node, 'body'):
        body_stmts = node.body
    elif hasattr(node, 'statements'):
        body_stmts = node.statements

    if not body_stmts:
        return "    :"

    for stmt in body_stmts:
        line = _stmt_to_source(stmt)
        if line:
            parts.append(f"    {line}")

    return "\n".join(parts) if parts else "    :"


def _stmt_to_source(node) -> str:
    """Convert a statement node to source."""
    from ...ast.types import SimpleCommandNode
    if hasattr(node, 'pipelines'):
        cmd_parts = []
        for i, pipeline in enumerate(node.pipelines):
            if i > 0 and i - 1 < len(node.operators):
                cmd_parts.append(node.operators[i - 1])
            pipeline_str = _pipeline_to_source(pipeline)
            cmd_parts.append(pipeline_str)
        return " ".join(cmd_parts)
    return ""


def _pipeline_to_source(node) -> str:
    """Convert a pipeline node to source."""
    parts = []
    for i, cmd in enumerate(node.commands):
        if i > 0:
            parts.append("|")
        parts.append(_cmd_to_source(cmd))
    result = " ".join(parts)
    if node.negated:
        result = f"! {result}"
    return result


def _cmd_to_source(node) -> str:
    """Convert a command node to source."""
    from ...ast.types import SimpleCommandNode
    if isinstance(node, SimpleCommandNode) or (hasattr(node, 'type') and node.type == "SimpleCommand"):
        parts = []
        if node.name:
            parts.append(_word_to_source(node.name))
        for arg in node.args:
            parts.append(_word_to_source(arg))
        return " ".join(parts)
    return ""


def _word_to_source(word) -> str:
    """Convert a word node to approximate source."""
    parts = []
    for part in word.parts:
        if hasattr(part, 'value'):
            parts.append(part.value)
        elif hasattr(part, 'parts'):
            inner = ""
            for p in part.parts:
                if hasattr(p, 'value'):
                    inner += p.value
                elif hasattr(p, 'parameter'):
                    inner += f"${p.parameter}"
            if part.type == "DoubleQuoted":
                parts.append(f'"{inner}"')
            elif part.type == "SingleQuoted":
                parts.append(f"'{inner}'")
            else:
                parts.append(inner)
        elif hasattr(part, 'parameter'):
            parts.append(f"${part.parameter}")
    return "".join(parts)


def _list_variables(ctx: "InterpreterContext", options: dict) -> "ExecResult":
    """List variables with matching attributes."""
    env = ctx.state.env
    lines = []

    # Collect unique variable names
    seen = set()
    for key in sorted(env.keys()):
        if "__" in key:
            continue
        if key.startswith("_"):
            continue
        if key in ("?", "#", "$", "!", "-", "*", "@"):
            continue
        if key.isdigit():
            continue
        seen.add(key)

    # Also add arrays
    for key in env.keys():
        if key.endswith("__is_array"):
            arr_name = key[:-len("__is_array")]
            if not arr_name.startswith("_"):
                seen.add(arr_name)

    for name in sorted(seen):
        decl = _format_var_decl(env, name, ctx)
        if decl:
            lines.append(decl)

    return _result("\n".join(lines) + "\n" if lines else "", "", 0)
