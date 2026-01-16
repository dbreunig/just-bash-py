"""Read command implementation.

Usage: read [-r] [-d delim] [-n nchars] [-p prompt] [-t timeout] [name ...]

Read a line from stdin and split it into fields.

Options:
  -r        Do not treat backslash as escape character
  -d delim  Use delim as line delimiter instead of newline
  -n nchars Read only nchars characters
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
        array_name = None  # -a option
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
                delimiter = args[i]
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
            elif arg == "-p" and i + 1 < len(args):
                # Prompt option - we ignore it since we can't prompt
                i += 1
            elif arg == "-t" and i + 1 < len(args):
                # Timeout option - we ignore it
                i += 1
            elif arg.startswith("-"):
                # Unknown option - ignore for compatibility
                pass
            else:
                var_names.append(arg)
            i += 1

        # Default variable is REPLY
        if not var_names:
            var_names = ["REPLY"]

        # Get input from stdin
        stdin = ctx.stdin or ""

        # Find the line to read
        if delimiter == "\n":
            # Standard line reading
            lines = stdin.split("\n")
            line = lines[0] if lines else ""
        else:
            # Custom delimiter
            parts = stdin.split(delimiter)
            line = parts[0] if parts else ""

        # Apply nchars limit
        if nchars is not None:
            line = line[:nchars]

        # Process backslash escapes if not in raw mode
        if not raw_mode:
            # Handle backslash-newline continuation (remove them)
            line = line.replace("\\\n", "")
            # Handle other escapes
            result = []
            i = 0
            while i < len(line):
                if line[i] == "\\" and i + 1 < len(line):
                    # Escape the next character
                    result.append(line[i + 1])
                    i += 2
                else:
                    result.append(line[i])
                    i += 1
            line = "".join(result)

        # Split on IFS
        ifs = ctx.env.get("IFS", " \t\n")
        if ifs:
            # Split on IFS characters
            words = self._split_on_ifs(line, ifs)
        else:
            # Empty IFS - no splitting
            words = [line] if line else []

        # Handle -a option (read into array)
        if array_name:
            # Clear existing array elements
            prefix = f"{array_name}_"
            to_remove = [k for k in ctx.env if k.startswith(prefix) and not k.startswith(f"{array_name}__")]
            for k in to_remove:
                del ctx.env[k]

            # Mark as array
            ctx.env[f"{array_name}__is_array"] = "indexed"

            # Store each word as array element
            for idx, word in enumerate(words):
                ctx.env[f"{array_name}_{idx}"] = word

            exit_code = 0 if stdin else 1
            return ExecResult(stdout="", stderr="", exit_code=exit_code)

        # Assign to variables
        for i, var in enumerate(var_names):
            if i < len(words):
                if i == len(var_names) - 1:
                    # Last variable gets all remaining words
                    ctx.env[var] = " ".join(words[i:])
                else:
                    ctx.env[var] = words[i]
            else:
                ctx.env[var] = ""

        # Return success if we read something, failure if EOF
        exit_code = 0 if stdin else 1
        return ExecResult(stdout="", stderr="", exit_code=exit_code)

    def _split_on_ifs(self, value: str, ifs: str) -> list[str]:
        """Split a string on IFS characters."""
        if not value:
            return []

        # Identify IFS whitespace vs non-whitespace
        ifs_whitespace = "".join(c for c in ifs if c in " \t\n")

        # Simple split for whitespace-only IFS
        if ifs == ifs_whitespace:
            return value.split()

        # Complex case with non-whitespace delimiters
        result = []
        current = []
        i = 0
        while i < len(value):
            c = value[i]
            if c in ifs_whitespace:
                if current:
                    result.append("".join(current))
                    current = []
                # Skip consecutive whitespace
                while i < len(value) and value[i] in ifs_whitespace:
                    i += 1
            elif c in ifs:
                # Non-whitespace delimiter
                result.append("".join(current))
                current = []
                i += 1
            else:
                current.append(c)
                i += 1

        if current:
            result.append("".join(current))

        return result
