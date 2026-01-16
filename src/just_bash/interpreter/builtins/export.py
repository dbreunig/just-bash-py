"""Export builtin implementation.

Usage: export [name[=value] ...]

Mark variables for export to child processes. If no arguments are given,
list all exported variables.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


async def handle_export(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the export builtin."""
    from ...types import ExecResult

    # No arguments: list all exported variables
    if not args:
        lines = []
        for k, v in sorted(ctx.state.env.items()):
            # Skip internal variables
            if k.startswith("PIPESTATUS_") or k == "?" or k == "#":
                continue
            # Escape special characters in value
            escaped_v = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'declare -x {k}="{escaped_v}"')
        return ExecResult(stdout="\n".join(lines) + "\n" if lines else "", stderr="", exit_code=0)

    # Process each argument
    for arg in args:
        # Skip options
        if arg.startswith("-"):
            continue

        if "=" in arg:
            name, value = arg.split("=", 1)
        else:
            # Export existing variable or create empty
            name = arg
            value = ctx.state.env.get(arg, "")

        # Validate identifier
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            return ExecResult(
                stdout="",
                stderr=f"bash: export: '{name}': not a valid identifier\n",
                exit_code=1,
            )

        ctx.state.env[name] = value

    return ExecResult(stdout="", stderr="", exit_code=0)
