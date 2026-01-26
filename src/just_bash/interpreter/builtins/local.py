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


def _save_array_in_scope(ctx: "InterpreterContext", name: str, scope: dict) -> None:
    """Save all array-related keys for a variable in the local scope."""
    env = ctx.state.env
    # Save the array marker
    array_key = f"{name}__is_array"
    if array_key not in scope:
        scope[array_key] = env.get(array_key)

    # Save all existing array element keys
    prefix = f"{name}_"
    for key in list(env.keys()):
        if key.startswith(prefix) and not key.startswith(f"{name}__"):
            if key not in scope:
                scope[key] = env.get(key)


def _clear_array_elements(ctx: "InterpreterContext", name: str) -> None:
    """Remove all array element keys for a variable."""
    prefix = f"{name}_"
    to_remove = [k for k in ctx.state.env if k.startswith(prefix) and not k.startswith(f"{name}__")]
    for k in to_remove:
        del ctx.state.env[k]


async def handle_local(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the local builtin."""
    from ...types import ExecResult
    from .declare import _parse_array_assignment

    # Check if we're inside a function
    if not ctx.state.local_scopes:
        return ExecResult(
            stdout="",
            stderr="bash: local: can only be used in a function\n",
            exit_code=1,
        )

    current_scope = ctx.state.local_scopes[-1]

    # Parse flags
    is_array = False
    is_assoc = False
    remaining_args = []

    for arg in args:
        if arg.startswith("-") and not ("=" in arg):
            # Parse flag characters
            for ch in arg[1:]:
                if ch == "a":
                    is_array = True
                elif ch == "A":
                    is_assoc = True
                # Other flags like -i, -r, -x are ignored for now
        else:
            remaining_args.append(arg)

    for arg in remaining_args:
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

        # Handle array initialization
        if (is_array or is_assoc) and value.startswith("(") and value.endswith(")"):
            # Save existing array keys before overwriting
            _save_array_in_scope(ctx, name, current_scope)

            # Set array type marker
            array_key = f"{name}__is_array"
            ctx.state.env[array_key] = "assoc" if is_assoc else "indexed"

            # Clear existing elements and parse new ones
            _clear_array_elements(ctx, name)
            inner = value[1:-1].strip()
            if inner:
                _parse_array_assignment(ctx, name, inner, is_assoc)
        elif is_array or is_assoc:
            # Declare as array without initialization
            _save_array_in_scope(ctx, name, current_scope)
            array_key = f"{name}__is_array"
            ctx.state.env[array_key] = "assoc" if is_assoc else "indexed"
            if "=" in arg:
                # Simple value assignment - set element 0
                ctx.state.env[f"{name}_0"] = value
        else:
            # Simple variable
            ctx.state.env[name] = value

    return ExecResult(stdout="", stderr="", exit_code=0)
