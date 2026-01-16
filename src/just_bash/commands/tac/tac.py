"""Tac command implementation."""

from ...types import CommandContext, ExecResult


class TacCommand:
    """The tac command - reverse lines."""

    name = "tac"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the tac command."""
        files: list[str] = []

        for arg in args:
            if arg == "--help":
                return ExecResult(
                    stdout="Usage: tac [OPTION]... [FILE]...\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg.startswith("-") and len(arg) > 1:
                pass  # Ignore unknown options
            else:
                files.append(arg)

        # Read content
        if files:
            content_parts = []
            for f in files:
                try:
                    path = ctx.fs.resolve_path(ctx.cwd, f)
                    content_parts.append(await ctx.fs.read_file(path))
                except FileNotFoundError:
                    return ExecResult(
                        stdout="",
                        stderr=f"tac: {f}: No such file or directory\n",
                        exit_code=1,
                    )
            content = "".join(content_parts)
        else:
            content = ctx.stdin

        if not content:
            return ExecResult(stdout="", stderr="", exit_code=0)

        # Reverse lines
        lines = content.splitlines()
        reversed_lines = list(reversed(lines))

        output = "\n".join(reversed_lines)
        if content.endswith("\n"):
            output += "\n"

        return ExecResult(stdout=output, stderr="", exit_code=0)
