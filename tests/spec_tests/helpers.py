"""Test helper commands for spec tests.

These replace the Python scripts used in the original Oils shell tests.
"""

from just_bash.types import CommandContext, ExecResult


class ArgvCommand:
    """argv.py - prints arguments in Python repr() format: ['arg1', "arg with '"]

    Python uses single quotes by default, double quotes when string contains single quotes.
    """

    name = "argv.py"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        formatted = []
        for arg in args:
            has_single_quote = "'" in arg
            has_double_quote = '"' in arg

            if has_single_quote and not has_double_quote:
                # Use double quotes when string contains single quotes but no double quotes
                escaped = arg.replace("\\", "\\\\")
                formatted.append(f'"{escaped}"')
            else:
                # Default: use single quotes (escape single quotes and backslashes)
                escaped = arg.replace("\\", "\\\\").replace("'", "\\'")
                formatted.append(f"'{escaped}'")

        return ExecResult(
            stdout=f"[{', '.join(formatted)}]\n",
            stderr="",
            exit_code=0,
        )


class PrintenvCommand:
    """printenv.py - prints environment variable values, one per line.

    Prints "None" for variables that are not set (matching Python's printenv.py).
    """

    name = "printenv.py"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        values = [ctx.env.get(name, "None") for name in args]
        output = "\n".join(values)
        return ExecResult(
            stdout=f"{output}\n" if output else "",
            stderr="",
            exit_code=0,
        )


class StdoutStderrCommand:
    """stdout_stderr.py - outputs to both stdout and stderr."""

    name = "stdout_stderr.py"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        return ExecResult(
            stdout="STDOUT\n",
            stderr="STDERR\n",
            exit_code=0,
        )


class ReadFromFdCommand:
    """read_from_fd.py - reads from a file descriptor (simplified - reads from stdin)."""

    name = "read_from_fd.py"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        # In real bash, this reads from a specific FD. Here we just return stdin or empty.
        fd = args[0] if args else "0"
        if fd == "0" and ctx.stdin:
            return ExecResult(stdout=ctx.stdin, stderr="", exit_code=0)
        return ExecResult(stdout="", stderr="", exit_code=0)


# All test helper commands
TEST_HELPER_COMMANDS = [
    ArgvCommand(),
    PrintenvCommand(),
    StdoutStderrCommand(),
    ReadFromFdCommand(),
]


def get_test_helper_commands() -> list:
    """Get all test helper commands for registration."""
    return TEST_HELPER_COMMANDS.copy()
