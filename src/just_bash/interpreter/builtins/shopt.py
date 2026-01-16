"""Shopt builtin implementation.

Usage: shopt [-pqsu] [optname ...]

Shell options control various behaviors of the shell.

Options:
  -s    Enable (set) each optname
  -u    Disable (unset) each optname
  -q    Quiet mode, suppress output (exit status indicates if option is set)
  -p    Print options in a form that can be reused as input
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


# Default states for shell options
DEFAULT_SHOPTS = {
    # Bash common options
    "expand_aliases": True,
    "extglob": False,
    "extquote": True,
    "failglob": False,
    "globstar": False,
    "nocasematch": False,
    "nullglob": False,
    "dotglob": False,
    "lastpipe": False,
    "xpg_echo": False,
    "progcomp": True,
    "histappend": False,
    "extdebug": False,
    "inherit_errexit": False,
    "command_sub_errexit": False,
    "process_sub_fail": False,
    # Strict options (for oil/ysh compatibility)
    "strict_array": False,
    "strict_arith": False,
    "strict_argv": False,
    "strict_arg_parse": False,
    "strict_control_flow": False,
    "strict_nameref": False,
    "strict_word_eval": False,
    "strict_tilde": False,
    "strict_status": False,
    "strict_binding": False,
    "strict": False,
    # Other options
    "eval_unsafe_arith": False,
    "ysh": False,
    "compat_array": False,
    "nounset": False,
    "parse_at": False,
    "simple_eval_builtin": False,
    "no_last_fork": False,
    "no_fork_last": False,
    "no_dash_glob": False,
    "globskipdots": True,
    "ignore_shopt_not_impl": False,
    "ignore_flags_not_impl": False,
}


def _result(stdout: str, stderr: str, exit_code: int) -> "ExecResult":
    """Create an ExecResult."""
    from ...types import ExecResult
    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


def _get_shopts(ctx: "InterpreterContext") -> dict[str, bool]:
    """Get the shell options dictionary from context."""
    # Store shopts in env with __shopt__ prefix
    shopts = {}
    for name, default in DEFAULT_SHOPTS.items():
        key = f"__shopt_{name}__"
        if key in ctx.state.env:
            shopts[name] = ctx.state.env[key] == "1"
        else:
            shopts[name] = default
    return shopts


def _set_shopt(ctx: "InterpreterContext", name: str, value: bool) -> None:
    """Set a shell option."""
    ctx.state.env[f"__shopt_{name}__"] = "1" if value else "0"


async def handle_shopt(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the shopt builtin."""
    # Parse options
    set_mode = False
    unset_mode = False
    quiet_mode = False
    print_mode = False
    optnames = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-s":
            set_mode = True
        elif arg == "-u":
            unset_mode = True
        elif arg == "-q":
            quiet_mode = True
        elif arg == "-p":
            print_mode = True
        elif arg == "--":
            optnames.extend(args[i + 1:])
            break
        elif arg.startswith("-"):
            # Handle combined flags like -su
            for c in arg[1:]:
                if c == "s":
                    set_mode = True
                elif c == "u":
                    unset_mode = True
                elif c == "q":
                    quiet_mode = True
                elif c == "p":
                    print_mode = True
                else:
                    return _result("", f"bash: shopt: -{c}: invalid option\n", 1)
        else:
            optnames.append(arg)
        i += 1

    shopts = _get_shopts(ctx)

    # If both -s and -u specified, error
    if set_mode and unset_mode:
        return _result("", "bash: shopt: cannot set and unset options simultaneously\n", 1)

    # No optnames and no -s/-u: show all options or those matching filter
    if not optnames and not set_mode and not unset_mode:
        output = []
        for name in sorted(DEFAULT_SHOPTS.keys()):
            state = shopts.get(name, DEFAULT_SHOPTS.get(name, False))
            state_str = "on" if state else "off"
            if print_mode:
                prefix = "-s" if state else "-u"
                output.append(f"shopt {prefix} {name}")
            else:
                output.append(f"{name}\t{state_str}")
        if not quiet_mode:
            return _result("\n".join(output) + "\n" if output else "", "", 0)
        return _result("", "", 0)

    # With -s/-u but no optnames: show options that match the state
    if not optnames and (set_mode or unset_mode) and not quiet_mode:
        target_state = set_mode
        output = []
        for name in sorted(DEFAULT_SHOPTS.keys()):
            state = shopts.get(name, DEFAULT_SHOPTS.get(name, False))
            if state == target_state:
                state_str = "on" if state else "off"
                if print_mode:
                    prefix = "-s" if state else "-u"
                    output.append(f"shopt {prefix} {name}")
                else:
                    output.append(f"{name}\t{state_str}")
        return _result("\n".join(output) + "\n" if output else "", "", 0)

    # Process optnames
    exit_code = 0
    output = []

    for name in optnames:
        # Check if option exists
        if name not in DEFAULT_SHOPTS:
            # Unknown option - but if ignore_shopt_not_impl is set, silently ignore
            if shopts.get("ignore_shopt_not_impl", False):
                continue
            return _result("", f"bash: shopt: {name}: invalid shell option name\n", 1)

        if set_mode:
            _set_shopt(ctx, name, True)
        elif unset_mode:
            _set_shopt(ctx, name, False)
        else:
            # Query mode
            state = shopts.get(name, DEFAULT_SHOPTS.get(name, False))
            if not state:
                exit_code = 1
            if not quiet_mode:
                state_str = "on" if state else "off"
                if print_mode:
                    prefix = "-s" if state else "-u"
                    output.append(f"shopt {prefix} {name}")
                else:
                    output.append(f"{name}\t{state_str}")

    if output and not quiet_mode:
        return _result("\n".join(output) + "\n", "", exit_code)
    return _result("", "", exit_code)
