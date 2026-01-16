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

    for name in names:
        if mode == "function":
            ctx.state.functions.pop(name, None)
        else:
            # Check if variable is readonly
            if name in ctx.state.readonly_vars:
                return ExecResult(
                    stdout="",
                    stderr=f"bash: unset: {name}: cannot unset: readonly variable\n",
                    exit_code=1,
                )
            ctx.state.env.pop(name, None)

    return ExecResult(stdout="", stderr="", exit_code=0)
