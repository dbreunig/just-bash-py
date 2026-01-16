"""Grep command implementation.

Usage: grep [OPTION]... PATTERN [FILE]...

Search for PATTERN in each FILE.
With no FILE, or when FILE is -, read standard input.

Options:
  -i, --ignore-case     ignore case distinctions
  -v, --invert-match    select non-matching lines
  -c, --count           print only a count of matching lines per FILE
  -l, --files-with-matches  print only names of FILEs with matches
  -L, --files-without-match  print only names of FILEs without matches
  -n, --line-number     print line number with output lines
  -H, --with-filename   print the file name for each match
  -h, --no-filename     suppress the file name prefix on output
  -o, --only-matching   show only the part of a line matching PATTERN
  -q, --quiet, --silent suppress all normal output
  -r, -R, --recursive   recursively search directories
  -E, --extended-regexp PATTERN is an extended regular expression
  -F, --fixed-strings   PATTERN is a set of newline-separated strings
  -w, --word-regexp     match only whole words
  -x, --line-regexp     match only whole lines
"""

import re
from ...types import CommandContext, ExecResult


class GrepCommand:
    """The grep command."""

    name = "grep"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the grep command."""
        ignore_case = False
        invert_match = False
        count_only = False
        files_with_matches = False
        files_without_match = False
        line_numbers = False
        with_filename = None  # None means auto-detect based on file count
        only_matching = False
        quiet = False
        recursive = False
        extended_regexp = False
        fixed_strings = False
        word_regexp = False
        line_regexp = False

        pattern = None
        files: list[str] = []

        # Parse arguments
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--":
                if pattern is None and i + 1 < len(args):
                    pattern = args[i + 1]
                    files.extend(args[i + 2:])
                else:
                    files.extend(args[i + 1:])
                break
            elif arg.startswith("--"):
                if arg == "--ignore-case":
                    ignore_case = True
                elif arg == "--invert-match":
                    invert_match = True
                elif arg == "--count":
                    count_only = True
                elif arg == "--files-with-matches":
                    files_with_matches = True
                elif arg == "--files-without-match":
                    files_without_match = True
                elif arg == "--line-number":
                    line_numbers = True
                elif arg == "--with-filename":
                    with_filename = True
                elif arg == "--no-filename":
                    with_filename = False
                elif arg == "--only-matching":
                    only_matching = True
                elif arg == "--quiet" or arg == "--silent":
                    quiet = True
                elif arg == "--recursive":
                    recursive = True
                elif arg == "--extended-regexp":
                    extended_regexp = True
                elif arg == "--fixed-strings":
                    fixed_strings = True
                elif arg == "--word-regexp":
                    word_regexp = True
                elif arg == "--line-regexp":
                    line_regexp = True
                else:
                    return ExecResult(
                        stdout="",
                        stderr=f"grep: unrecognized option '{arg}'\n",
                        exit_code=2,
                    )
            elif arg.startswith("-") and arg != "-":
                for c in arg[1:]:
                    if c == 'i':
                        ignore_case = True
                    elif c == 'v':
                        invert_match = True
                    elif c == 'c':
                        count_only = True
                    elif c == 'l':
                        files_with_matches = True
                    elif c == 'L':
                        files_without_match = True
                    elif c == 'n':
                        line_numbers = True
                    elif c == 'H':
                        with_filename = True
                    elif c == 'h':
                        with_filename = False
                    elif c == 'o':
                        only_matching = True
                    elif c == 'q':
                        quiet = True
                    elif c == 'r' or c == 'R':
                        recursive = True
                    elif c == 'E':
                        extended_regexp = True
                    elif c == 'F':
                        fixed_strings = True
                    elif c == 'w':
                        word_regexp = True
                    elif c == 'x':
                        line_regexp = True
                    else:
                        return ExecResult(
                            stdout="",
                            stderr=f"grep: invalid option -- '{c}'\n",
                            exit_code=2,
                        )
            elif pattern is None:
                pattern = arg
            else:
                files.append(arg)
            i += 1

        if pattern is None:
            return ExecResult(
                stdout="",
                stderr="grep: pattern not specified\n",
                exit_code=2,
            )

        # Default to stdin
        if not files:
            files = ["-"]

        # Auto-detect filename display
        if with_filename is None:
            with_filename = len(files) > 1

        # Build regex pattern
        try:
            if fixed_strings:
                # Escape all regex metacharacters
                pattern = re.escape(pattern)
            if word_regexp:
                pattern = r'\b' + pattern + r'\b'
            if line_regexp:
                pattern = '^' + pattern + '$'

            flags = re.IGNORECASE if ignore_case else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ExecResult(
                stdout="",
                stderr=f"grep: invalid pattern '{pattern}': {e}\n",
                exit_code=2,
            )

        stdout = ""
        stderr = ""
        found_match = False

        for file in files:
            try:
                if file == "-":
                    content = ctx.stdin
                else:
                    path = ctx.fs.resolve_path(ctx.cwd, file)
                    content = await ctx.fs.read_file(path)

                lines = content.split("\n")
                # Handle trailing empty line from split
                if lines and lines[-1] == "":
                    lines = lines[:-1]

                match_count = 0
                file_has_match = False

                for line_num, line in enumerate(lines, 1):
                    match = regex.search(line)
                    matches_pattern = bool(match)

                    if invert_match:
                        matches_pattern = not matches_pattern

                    if matches_pattern:
                        match_count += 1
                        file_has_match = True
                        found_match = True

                        if quiet:
                            return ExecResult(stdout="", stderr="", exit_code=0)

                        if files_with_matches:
                            continue

                        if not count_only and not files_without_match:
                            if only_matching and match and not invert_match:
                                output = match.group(0)
                            else:
                                output = line

                            parts = []
                            if with_filename:
                                parts.append(f"{file}:")
                            if line_numbers:
                                parts.append(f"{line_num}:")
                            parts.append(output)
                            stdout += "".join(parts) + "\n"

                if count_only:
                    if with_filename:
                        stdout += f"{file}:{match_count}\n"
                    else:
                        stdout += f"{match_count}\n"
                elif files_with_matches and file_has_match:
                    stdout += f"{file}\n"
                elif files_without_match and not file_has_match:
                    stdout += f"{file}\n"

            except FileNotFoundError:
                stderr += f"grep: {file}: No such file or directory\n"
            except IsADirectoryError:
                if recursive:
                    # TODO: Implement recursive search
                    pass
                else:
                    stderr += f"grep: {file}: Is a directory\n"

        exit_code = 0 if found_match else 1
        return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


class FgrepCommand(GrepCommand):
    """The fgrep command - grep with fixed strings."""

    name = "fgrep"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute fgrep (grep -F)."""
        return await super().execute(["-F"] + args, ctx)


class EgrepCommand(GrepCommand):
    """The egrep command - grep with extended regexp."""

    name = "egrep"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute egrep (grep -E)."""
        return await super().execute(["-E"] + args, ctx)
