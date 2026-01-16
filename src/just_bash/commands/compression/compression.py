"""Compression command implementations (gzip, gunzip, zcat)."""

import gzip
from ...types import CommandContext, ExecResult


class GzipCommand:
    """The gzip command - compress files."""

    name = "gzip"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the gzip command."""
        decompress = False
        keep_original = False
        force = False
        stdout_mode = False
        verbose = False
        level = 6
        files: list[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ("-d", "--decompress", "--uncompress"):
                decompress = True
            elif arg in ("-k", "--keep"):
                keep_original = True
            elif arg in ("-f", "--force"):
                force = True
            elif arg in ("-c", "--stdout", "--to-stdout"):
                stdout_mode = True
            elif arg in ("-v", "--verbose"):
                verbose = True
            elif arg in ("-1", "--fast"):
                level = 1
            elif arg in ("-9", "--best"):
                level = 9
            elif arg.startswith("-") and len(arg) == 2 and arg[1].isdigit():
                level = int(arg[1])
            elif arg == "--help":
                return ExecResult(
                    stdout="Usage: gzip [OPTION]... [FILE]...\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg == "--":
                files.extend(args[i + 1:])
                break
            elif arg.startswith("-"):
                # Handle combined short options
                for c in arg[1:]:
                    if c == "d":
                        decompress = True
                    elif c == "k":
                        keep_original = True
                    elif c == "f":
                        force = True
                    elif c == "c":
                        stdout_mode = True
                    elif c == "v":
                        verbose = True
                    elif c.isdigit():
                        level = int(c)
            else:
                files.append(arg)
            i += 1

        # Read from stdin if no files
        if not files:
            if ctx.stdin:
                return await self._process_stdin(ctx, decompress, level)
            return ExecResult(
                stdout="",
                stderr="gzip: missing operand\n",
                exit_code=1,
            )

        stdout_parts = []
        stderr = ""
        exit_code = 0

        for file in files:
            try:
                path = ctx.fs.resolve_path(ctx.cwd, file)
                content = await ctx.fs.read_file_bytes(path)

                if decompress:
                    if not file.endswith(".gz") and not force:
                        stderr += f"gzip: {file}: unknown suffix -- ignored\n"
                        continue
                    try:
                        result = gzip.decompress(content)
                    except Exception as e:
                        stderr += f"gzip: {file}: {e}\n"
                        exit_code = 1
                        continue

                    if stdout_mode:
                        stdout_parts.append(result.decode("utf-8", errors="replace"))
                    else:
                        new_path = path[:-3] if path.endswith(".gz") else path + ".out"
                        await ctx.fs.write_file(new_path, result)
                        if not keep_original:
                            await ctx.fs.rm(path)
                else:
                    result = gzip.compress(content, compresslevel=level)

                    if stdout_mode:
                        # Can't output binary to stdout in text mode
                        stdout_parts.append(f"<binary gzip data, {len(result)} bytes>")
                    else:
                        new_path = path + ".gz"
                        await ctx.fs.write_file(new_path, result)
                        if not keep_original:
                            await ctx.fs.rm(path)

            except FileNotFoundError:
                stderr += f"gzip: {file}: No such file or directory\n"
                exit_code = 1
            except IsADirectoryError:
                stderr += f"gzip: {file}: Is a directory\n"
                exit_code = 1

        stdout = "".join(stdout_parts)
        return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

    async def _process_stdin(
        self, ctx: CommandContext, decompress: bool, level: int
    ) -> ExecResult:
        """Process stdin."""
        try:
            content = ctx.stdin.encode("utf-8")
            if decompress:
                result = gzip.decompress(content)
                return ExecResult(
                    stdout=result.decode("utf-8", errors="replace"),
                    stderr="",
                    exit_code=0,
                )
            else:
                result = gzip.compress(content, compresslevel=level)
                return ExecResult(
                    stdout=f"<binary gzip data, {len(result)} bytes>",
                    stderr="",
                    exit_code=0,
                )
        except Exception as e:
            return ExecResult(stdout="", stderr=f"gzip: {e}\n", exit_code=1)


class GunzipCommand:
    """The gunzip command - decompress files."""

    name = "gunzip"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute gunzip (gzip -d)."""
        gzip_cmd = GzipCommand()
        return await gzip_cmd.execute(["-d"] + args, ctx)


class ZcatCommand:
    """The zcat command - decompress to stdout."""

    name = "zcat"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute zcat (gzip -dc)."""
        gzip_cmd = GzipCommand()
        return await gzip_cmd.execute(["-dc"] + args, ctx)
