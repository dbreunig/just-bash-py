"""Rg (ripgrep) command implementation."""

import re
from ...types import CommandContext, ExecResult


class RgCommand:
    """The rg (ripgrep) command - recursive grep."""

    name = "rg"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the rg command."""
        pattern = None
        paths: list[str] = []
        ignore_case = False
        show_line_numbers = True
        count_only = False
        files_only = False
        invert_match = False
        word_match = False

        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ("-i", "--ignore-case"):
                ignore_case = True
            elif arg in ("-n", "--line-number"):
                show_line_numbers = True
            elif arg in ("-N", "--no-line-number"):
                show_line_numbers = False
            elif arg in ("-c", "--count"):
                count_only = True
            elif arg in ("-l", "--files-with-matches"):
                files_only = True
            elif arg in ("-v", "--invert-match"):
                invert_match = True
            elif arg in ("-w", "--word-regexp"):
                word_match = True
            elif arg == "--help":
                return ExecResult(
                    stdout="Usage: rg [OPTIONS] PATTERN [PATH...]\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg.startswith("-"):
                pass  # Ignore unknown options
            elif pattern is None:
                pattern = arg
            else:
                paths.append(arg)
            i += 1

        if pattern is None:
            return ExecResult(
                stdout="",
                stderr="rg: no pattern given\n",
                exit_code=2,
            )

        if not paths:
            paths = ["."]

        # Build regex
        if word_match:
            pattern = r"\b" + pattern + r"\b"

        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ExecResult(
                stdout="",
                stderr=f"rg: regex error: {e}\n",
                exit_code=2,
            )

        output_lines = []
        found_match = False

        for path in paths:
            try:
                resolved = ctx.fs.resolve_path(ctx.cwd, path)
                stat = await ctx.fs.stat(resolved)

                if stat.is_directory:
                    # Recursive search
                    await self._search_directory(
                        ctx, resolved, path, regex, ignore_case, invert_match,
                        show_line_numbers, count_only, files_only, output_lines
                    )
                else:
                    # Search single file
                    self._found = await self._search_file(
                        ctx, resolved, path, regex, invert_match,
                        show_line_numbers, count_only, files_only, output_lines
                    )
                    if self._found:
                        found_match = True

            except FileNotFoundError:
                pass  # Skip missing files silently like rg does
            except Exception:
                pass

        # Check if we found any matches from output
        if output_lines:
            found_match = True

        output = "\n".join(output_lines)
        if output:
            output += "\n"

        return ExecResult(
            stdout=output,
            stderr="",
            exit_code=0 if found_match else 1,
        )

    async def _search_directory(
        self, ctx: CommandContext, path: str, display_path: str,
        regex, ignore_case: bool, invert_match: bool,
        show_line_numbers: bool, count_only: bool, files_only: bool,
        output_lines: list[str]
    ) -> None:
        """Search a directory recursively."""
        try:
            entries = await ctx.fs.readdir(path)

            for entry in sorted(entries):
                if entry.startswith("."):
                    continue

                entry_path = f"{path}/{entry}"
                entry_display = f"{display_path}/{entry}"

                try:
                    stat = await ctx.fs.stat(entry_path)

                    if stat.is_directory:
                        await self._search_directory(
                            ctx, entry_path, entry_display, regex, ignore_case,
                            invert_match, show_line_numbers, count_only, files_only,
                            output_lines
                        )
                    else:
                        await self._search_file(
                            ctx, entry_path, entry_display, regex, invert_match,
                            show_line_numbers, count_only, files_only, output_lines
                        )
                except Exception:
                    pass
        except Exception:
            pass

    async def _search_file(
        self, ctx: CommandContext, path: str, display_path: str,
        regex, invert_match: bool, show_line_numbers: bool,
        count_only: bool, files_only: bool, output_lines: list[str]
    ) -> bool:
        """Search a single file."""
        try:
            content = await ctx.fs.read_file(path)
        except Exception:
            return False

        lines = content.splitlines()
        matches = []

        for line_num, line in enumerate(lines, 1):
            match = regex.search(line)
            if invert_match:
                match = not match
            if match:
                matches.append((line_num, line))

        if not matches:
            return False

        if files_only:
            output_lines.append(display_path)
        elif count_only:
            output_lines.append(f"{display_path}:{len(matches)}")
        else:
            for line_num, line in matches:
                if show_line_numbers:
                    output_lines.append(f"{display_path}:{line_num}:{line}")
                else:
                    output_lines.append(f"{display_path}:{line}")

        return True
