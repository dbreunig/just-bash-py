"""Pwd command implementation.

Usage: pwd [-LP]

Print the name of the current working directory.

Options:
  -L    Print the value of $PWD if it names the current working directory
  -P    Print the physical directory, without any symbolic links
"""

from ...types import CommandContext, ExecResult


class PwdCommand:
    """The pwd command."""

    name = "pwd"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the pwd command."""
        # For now, just return cwd (ignore -L/-P options in virtual fs)
        return ExecResult(stdout=f"{ctx.cwd}\n", stderr="", exit_code=0)
