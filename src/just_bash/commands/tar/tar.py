"""Tar command implementation."""

import io
import tarfile
import gzip
from datetime import datetime
from fnmatch import fnmatch

from ...types import CommandContext, ExecResult


class TarCommand:
    """The tar command - manipulate tape archives."""

    name = "tar"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the tar command."""
        if "--help" in args:
            return ExecResult(
                stdout=(
                    "Usage: tar [options] [file...]\n"
                    "Create, extract, or list contents of tar archives.\n\n"
                    "Options:\n"
                    "  -c, --create     create a new archive\n"
                    "  -x, --extract    extract files from an archive\n"
                    "  -t, --list       list contents of an archive\n"
                    "  -f FILE          use archive file FILE\n"
                    "  -z, --gzip       filter archive through gzip\n"
                    "  -v, --verbose    verbosely list files processed\n"
                    "  -C DIR           change to directory DIR\n"
                    "  --help           display this help\n"
                ),
                stderr="",
                exit_code=0,
            )

        # Parse options
        create = False
        extract = False
        list_mode = False
        archive_file = ""
        use_gzip = False
        verbose = False
        directory = ""
        files: list[str] = []

        i = 0
        while i < len(args):
            arg = args[i]

            # Handle combined short options (e.g., -cvzf)
            if arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
                j = 1
                while j < len(arg):
                    char = arg[j]
                    if char == "c":
                        create = True
                    elif char == "x":
                        extract = True
                    elif char == "t":
                        list_mode = True
                    elif char == "z":
                        use_gzip = True
                    elif char == "v":
                        verbose = True
                    elif char == "f":
                        # -f requires a value
                        if j < len(arg) - 1:
                            archive_file = arg[j + 1:]
                            j = len(arg)
                        else:
                            i += 1
                            if i >= len(args):
                                return ExecResult(
                                    stdout="",
                                    stderr="tar: option requires an argument -- 'f'\n",
                                    exit_code=2,
                                )
                            archive_file = args[i]
                    elif char == "C":
                        if j < len(arg) - 1:
                            directory = arg[j + 1:]
                            j = len(arg)
                        else:
                            i += 1
                            if i >= len(args):
                                return ExecResult(
                                    stdout="",
                                    stderr="tar: option requires an argument -- 'C'\n",
                                    exit_code=2,
                                )
                            directory = args[i]
                    else:
                        return ExecResult(
                            stdout="",
                            stderr=f"tar: invalid option -- '{char}'\n",
                            exit_code=2,
                        )
                    j += 1
                i += 1
                continue

            # Long options and single short options
            if arg in ("-c", "--create"):
                create = True
            elif arg in ("-x", "--extract", "--get"):
                extract = True
            elif arg in ("-t", "--list"):
                list_mode = True
            elif arg in ("-z", "--gzip", "--gunzip"):
                use_gzip = True
            elif arg in ("-v", "--verbose"):
                verbose = True
            elif arg == "-f" or arg == "--file":
                i += 1
                if i >= len(args):
                    return ExecResult(
                        stdout="",
                        stderr="tar: option requires an argument -- 'f'\n",
                        exit_code=2,
                    )
                archive_file = args[i]
            elif arg.startswith("--file="):
                archive_file = arg[7:]
            elif arg in ("-C", "--directory"):
                i += 1
                if i >= len(args):
                    return ExecResult(
                        stdout="",
                        stderr="tar: option requires an argument -- 'C'\n",
                        exit_code=2,
                    )
                directory = args[i]
            elif arg.startswith("--directory="):
                directory = arg[12:]
            elif arg == "--":
                files.extend(args[i + 1:])
                break
            elif arg.startswith("-"):
                return ExecResult(
                    stdout="",
                    stderr=f"tar: invalid option -- '{arg}'\n",
                    exit_code=2,
                )
            else:
                files.append(arg)
            i += 1

        # Validate operation mode
        op_count = sum([create, extract, list_mode])
        if op_count == 0:
            return ExecResult(
                stdout="",
                stderr="tar: You must specify one of -c, -x, or -t\n",
                exit_code=2,
            )
        if op_count > 1:
            return ExecResult(
                stdout="",
                stderr="tar: You may not specify more than one of -c, -x, or -t\n",
                exit_code=2,
            )

        # Determine work directory
        work_dir = ctx.fs.resolve_path(ctx.cwd, directory) if directory else ctx.cwd

        if create:
            return await self._create_archive(
                ctx, archive_file, files, work_dir, use_gzip, verbose
            )
        elif extract:
            return await self._extract_archive(
                ctx, archive_file, files, work_dir, use_gzip, verbose
            )
        else:  # list_mode
            return await self._list_archive(
                ctx, archive_file, files, use_gzip, verbose
            )

    async def _create_archive(
        self,
        ctx: CommandContext,
        archive_file: str,
        files: list[str],
        work_dir: str,
        use_gzip: bool,
        verbose: bool,
    ) -> ExecResult:
        """Create a tar archive."""
        if not files:
            return ExecResult(
                stdout="",
                stderr="tar: Cowardly refusing to create an empty archive\n",
                exit_code=2,
            )

        # Create archive in memory
        buffer = io.BytesIO()
        mode = "w:gz" if use_gzip else "w"

        try:
            tar = tarfile.open(fileobj=buffer, mode=mode)
        except Exception as e:
            return ExecResult(
                stdout="",
                stderr=f"tar: error opening archive: {e}\n",
                exit_code=2,
            )

        verbose_output = ""
        errors: list[str] = []

        for file_path in files:
            try:
                await self._add_to_archive(
                    ctx, tar, work_dir, file_path, verbose, errors
                )
                if verbose:
                    verbose_output += f"{file_path}\n"
            except Exception as e:
                errors.append(f"tar: {file_path}: {e}")

        tar.close()

        # Write archive to file or stdout
        archive_data = buffer.getvalue()
        if archive_file and archive_file != "-":
            archive_path = ctx.fs.resolve_path(ctx.cwd, archive_file)
            try:
                await ctx.fs.write_file(archive_path, archive_data)
            except Exception as e:
                return ExecResult(
                    stdout="",
                    stderr=f"tar: {archive_file}: {e}\n",
                    exit_code=2,
                )
            stdout = ""
        else:
            # Output binary to stdout
            stdout = archive_data.decode("latin-1")

        stderr = verbose_output
        if errors:
            stderr += "\n".join(errors) + "\n"
        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=2 if errors else 0,
        )

    async def _add_to_archive(
        self,
        ctx: CommandContext,
        tar: tarfile.TarFile,
        base_path: str,
        relative_path: str,
        verbose: bool,
        errors: list[str],
    ) -> None:
        """Add a file or directory to the archive."""
        full_path = ctx.fs.resolve_path(base_path, relative_path)

        try:
            stat = await ctx.fs.stat(full_path)
        except FileNotFoundError:
            errors.append(f"tar: {relative_path}: No such file or directory")
            return

        # Get mtime - handle both float and datetime
        mtime = stat.mtime
        if hasattr(mtime, 'timestamp'):
            mtime = int(mtime.timestamp())
        elif isinstance(mtime, (int, float)):
            mtime = int(mtime)
        else:
            mtime = 0

        if stat.is_directory:
            # Add directory entry
            info = tarfile.TarInfo(name=relative_path)
            info.type = tarfile.DIRTYPE
            info.mode = stat.mode
            info.mtime = mtime
            tar.addfile(info)

            # Add contents recursively
            items = await ctx.fs.readdir(full_path)
            for item in items:
                child_path = f"{relative_path}/{item}" if relative_path else item
                await self._add_to_archive(ctx, tar, base_path, child_path, verbose, errors)

        elif stat.is_file:
            content = await ctx.fs.read_file_bytes(full_path)
            info = tarfile.TarInfo(name=relative_path)
            info.size = len(content)
            info.mode = stat.mode
            info.mtime = mtime
            tar.addfile(info, io.BytesIO(content))

        elif stat.is_symlink:
            target = await ctx.fs.readlink(full_path)
            info = tarfile.TarInfo(name=relative_path)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            info.mode = stat.mode
            tar.addfile(info)

    async def _extract_archive(
        self,
        ctx: CommandContext,
        archive_file: str,
        specific_files: list[str],
        work_dir: str,
        use_gzip: bool,
        verbose: bool,
    ) -> ExecResult:
        """Extract a tar archive."""
        # Read archive
        if archive_file and archive_file != "-":
            archive_path = ctx.fs.resolve_path(ctx.cwd, archive_file)
            try:
                archive_data = await ctx.fs.read_file_bytes(archive_path)
            except FileNotFoundError:
                return ExecResult(
                    stdout="",
                    stderr=f"tar: {archive_file}: Cannot open: No such file or directory\n",
                    exit_code=2,
                )
        else:
            archive_data = ctx.stdin.encode("latin-1")

        # Open archive
        buffer = io.BytesIO(archive_data)
        try:
            # Auto-detect compression or use explicit flag
            if use_gzip or self._is_gzip(archive_data):
                tar = tarfile.open(fileobj=buffer, mode="r:gz")
            else:
                tar = tarfile.open(fileobj=buffer, mode="r")
        except Exception as e:
            return ExecResult(
                stdout="",
                stderr=f"tar: error opening archive: {e}\n",
                exit_code=2,
            )

        verbose_output = ""
        errors: list[str] = []

        # Create work directory if needed
        try:
            await ctx.fs.mkdir(work_dir, recursive=True)
        except Exception:
            pass

        for member in tar.getmembers():
            name = member.name

            # Check if specific files requested
            if specific_files:
                if not any(
                    name == f or name.startswith(f"{f}/") or fnmatch(name, f)
                    for f in specific_files
                ):
                    continue

            target_path = ctx.fs.resolve_path(work_dir, name)

            try:
                if member.isdir():
                    await ctx.fs.mkdir(target_path, recursive=True)
                elif member.isfile():
                    # Ensure parent directory exists
                    parent = target_path.rsplit("/", 1)[0]
                    if parent:
                        try:
                            await ctx.fs.mkdir(parent, recursive=True)
                        except Exception:
                            pass

                    f = tar.extractfile(member)
                    if f:
                        content = f.read()
                        await ctx.fs.write_file(target_path, content)
                elif member.issym():
                    parent = target_path.rsplit("/", 1)[0]
                    if parent:
                        try:
                            await ctx.fs.mkdir(parent, recursive=True)
                        except Exception:
                            pass
                    try:
                        await ctx.fs.symlink(member.linkname, target_path)
                    except Exception:
                        pass

                if verbose:
                    verbose_output += f"{name}\n"

            except Exception as e:
                errors.append(f"tar: {name}: {e}")

        tar.close()

        stderr = verbose_output
        if errors:
            stderr += "\n".join(errors) + "\n"
        return ExecResult(
            stdout="",
            stderr=stderr,
            exit_code=2 if errors else 0,
        )

    async def _list_archive(
        self,
        ctx: CommandContext,
        archive_file: str,
        specific_files: list[str],
        use_gzip: bool,
        verbose: bool,
    ) -> ExecResult:
        """List contents of a tar archive."""
        # Read archive
        if archive_file and archive_file != "-":
            archive_path = ctx.fs.resolve_path(ctx.cwd, archive_file)
            try:
                archive_data = await ctx.fs.read_file_bytes(archive_path)
            except FileNotFoundError:
                return ExecResult(
                    stdout="",
                    stderr=f"tar: {archive_file}: Cannot open: No such file or directory\n",
                    exit_code=2,
                )
        else:
            archive_data = ctx.stdin.encode("latin-1")

        # Open archive
        buffer = io.BytesIO(archive_data)
        try:
            if use_gzip or self._is_gzip(archive_data):
                tar = tarfile.open(fileobj=buffer, mode="r:gz")
            else:
                tar = tarfile.open(fileobj=buffer, mode="r")
        except Exception as e:
            return ExecResult(
                stdout="",
                stderr=f"tar: error opening archive: {e}\n",
                exit_code=2,
            )

        stdout = ""

        for member in tar.getmembers():
            name = member.name

            # Check if specific files requested
            if specific_files:
                if not any(
                    name == f or name.startswith(f"{f}/") or fnmatch(name, f)
                    for f in specific_files
                ):
                    continue

            if verbose:
                # Verbose format
                mode_str = self._format_mode(member.mode, member.isdir())
                owner = f"{member.uid}/{member.gid}"
                size = str(member.size).rjust(8)
                mtime = datetime.fromtimestamp(member.mtime)
                date_str = mtime.strftime("%b %d %H:%M")
                line = f"{mode_str} {owner:<10} {size} {date_str} {name}"
                if member.issym():
                    line += f" -> {member.linkname}"
                stdout += f"{line}\n"
            else:
                stdout += f"{name}\n"

        tar.close()
        return ExecResult(stdout=stdout, stderr="", exit_code=0)

    def _is_gzip(self, data: bytes) -> bool:
        """Check if data is gzip compressed."""
        return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B

    def _format_mode(self, mode: int, is_dir: bool) -> str:
        """Format file mode like ls -l."""
        chars = "d" if is_dir else "-"
        perms = [
            "r" if mode & 0o400 else "-",
            "w" if mode & 0o200 else "-",
            "x" if mode & 0o100 else "-",
            "r" if mode & 0o040 else "-",
            "w" if mode & 0o020 else "-",
            "x" if mode & 0o010 else "-",
            "r" if mode & 0o004 else "-",
            "w" if mode & 0o002 else "-",
            "x" if mode & 0o001 else "-",
        ]
        return chars + "".join(perms)
