"""Unset builtin implementation.

Usage: unset [-f] [-v] [name ...]

Remove variables or functions.

Options:
  -v  Treat each name as a variable name (default)
  -f  Treat each name as a function name
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


async def handle_unset(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the unset builtin."""
    from ...types import ExecResult

    mode = "variable"
    names = []

    for arg in args:
        if arg == "-v":
            mode = "variable"
        elif arg == "-f":
            mode = "function"
        elif arg == "-n":
            # -n treats name as a nameref - we don't support this but ignore
            pass
        elif arg.startswith("-"):
            # Skip unknown options
            pass
        else:
            names.append(arg)

    import re

    for name in names:
        if mode == "function":
            ctx.state.functions.pop(name, None)
        else:
            # Check for array element syntax: a[idx]
            array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', name)
            if array_match:
                arr_name = array_match.group(1)
                subscript = array_match.group(2)
                # Check if variable is readonly
                if arr_name in ctx.state.readonly_vars:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: unset: {arr_name}: cannot unset: readonly variable\n",
                        exit_code=1,
                    )
                # Remove specific array element
                ctx.state.env.pop(f"{arr_name}_{subscript}", None)
            else:
                # Check if variable is readonly
                if name in ctx.state.readonly_vars:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: unset: {name}: cannot unset: readonly variable\n",
                        exit_code=1,
                    )
                # Remove the variable
                ctx.state.env.pop(name, None)
                # Also remove all array elements if this is an array
                prefix = f"{name}_"
                to_remove = [k for k in ctx.state.env if k.startswith(prefix)]
                for k in to_remove:
                    del ctx.state.env[k]

    return ExecResult(stdout="", stderr="", exit_code=0)
