"""Readonly builtin implementation.

Usage: readonly [-p] [name[=value] ...]

Marks variables as readonly. Once a variable is marked readonly, it cannot
be reassigned or unset.

Options:
  -p    Display all readonly variables
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


def _result(stdout: str, stderr: str, exit_code: int) -> "ExecResult":
    """Create an ExecResult."""
    from ...types import ExecResult
    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


async def handle_readonly(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the readonly builtin."""
    # Parse options
    show_all = False
    names = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-p":
            show_all = True
        elif arg == "--":
            names.extend(args[i + 1:])
            break
        elif arg.startswith("-"):
            # Unknown option - ignore for now
            pass
        else:
            names.append(arg)
        i += 1

    # If no names and -p or no args, show all readonly variables
    if not names or show_all:
        output = []
        readonly_vars = ctx.state.env.get("__readonly__", "").split()
        for var in sorted(readonly_vars):
            if var in ctx.state.env:
                value = ctx.state.env[var]
                output.append(f"declare -r {var}=\"{value}\"")
            else:
                output.append(f"declare -r {var}")
        if output:
            return _result("\n".join(output) + "\n", "", 0)
        return _result("", "", 0)

    # Mark variables as readonly
    readonly_set = set(ctx.state.env.get("__readonly__", "").split())

    for name_value in names:
        if "=" in name_value:
            name, value = name_value.split("=", 1)
            # Check if already readonly
            if name in readonly_set:
                return _result("", f"bash: readonly: {name}: readonly variable\n", 1)
            ctx.state.env[name] = value
        else:
            name = name_value

        readonly_set.add(name)

    # Store readonly set
    ctx.state.env["__readonly__"] = " ".join(sorted(readonly_set))

    return _result("", "", 0)
