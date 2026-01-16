"""Cd builtin implementation.

Usage: cd [dir]
       cd -

Change the current working directory to dir. If dir is not specified,
change to $HOME. If dir is -, change to $OLDPWD.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


async def handle_cd(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the cd builtin."""
    from ...types import ExecResult

    # Determine target directory
    if not args:
        # cd with no args goes to HOME
        target = ctx.state.env.get("HOME", "/")
    elif args[0] == "-":
        # cd - goes to previous directory
        target = ctx.state.previous_dir
        if not target:
            return ExecResult(
                stdout="",
                stderr="bash: cd: OLDPWD not set\n",
                exit_code=1,
            )
    else:
        target = args[0]

    # Resolve the path
    new_dir = ctx.fs.resolve_path(ctx.state.cwd, target)

    # Verify directory exists
    try:
        exists = await ctx.fs.exists(new_dir)
        if not exists:
            return ExecResult(
                stdout="",
                stderr=f"bash: cd: {target}: No such file or directory\n",
                exit_code=1,
            )

        is_dir = await ctx.fs.is_directory(new_dir)
        if not is_dir:
            return ExecResult(
                stdout="",
                stderr=f"bash: cd: {target}: Not a directory\n",
                exit_code=1,
            )
    except Exception as e:
        return ExecResult(
            stdout="",
            stderr=f"bash: cd: {target}: {e}\n",
            exit_code=1,
        )

    # Update state
    old_dir = ctx.state.cwd
    ctx.state.previous_dir = old_dir
    ctx.state.cwd = new_dir
    ctx.state.env["OLDPWD"] = old_dir
    ctx.state.env["PWD"] = new_dir

    # If cd - was used, print the new directory
    stdout = ""
    if args and args[0] == "-":
        stdout = new_dir + "\n"

    return ExecResult(stdout=stdout, stderr="", exit_code=0)
