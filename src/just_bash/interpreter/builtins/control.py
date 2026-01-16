"""Control flow builtins: break, continue, return, exit.

These builtins control the flow of script execution.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult

from ..errors import BreakError, ContinueError, ReturnError, ExitError


async def handle_break(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the break builtin.

    Usage: break [n]

    Exit from within a for, while, until, or select loop.
    If n is specified, break out of n enclosing loops.
    """
    levels = 1
    if args:
        try:
            levels = int(args[0])
            if levels < 1:
                levels = 1
        except ValueError:
            from ...types import ExecResult
            return ExecResult(
                stdout="",
                stderr=f"bash: break: {args[0]}: numeric argument required\n",
                exit_code=1,
            )

    # Check if we're in a loop
    if ctx.state.loop_depth < 1:
        from ...types import ExecResult
        return ExecResult(
            stdout="",
            stderr="",  # bash doesn't print error for break outside loop
            exit_code=0,
        )

    raise BreakError(levels=levels)


async def handle_continue(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the continue builtin.

    Usage: continue [n]

    Resume the next iteration of an enclosing for, while, until, or select loop.
    If n is specified, resume at the nth enclosing loop.
    """
    levels = 1
    if args:
        try:
            levels = int(args[0])
            if levels < 1:
                levels = 1
        except ValueError:
            from ...types import ExecResult
            return ExecResult(
                stdout="",
                stderr=f"bash: continue: {args[0]}: numeric argument required\n",
                exit_code=1,
            )

    # Check if we're in a loop
    if ctx.state.loop_depth < 1:
        from ...types import ExecResult
        return ExecResult(
            stdout="",
            stderr="",  # bash doesn't print error for continue outside loop
            exit_code=0,
        )

    raise ContinueError(levels=levels)


async def handle_return(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the return builtin.

    Usage: return [n]

    Return from a shell function or sourced script.
    n is the return value (0-255). If n is omitted, the return value is
    the exit status of the last command executed.
    """
    exit_code = ctx.state.last_exit_code
    if args:
        try:
            exit_code = int(args[0]) & 255  # Mask to 0-255
        except ValueError:
            from ...types import ExecResult
            return ExecResult(
                stdout="",
                stderr=f"bash: return: {args[0]}: numeric argument required\n",
                exit_code=1,
            )

    raise ReturnError(exit_code)


async def handle_exit(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the exit builtin.

    Usage: exit [n]

    Exit the shell with status n. If n is omitted, the exit status is
    that of the last command executed.
    """
    exit_code = ctx.state.last_exit_code
    if args:
        try:
            exit_code = int(args[0]) & 255  # Mask to 0-255
        except ValueError:
            from ...types import ExecResult
            return ExecResult(
                stdout="",
                stderr=f"bash: exit: {args[0]}: numeric argument required\n",
                exit_code=1,
            )

    raise ExitError(exit_code)
