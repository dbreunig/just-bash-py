"""Which command implementation."""

from ..registry import COMMAND_NAMES
from ...types import CommandContext, ExecResult


class WhichCommand:
    """The which command - locate a command."""

    name = "which"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the which command."""
        silent = False
        show_all = False
        commands: list[str] = []

        for arg in args:
            if arg in ("-s", "--silent"):
                silent = True
            elif arg in ("-a", "--all"):
                show_all = True
            elif arg == "--help":
                return ExecResult(
                    stdout="Usage: which [OPTION]... COMMAND...\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg.startswith("-"):
                pass  # Ignore unknown options
            else:
                commands.append(arg)

        if not commands:
            return ExecResult(stdout="", stderr="", exit_code=1)

        output_lines = []
        exit_code = 0

        for cmd in commands:
            # Check if command exists in our registry
            if cmd in COMMAND_NAMES:
                if not silent:
                    output_lines.append(f"/usr/bin/{cmd}")
            else:
                exit_code = 1

        output = "\n".join(output_lines)
        if output:
            output += "\n"

        return ExecResult(stdout="" if silent else output, stderr="", exit_code=exit_code)
