"""Touch command implementation.

Usage: touch [OPTION]... FILE...

Update the access and modification times of each FILE to the current time.
A FILE argument that does not exist is created empty.

Options:
  -c, --no-create  do not create any files
"""

from ...types import CommandContext, ExecResult


class TouchCommand:
    """The touch command."""

    name = "touch"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the touch command."""
        no_create = False
        files: list[str] = []

        # Parse arguments
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--":
                files.extend(args[i + 1:])
                break
            elif arg.startswith("--"):
                if arg == "--no-create":
                    no_create = True
                else:
                    return ExecResult(
                        stdout="",
                        stderr=f"touch: unrecognized option '{arg}'\n",
                        exit_code=1,
                    )
            elif arg.startswith("-") and arg != "-":
                for c in arg[1:]:
                    if c == "c":
                        no_create = True
                    else:
                        return ExecResult(
                            stdout="",
                            stderr=f"touch: invalid option -- '{c}'\n",
                            exit_code=1,
                        )
            else:
                files.append(arg)
            i += 1

        if not files:
            return ExecResult(
                stdout="",
                stderr="touch: missing file operand\n",
                exit_code=1,
            )

        stderr = ""
        exit_code = 0

        for f in files:
            try:
                path = ctx.fs.resolve_path(ctx.cwd, f)
                # Check if file exists
                try:
                    await ctx.fs.stat(path)
                    # File exists - update timestamp (no-op in our virtual fs)
                except FileNotFoundError:
                    # File doesn't exist
                    if no_create:
                        continue
                    # Create empty file
                    await ctx.fs.write_file(path, "")
            except FileNotFoundError:
                stderr += f"touch: cannot touch '{f}': No such file or directory\n"
                exit_code = 1
            except IsADirectoryError:
                # Touching a directory is fine, just update timestamp (no-op)
                pass

        return ExecResult(stdout="", stderr=stderr, exit_code=exit_code)
