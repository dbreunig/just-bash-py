"""Miscellaneous builtins: colon, true, false, type, command, builtin, exec, wait.

These are simple builtins that don't need their own files.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


def _result(stdout: str, stderr: str, exit_code: int) -> "ExecResult":
    """Create an ExecResult."""
    from ...types import ExecResult
    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


async def handle_colon(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the : (colon) builtin - null command, always succeeds."""
    return _result("", "", 0)


async def handle_true(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the true builtin - always succeeds."""
    return _result("", "", 0)


async def handle_false(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the false builtin - always fails."""
    return _result("", "", 1)


async def handle_type(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the type builtin - display information about command type.

    Usage: type [-afptP] name [name ...]

    Options:
      -a    Display all locations containing an executable named name
      -f    Suppress shell function lookup
      -p    Display path to executable (like which)
      -P    Force path search even for builtins
      -t    Output a single word: alias, keyword, function, builtin, file, or ''
    """
    from .alias import get_aliases

    # Parse options
    show_all = False
    no_functions = False
    path_only = False
    force_path = False
    type_only = False
    names = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            names.extend(args[i + 1:])
            break
        elif arg.startswith("-") and len(arg) > 1:
            for c in arg[1:]:
                if c == "a":
                    show_all = True
                elif c == "f":
                    no_functions = True
                elif c == "p":
                    path_only = True
                elif c == "P":
                    force_path = True
                elif c == "t":
                    type_only = True
                else:
                    return _result("", f"bash: type: -{c}: invalid option\n", 1)
        else:
            names.append(arg)
        i += 1

    if not names:
        return _result("", "bash: type: usage: type [-afptP] name [name ...]\n", 1)

    # Keywords
    keywords = {
        "if", "then", "else", "elif", "fi", "case", "esac", "for", "select",
        "while", "until", "do", "done", "in", "function", "time", "coproc",
        "{", "}", "!", "[[", "]]"
    }

    # Get builtins (includes commands that bash treats as builtins)
    from . import BUILTINS
    # Commands that are implemented externally but should be reported as builtins
    _builtin_command_names = {
        "echo", "printf", "read", "pwd", "test", "[", "kill", "enable",
        "help", "hash", "ulimit", "umask", "jobs", "fg", "bg", "disown",
        "suspend", "logout", "dirs", "pushd", "popd", "times", "trap",
        "caller", "complete", "compgen", "compopt",
    }

    # Get aliases
    aliases = get_aliases(ctx)

    # Get functions
    functions = getattr(ctx.state, 'functions', {})

    output = []
    exit_code = 0

    for name in names:
        found = False

        # Check alias (unless -f)
        if not no_functions and name in aliases:
            found = True
            if type_only:
                output.append("alias")
            elif path_only:
                pass  # -p doesn't show aliases
            else:
                output.append(f"{name} is aliased to `{aliases[name]}'")
            if not show_all:
                continue

        # Check keyword
        if name in keywords:
            found = True
            if type_only:
                output.append("keyword")
            elif not path_only:
                output.append(f"{name} is a shell keyword")
            if not show_all:
                continue

        # Check function (unless -f or -P)
        if not no_functions and not force_path and name in functions:
            found = True
            if type_only:
                output.append("function")
            elif not path_only:
                output.append(f"{name} is a function")
            if not show_all:
                continue

        # Check builtin (unless -P)
        if not force_path and (name in BUILTINS or name in _builtin_command_names):
            found = True
            if type_only:
                output.append("builtin")
            elif not path_only:
                output.append(f"{name} is a shell builtin")
            if not show_all:
                continue

        # Check command registry
        from ...commands import COMMAND_NAMES
        if name in COMMAND_NAMES and name not in _builtin_command_names:
            found = True
            if type_only:
                output.append("file")
            elif path_only:
                output.append(name)
            else:
                output.append(f"{name} is {name}")
            if not show_all:
                continue

        if not found:
            if type_only:
                pass  # bash outputs nothing for type -t on not-found commands
            else:
                output.append(f"bash: type: {name}: not found")
            exit_code = 1

    if output:
        return _result("\n".join(output) + "\n", "", exit_code)
    return _result("", "", exit_code)


async def handle_command(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the command builtin - run command bypassing functions.

    Usage: command [-pVv] command [arguments ...]

    Options:
      -p    Use a default path to search for command
      -v    Display description of command (like type)
      -V    Display verbose description of command
    """
    # Parse options
    describe = False
    verbose = False
    use_default_path = False
    cmd_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            cmd_args = args[i + 1:]
            break
        elif arg.startswith("-") and len(arg) > 1 and not cmd_args:
            for c in arg[1:]:
                if c == "p":
                    use_default_path = True
                elif c == "v":
                    describe = True
                elif c == "V":
                    verbose = True
                else:
                    return _result("", f"bash: command: -{c}: invalid option\n", 1)
        else:
            cmd_args = args[i:]
            break
        i += 1

    if not cmd_args:
        if describe or verbose:
            return _result("", "", 0)
        return _result("", "", 0)

    cmd_name = cmd_args[0]

    # Handle -v or -V: describe the command
    if describe or verbose:
        from . import BUILTINS
        from ...commands import COMMAND_NAMES

        functions = getattr(ctx.state, 'functions', {})

        if cmd_name in functions:
            if verbose:
                return _result(f"{cmd_name} is a function\n", "", 0)
            else:
                return _result(f"{cmd_name}\n", "", 0)
        elif cmd_name in BUILTINS:
            if verbose:
                return _result(f"{cmd_name} is a shell builtin\n", "", 0)
            else:
                return _result(f"{cmd_name}\n", "", 0)
        elif cmd_name in COMMAND_NAMES:
            if verbose:
                return _result(f"{cmd_name} is {cmd_name}\n", "", 0)
            else:
                return _result(f"{cmd_name}\n", "", 0)
        else:
            return _result("", f"bash: command: {cmd_name}: not found\n", 1)

    # Execute the command, bypassing functions
    # Store current function state and temporarily hide the function
    functions = getattr(ctx.state, 'functions', {})
    hidden_func = functions.pop(cmd_name, None)

    try:
        # Build command string with proper quoting
        def shell_quote(s: str) -> str:
            if not s or any(c in s for c in ' \t\n\'"\\$`!'):
                return "'" + s.replace("'", "'\\''") + "'"
            return s

        cmd_str = " ".join(shell_quote(a) for a in cmd_args)
        result = await ctx.exec_fn(cmd_str, None, None)
        return result
    finally:
        # Restore function if it was hidden
        if hidden_func is not None:
            functions[cmd_name] = hidden_func


async def handle_builtin(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the builtin builtin - run shell builtin directly.

    Usage: builtin [shell-builtin [args]]
    """
    if not args:
        return _result("", "", 0)

    builtin_name = args[0]
    builtin_args = args[1:]

    from . import BUILTINS

    if builtin_name not in BUILTINS:
        return _result("", f"bash: builtin: {builtin_name}: not a shell builtin\n", 1)

    handler = BUILTINS[builtin_name]
    return await handler(ctx, builtin_args)


async def handle_exec(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the exec builtin - replace shell with command.

    Usage: exec [-cl] [-a name] [command [arguments ...]]

    In a sandboxed environment, this just executes the command normally
    since we can't actually replace the process.

    Options:
      -c    Execute command with empty environment
      -l    Pass dash as zeroth argument (login shell)
      -a name  Pass name as zeroth argument
    """
    # Parse options
    clear_env = False
    login_shell = False
    arg0_name = None
    cmd_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            cmd_args = args[i + 1:]
            break
        elif arg == "-c" and not cmd_args:
            clear_env = True
        elif arg == "-l" and not cmd_args:
            login_shell = True
        elif arg == "-a" and not cmd_args and i + 1 < len(args):
            i += 1
            arg0_name = args[i]
        elif arg.startswith("-") and not cmd_args:
            # Combined options
            for c in arg[1:]:
                if c == "c":
                    clear_env = True
                elif c == "l":
                    login_shell = True
                else:
                    return _result("", f"bash: exec: -{c}: invalid option\n", 1)
        else:
            cmd_args = args[i:]
            break
        i += 1

    # If no command, exec affects persistent FD redirections
    if not cmd_args:
        # Redirections are handled by the interpreter's redirect processing
        # which now supports the FD table. Return success.
        return _result("", "", 0)

    # In sandboxed mode, just execute the command
    def shell_quote(s: str) -> str:
        if not s or any(c in s for c in ' \t\n\'"\\$`!'):
            return "'" + s.replace("'", "'\\''") + "'"
        return s

    cmd_str = " ".join(shell_quote(a) for a in cmd_args)
    result = await ctx.exec_fn(cmd_str, None, None)
    return result


async def handle_wait(
    ctx: "InterpreterContext", args: list[str]
) -> "ExecResult":
    """Execute the wait builtin - wait for background jobs.

    Usage: wait [-fn] [-p var] [id ...]

    In a sandboxed environment without true background jobs,
    this is mostly a no-op but returns success.

    Options:
      -f    Wait for job termination (not just state change)
      -n    Wait for any job to complete
      -p var  Store PID in var
    """
    # Parse options
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        elif arg.startswith("-"):
            # Accept but ignore options since we don't have real job control
            if arg == "-p" and i + 1 < len(args):
                i += 1
        i += 1

    # No real job control in sandboxed environment, return success
    return _result("", "", 0)
