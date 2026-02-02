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
    from ..types import VariableStore

    mode = "variable"
    unset_nameref = False
    names = []

    for arg in args:
        if arg == "-v":
            mode = "variable"
        elif arg == "-f":
            mode = "function"
        elif arg == "-n":
            # -n: unset the nameref itself, not the target
            unset_nameref = True
        elif arg.startswith("-"):
            # Skip unknown options
            pass
        else:
            names.append(arg)

    import re
    env = ctx.state.env

    for name in names:
        if mode == "function":
            ctx.state.functions.pop(name, None)
        else:
            # Handle -n flag: unset the nameref variable itself
            if unset_nameref and isinstance(env, VariableStore):
                env.clear_nameref(name)
                env.pop(name, None)
                continue

            # Resolve nameref for unset target
            resolved_name = name
            if isinstance(env, VariableStore) and env.is_nameref(name):
                try:
                    resolved_name = env.resolve_nameref(name)
                except ValueError:
                    resolved_name = name

            # Check for array element syntax: a[idx]
            array_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', resolved_name)
            if array_match:
                arr_name = array_match.group(1)
                subscript = array_match.group(2)
                # Check if variable is readonly
                if _is_readonly(ctx, arr_name):
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: unset: {arr_name}: cannot unset: readonly variable\n",
                        exit_code=1,
                    )
                # Remove specific array element
                env.pop(f"{arr_name}_{subscript}", None)
            else:
                # Check if variable is readonly
                if _is_readonly(ctx, resolved_name):
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: unset: {resolved_name}: cannot unset: readonly variable\n",
                        exit_code=1,
                    )
                # Remove the variable
                env.pop(resolved_name, None)
                # Also remove all array elements if this is an array
                prefix = f"{resolved_name}_"
                to_remove = [k for k in env if k.startswith(prefix)]
                for k in to_remove:
                    del env[k]
                # Clean up metadata
                if isinstance(env, VariableStore):
                    env._metadata.pop(resolved_name, None)

    return ExecResult(stdout="", stderr="", exit_code=0)


def _is_readonly(ctx: "InterpreterContext", name: str) -> bool:
    """Check if a variable is readonly."""
    from ..types import VariableStore
    env = ctx.state.env
    if isinstance(env, VariableStore) and env.is_readonly(name):
        return True
    return name in ctx.state.readonly_vars
