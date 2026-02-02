"""Read command implementation.

Usage: read [-r] [-d delim] [-n nchars] [-N nchars] [-p prompt] [-t timeout] [name ...]

Read a line from stdin and split it into fields.

Options:
  -r        Do not treat backslash as escape character
  -d delim  Use delim as line delimiter instead of newline
  -n nchars Read at most nchars characters
  -N nchars Read exactly nchars characters (no IFS splitting, ignores delimiters)
  -p prompt Output the string prompt before reading
  -t timeout Time out after timeout seconds

If no names are given, the line is stored in REPLY.
"""

from ...types import CommandContext, ExecResult


class ReadCommand:
    """The read builtin command."""

    name = "read"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the read command."""
        # Parse options
        raw_mode = False
        delimiter = "\n"
        nchars = None
        no_split = False  # -N mode: no IFS splitting
        array_name = None  # -a option
        fd_num = None  # -u option
        var_names = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-r":
                raw_mode = True
            elif arg == "-a" and i + 1 < len(args):
                i += 1
                array_name = args[i]
            elif arg == "-d" and i + 1 < len(args):
                i += 1
                delimiter = args[i] if args[i] else "\0"
            elif arg.startswith("-d") and len(arg) > 2:
                delimiter = arg[2:]
            elif arg == "-n" and i + 1 < len(args):
                i += 1
                try:
                    nchars = int(args[i])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {args[i]}: invalid number\n",
                        exit_code=1,
                    )
            elif arg.startswith("-n") and len(arg) > 2:
                try:
                    nchars = int(arg[2:])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {arg[2:]}: invalid number\n",
                        exit_code=1,
                    )
            elif arg == "-N" and i + 1 < len(args):
                i += 1
                try:
                    nchars = int(args[i])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {args[i]}: invalid number\n",
                        exit_code=1,
                    )
                no_split = True
                delimiter = ""  # -N ignores delimiters
            elif arg.startswith("-N") and len(arg) > 2:
                try:
                    nchars = int(arg[2:])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {arg[2:]}: invalid number\n",
                        exit_code=1,
                    )
                no_split = True
                delimiter = ""  # -N ignores delimiters
            elif arg == "-u" and i + 1 < len(args):
                i += 1
                try:
                    fd_num = int(args[i])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {args[i]}: invalid file descriptor\n",
                        exit_code=1,
                    )
            elif arg.startswith("-u") and len(arg) > 2:
                try:
                    fd_num = int(arg[2:])
                except ValueError:
                    return ExecResult(
                        stdout="",
                        stderr=f"bash: read: {arg[2:]}: invalid file descriptor\n",
                        exit_code=1,
                    )
            elif arg == "-p" and i + 1 < len(args):
                i += 1
            elif arg == "-t" and i + 1 < len(args):
                i += 1
            elif arg.startswith("-"):
                pass
            else:
                var_names.append(arg)
            i += 1

        # Track whether we're using default REPLY
        use_reply = not var_names and not array_name
        if not var_names:
            var_names = ["REPLY"]

        # Get input from stdin or custom FD
        if fd_num is not None and fd_num >= 3:
            fd_contents = getattr(ctx, 'fd_contents', {})
            stdin = fd_contents.get(fd_num, "")
        else:
            stdin = ctx.stdin or ""

        # Determine if input was properly terminated by delimiter
        # (affects exit code: 1 if no terminating delimiter found)
        eof_reached = False
        if not stdin:
            eof_reached = True
        elif no_split:
            # -N mode: EOF if fewer chars available than requested
            if nchars is not None and len(stdin) < nchars:
                eof_reached = True
        elif delimiter not in stdin:
            eof_reached = True

        # Find the line to read
        if delimiter == "":
            # -N mode: read raw bytes, no delimiter processing
            line = stdin
        elif delimiter == "\n":
            lines = stdin.split("\n")
            line = lines[0] if lines else ""
        else:
            parts = stdin.split(delimiter)
            line = parts[0] if parts else ""

        # Apply nchars limit
        if nchars is not None:
            line = line[:nchars]

        # Process backslash escapes if not in raw mode and not -N mode
        if not raw_mode and not no_split:
            line = line.replace("\\\n", "")
            result = []
            ci = 0
            while ci < len(line):
                if line[ci] == "\\" and ci + 1 < len(line):
                    result.append(line[ci + 1])
                    ci += 2
                else:
                    result.append(line[ci])
                    ci += 1
            line = "".join(result)

        # Get IFS
        ifs = ctx.env.get("IFS", " \t\n")

        # Handle -a option (read into array)
        if array_name:
            # Split on IFS for array assignment
            if no_split:
                words = [line] if line else []
            elif ifs:
                words = self._split_on_ifs(line, ifs)
            else:
                words = [line] if line else []

            # Clear existing array elements
            prefix = f"{array_name}_"
            to_remove = [k for k in ctx.env if k.startswith(prefix) and not k.startswith(f"{array_name}__")]
            for k in to_remove:
                del ctx.env[k]

            ctx.env[f"{array_name}__is_array"] = "indexed"

            for idx, word in enumerate(words):
                ctx.env[f"{array_name}_{idx}"] = word

            return ExecResult(stdout="", stderr="", exit_code=1 if eof_reached else 0)

        # Assign to variables
        if no_split:
            # -N mode: no IFS splitting at all
            if len(var_names) == 1:
                ctx.env[var_names[0]] = line
            else:
                # Even with multiple vars, -N doesn't split
                ctx.env[var_names[0]] = line
                for v in var_names[1:]:
                    ctx.env[v] = ""
        elif use_reply or len(var_names) == 1:
            # Single variable or REPLY: no IFS splitting
            # But strip leading/trailing IFS whitespace
            stripped = self._strip_ifs_whitespace(line, ifs)
            ctx.env[var_names[0]] = stripped
        elif not ifs:
            # Empty IFS: no splitting
            ctx.env[var_names[0]] = line
            for v in var_names[1:]:
                ctx.env[v] = ""
        else:
            # Multiple variables: split on IFS
            self._assign_split_vars(line, var_names, ifs, ctx)

        return ExecResult(stdout="", stderr="", exit_code=1 if eof_reached else 0)

    def _strip_ifs_whitespace(self, value: str, ifs: str) -> str:
        """Strip leading and trailing IFS whitespace characters."""
        if not ifs:
            return value
        ifs_ws = set(c for c in ifs if c in " \t\n")
        if not ifs_ws:
            return value
        # Strip leading
        start = 0
        while start < len(value) and value[start] in ifs_ws:
            start += 1
        # Strip trailing
        end = len(value)
        while end > start and value[end - 1] in ifs_ws:
            end -= 1
        return value[start:end]

    def _assign_split_vars(self, line: str, var_names: list[str], ifs: str, ctx: CommandContext) -> None:
        """Split line on IFS and assign to multiple variables.

        The last variable gets the remainder of the line (preserving
        original separators from the input).
        """
        ifs_ws = set(c for c in ifs if c in " \t\n")
        ifs_nonws = set(c for c in ifs if c not in " \t\n")

        # We need to track positions in the original line so the last
        # variable gets the remainder from the original string
        num_vars = len(var_names)
        words = []
        pos = 0

        # Skip leading IFS whitespace
        while pos < len(line) and line[pos] in ifs_ws:
            pos += 1

        for var_idx in range(num_vars):
            if pos >= len(line):
                # No more input - set remaining vars to empty
                for vi in range(var_idx, num_vars):
                    ctx.env[var_names[vi]] = ""
                return

            if var_idx == num_vars - 1:
                # Last variable: gets the rest of the line, with trailing
                # IFS whitespace stripped
                remainder = line[pos:]
                # Strip trailing IFS whitespace
                end = len(remainder)
                while end > 0 and remainder[end - 1] in ifs_ws:
                    end -= 1
                ctx.env[var_names[var_idx]] = remainder[:end]
                return

            # Collect next word
            word_start = pos
            while pos < len(line) and line[pos] not in ifs_ws and line[pos] not in ifs_nonws:
                pos += 1

            word = line[word_start:pos]
            ctx.env[var_names[var_idx]] = word

            # Skip IFS delimiters between words
            # Whitespace IFS chars: skip all consecutive
            # Non-whitespace IFS chars: each one is a delimiter
            # Whitespace around non-whitespace is part of the delimiter
            if pos < len(line):
                # Skip leading whitespace
                while pos < len(line) and line[pos] in ifs_ws:
                    pos += 1
                # If we hit a non-whitespace delimiter, consume it
                if pos < len(line) and line[pos] in ifs_nonws:
                    pos += 1
                    # Skip trailing whitespace after non-ws delimiter
                    while pos < len(line) and line[pos] in ifs_ws:
                        pos += 1

        # Shouldn't reach here, but just in case
        for vi in range(len(words), num_vars):
            if var_names[vi] not in ctx.env:
                ctx.env[var_names[vi]] = ""

    def _split_on_ifs(self, value: str, ifs: str) -> list[str]:
        """Split a string on IFS characters.

        Follows bash IFS splitting rules:
        - IFS whitespace (space, tab, newline): leading/trailing stripped,
          consecutive act as single separator
        - IFS non-whitespace: each occurrence is a separator, consecutive
          produce empty fields
        - Mixed: whitespace adjacent to non-whitespace is part of the delimiter
        """
        if not value:
            return []

        ifs_ws = set(c for c in ifs if c in " \t\n")
        ifs_nonws = set(c for c in ifs if c not in " \t\n")

        # Whitespace-only IFS: simple split (strips leading/trailing, merges consecutive)
        if not ifs_nonws:
            return value.split()

        result = []
        current = []
        pos = 0

        # Skip leading IFS whitespace
        while pos < len(value) and value[pos] in ifs_ws:
            pos += 1

        while pos < len(value):
            c = value[pos]
            if c in ifs_nonws:
                # Non-whitespace delimiter: always produces field boundary
                result.append("".join(current))
                current = []
                pos += 1
                # Skip trailing IFS whitespace after non-ws delimiter
                while pos < len(value) and value[pos] in ifs_ws:
                    pos += 1
            elif c in ifs_ws:
                # IFS whitespace
                if current:
                    result.append("".join(current))
                    current = []
                # Skip consecutive whitespace
                while pos < len(value) and value[pos] in ifs_ws:
                    pos += 1
                # If next char is non-ws delimiter, it's part of this delimiter run
                # (don't start a new field yet - the non-ws handler will do it)
            else:
                current.append(c)
                pos += 1

        # Add last field if non-empty
        if current:
            result.append("".join(current))

        return result
