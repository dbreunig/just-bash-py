"""Local builtin implementation.

Usage: local [name[=value] ...]

Create local variables for use within a function. When the function
returns, any local variables are restored to their previous values.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


async def handle_local(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the local builtin."""
    from ...types import ExecResult

    # Check if we're inside a function
    if not ctx.state.local_scopes:
        return ExecResult(
            stdout="",
            stderr="bash: local: can only be used in a function\n",
            exit_code=1,
        )

    current_scope = ctx.state.local_scopes[-1]

    for arg in args:
        # Skip options
        if arg.startswith("-"):
            continue

        if "=" in arg:
            name, value = arg.split("=", 1)
        else:
            name = arg
            value = ""

        # Validate identifier
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            return ExecResult(
                stdout="",
                stderr=f"bash: local: '{name}': not a valid identifier\n",
                exit_code=1,
            )

        # Save original value for restoration (if not already saved)
        if name not in current_scope:
            current_scope[name] = ctx.state.env.get(name)

        # Set the new value
        ctx.state.env[name] = value

    return ExecResult(stdout="", stderr="", exit_code=0)
