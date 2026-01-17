"""Env and printenv command implementations."""

from ...types import CommandContext, ExecResult


class EnvCommand:
    """The env command - print environment."""

    name = "env"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the env command."""
        if "--help" in args:
            return ExecResult(
                stdout="Usage: env [OPTION]... [NAME=VALUE]... [COMMAND [ARG]...]\n",
                stderr="",
                exit_code=0,
            )

        # Print environment
        lines = [f"{k}={v}" for k, v in sorted(ctx.env.items())]
        return ExecResult(
            stdout="\n".join(lines) + "\n" if lines else "",
            stderr="",
            exit_code=0,
        )


class PrintenvCommand:
    """The printenv command - print environment variables."""

    name = "printenv"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the printenv command."""
        var_names: list[str] = []

        for arg in args:
            if arg == "--help":
                return ExecResult(
                    stdout="Usage: printenv [OPTION]... [VARIABLE]...\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg.startswith("-"):
                pass  # Ignore options
            else:
                var_names.append(arg)

        if not var_names:
            # Print all
            lines = [f"{k}={v}" for k, v in sorted(ctx.env.items())]
            return ExecResult(
                stdout="\n".join(lines) + "\n" if lines else "",
                stderr="",
                exit_code=0,
            )

        # Print specific variables
        output_lines = []
        exit_code = 0

        for name in var_names:
            if name in ctx.env:
                output_lines.append(ctx.env[name])
            else:
                exit_code = 1

        output = "\n".join(output_lines)
        if output:
            output += "\n"

        return ExecResult(stdout=output, stderr="", exit_code=exit_code)
