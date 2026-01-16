"""Set and shift builtin implementations.

set - Set or unset shell options and positional parameters.

Usage: set [options] [-- arg ...]
       set +o
       set -o [option]

Options:
  -e  errexit    Exit immediately if a command exits with non-zero status
  -u  nounset    Treat unset variables as an error when substituting
  -x  xtrace     Print commands and their arguments as they are executed
  -v  verbose    Print shell input lines as they are read
  -o pipefail    Return exit status of last failing command in pipeline

shift - Shift positional parameters.

Usage: shift [n]

Shift positional parameters to the left by n (default 1).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


async def handle_set(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the set builtin."""
    from ...types import ExecResult

    # No arguments: print all variables
    if not args:
        lines = []
        for k, v in sorted(ctx.state.env.items()):
            # Skip internal variables
            if k.startswith("PIPESTATUS_") or k == "?":
                continue
            lines.append(f"{k}='{v}'")
        return ExecResult(stdout="\n".join(lines) + "\n", stderr="", exit_code=0)

    i = 0
    while i < len(args):
        arg = args[i]

        # Handle -- which starts positional parameters
        if arg == "--":
            # Set positional parameters from remaining args
            new_params = args[i + 1:]
            _set_positional_params(ctx, new_params)
            return ExecResult(stdout="", stderr="", exit_code=0)

        # Handle -o option
        if arg == "-o":
            if i + 1 < len(args):
                i += 1
                opt_name = args[i]
                result = _set_option(ctx, opt_name, True)
                if result:
                    return result
            else:
                # List all options
                stdout = _list_options(ctx)
                return ExecResult(stdout=stdout, stderr="", exit_code=0)

        # Handle +o option
        elif arg == "+o":
            if i + 1 < len(args):
                i += 1
                opt_name = args[i]
                result = _set_option(ctx, opt_name, False)
                if result:
                    return result
            else:
                # List all options in a format that can be re-input
                stdout = _list_options_script(ctx)
                return ExecResult(stdout=stdout, stderr="", exit_code=0)

        # Handle short options like -e, -u, -x, -v
        elif arg.startswith("-") and len(arg) > 1 and arg[1] != "-":
            for c in arg[1:]:
                result = _set_short_option(ctx, c, True)
                if result:
                    return result

        elif arg.startswith("+") and len(arg) > 1:
            for c in arg[1:]:
                result = _set_short_option(ctx, c, False)
                if result:
                    return result

        # Treat as positional parameter
        else:
            new_params = args[i:]
            _set_positional_params(ctx, new_params)
            return ExecResult(stdout="", stderr="", exit_code=0)

        i += 1

    return ExecResult(stdout="", stderr="", exit_code=0)


def _set_positional_params(ctx: "InterpreterContext", params: list[str]) -> None:
    """Set positional parameters $1, $2, etc."""
    # Clear existing positional parameters
    i = 1
    while str(i) in ctx.state.env:
        del ctx.state.env[str(i)]
        i += 1

    # Set new positional parameters
    for i, param in enumerate(params, start=1):
        ctx.state.env[str(i)] = param

    # Update $# (number of positional parameters)
    ctx.state.env["#"] = str(len(params))


def _set_option(ctx: "InterpreterContext", name: str, enable: bool) -> "ExecResult | None":
    """Set a named option. Returns error result if invalid option."""
    from ...types import ExecResult

    options = ctx.state.options
    if name == "errexit":
        options.errexit = enable
    elif name == "nounset":
        options.nounset = enable
    elif name == "xtrace":
        options.xtrace = enable
    elif name == "verbose":
        options.verbose = enable
    elif name == "pipefail":
        options.pipefail = enable
    else:
        return ExecResult(
            stdout="",
            stderr=f"bash: set: {name}: invalid option name\n",
            exit_code=1,
        )
    return None


def _set_short_option(ctx: "InterpreterContext", char: str, enable: bool) -> "ExecResult | None":
    """Set a short option like -e. Returns error result if invalid."""
    from ...types import ExecResult

    options = ctx.state.options
    if char == "e":
        options.errexit = enable
    elif char == "u":
        options.nounset = enable
    elif char == "x":
        options.xtrace = enable
    elif char == "v":
        options.verbose = enable
    else:
        return ExecResult(
            stdout="",
            stderr=f"bash: set: -{char}: invalid option\n",
            exit_code=1,
        )
    return None


def _list_options(ctx: "InterpreterContext") -> str:
    """List all options in human-readable format."""
    options = ctx.state.options
    lines = [
        f"errexit         {'on' if options.errexit else 'off'}",
        f"nounset         {'on' if options.nounset else 'off'}",
        f"pipefail        {'on' if options.pipefail else 'off'}",
        f"verbose         {'on' if options.verbose else 'off'}",
        f"xtrace          {'on' if options.xtrace else 'off'}",
    ]
    return "\n".join(lines) + "\n"


def _list_options_script(ctx: "InterpreterContext") -> str:
    """List options in re-inputable script format."""
    options = ctx.state.options
    lines = [
        f"set {'-' if options.errexit else '+'}o errexit",
        f"set {'-' if options.nounset else '+'}o nounset",
        f"set {'-' if options.pipefail else '+'}o pipefail",
        f"set {'-' if options.verbose else '+'}o verbose",
        f"set {'-' if options.xtrace else '+'}o xtrace",
    ]
    return "\n".join(lines) + "\n"


async def handle_shift(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the shift builtin."""
    from ...types import ExecResult

    # Default shift count is 1
    n = 1
    if args:
        try:
            n = int(args[0])
        except ValueError:
            return ExecResult(
                stdout="",
                stderr=f"bash: shift: {args[0]}: numeric argument required\n",
                exit_code=1,
            )

    if n < 0:
        return ExecResult(
            stdout="",
            stderr=f"bash: shift: {n}: shift count out of range\n",
            exit_code=1,
        )

    # Get current positional parameters
    param_count = int(ctx.state.env.get("#", "0"))

    if n > param_count:
        return ExecResult(
            stdout="",
            stderr=f"bash: shift: {n}: shift count out of range\n",
            exit_code=1,
        )

    # Collect remaining parameters
    new_params = []
    for i in range(n + 1, param_count + 1):
        new_params.append(ctx.state.env.get(str(i), ""))

    # Set new positional parameters
    _set_positional_params(ctx, new_params)

    return ExecResult(stdout="", stderr="", exit_code=0)
