"""Argv command implementation.

Usage: argv.py [arg ...]

Print arguments as a Python-style list.
Used for testing word splitting and expansion.
"""

from ...types import CommandContext, ExecResult


class ArgvCommand:
    """The argv.py command for testing argument handling."""

    name = "argv.py"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the argv.py command."""
        # Format as Python list
        output = repr(args) + "\n"
        return ExecResult(stdout=output, stderr="", exit_code=0)
