"""Printf command implementation."""

import re
from ...types import CommandContext, ExecResult


class PrintfCommand:
    """The printf command."""

    name = "printf"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the printf command."""
        if not args:
            return ExecResult(
                stdout="",
                stderr="printf: usage: printf [-v var] format [arguments]\n",
                exit_code=2,
            )

        # Parse -v option and -- end-of-options
        var_name = None
        format_start = 0
        if len(args) >= 2 and args[0] == "-v":
            var_name = args[1]
            format_start = 2
        if format_start < len(args) and args[format_start] == "--":
            format_start += 1

        if len(args) <= format_start:
            return ExecResult(
                stdout="",
                stderr="printf: usage: printf [-v var] format [arguments]\n",
                exit_code=2,
            )

        format_str = args[format_start]
        arguments = args[format_start + 1:]

        try:
            output = self._format(format_str, arguments)

            if var_name is not None:
                # Assign to variable instead of printing
                ctx.env[var_name] = output
                return ExecResult(stdout="", stderr="", exit_code=0)

            return ExecResult(stdout=output, stderr="", exit_code=0)
        except ValueError as e:
            return ExecResult(stdout="", stderr=f"printf: {e}\n", exit_code=1)

    def _format(self, format_str: str, arguments: list[str]) -> str:
        """Format the string with arguments.

        Supports format reuse: if there are more arguments than format specifiers,
        the format string is reused for the remaining arguments.
        """
        result = []
        arg_index = 0

        # Continue formatting until all arguments are consumed
        while True:
            start_arg_index = arg_index
            formatted, arg_index = self._format_once(format_str, arguments, arg_index)
            result.append(formatted)

            # If no arguments were consumed or all arguments are consumed, stop
            if arg_index == start_arg_index or arg_index >= len(arguments):
                break

        return "".join(result)

    def _format_once(self, format_str: str, arguments: list[str], arg_index: int) -> tuple[str, int]:
        """Format the string once, returning formatted string and new arg index."""
        result = []
        i = 0

        while i < len(format_str):
            if format_str[i] == "\\" and i + 1 < len(format_str):
                # Handle escape sequences
                escape_result, consumed = self._process_escape(format_str, i)
                result.append(escape_result)
                i += consumed
            elif format_str[i] == "%" and i + 1 < len(format_str):
                # Handle format specifiers
                if format_str[i + 1] == "%":
                    result.append("%")
                    i += 2
                    continue

                # Parse format specifier with full support
                # Pattern: %[flags][width][.precision]specifier
                # Flags: -, +, space, #, 0
                # Width: number or *
                # Precision: .number or .*
                spec_pattern = r"([-+# 0]*)(\*|\d+)?(?:\.(\*|\d*))?([diouxXeEfFgGsbcq])"
                spec_match = re.match(spec_pattern, format_str[i + 1:])

                if spec_match:
                    flags = spec_match.group(1) or ""
                    width_spec = spec_match.group(2)
                    precision_spec = spec_match.group(3)
                    spec_type = spec_match.group(4)

                    # Handle * for width
                    width = None
                    if width_spec == "*":
                        if arg_index < len(arguments):
                            try:
                                width = int(arguments[arg_index])
                            except ValueError:
                                width = 0
                            arg_index += 1
                        else:
                            width = 0
                    elif width_spec:
                        width = int(width_spec)

                    # Handle * for precision
                    precision = None
                    if precision_spec == "*":
                        if arg_index < len(arguments):
                            try:
                                precision = int(arguments[arg_index])
                            except ValueError:
                                precision = 0
                            arg_index += 1
                        else:
                            precision = 0
                    elif precision_spec is not None:
                        precision = int(precision_spec) if precision_spec else 0

                    # Get argument
                    if arg_index < len(arguments):
                        arg = arguments[arg_index]
                        arg_index += 1
                    else:
                        arg = ""

                    # Format based on type
                    formatted = self._format_specifier(spec_type, arg, flags, width, precision)
                    result.append(formatted)

                    i += 1 + len(spec_match.group(0))
                else:
                    result.append(format_str[i])
                    i += 1
            else:
                result.append(format_str[i])
                i += 1

        return "".join(result), arg_index

    def _format_specifier(self, spec_type: str, arg: str, flags: str, width: int | None, precision: int | None) -> str:
        """Format a single specifier."""
        try:
            if spec_type == "q":
                # Shell quoting
                return self._shell_quote(arg)
            elif spec_type in "diouxX":
                val = self._parse_numeric_arg(arg)
                fmt = self._build_format_string(spec_type, flags, width, precision)
                return fmt % val
            elif spec_type in "eEfFgG":
                val = float(arg) if arg else 0.0
                fmt = self._build_format_string(spec_type, flags, width, precision)
                return fmt % val
            elif spec_type == "s":
                fmt = self._build_format_string(spec_type, flags, width, precision)
                return fmt % arg
            elif spec_type == "c":
                return arg[0] if arg else ""
            elif spec_type == "b":
                # %b is like %s but interprets escapes
                processed = self._process_escapes(arg)
                if width is not None:
                    if "-" in flags:
                        return processed.ljust(width)
                    else:
                        return processed.rjust(width)
                return processed
            else:
                return ""
        except (ValueError, TypeError):
            if spec_type in "diouxXeEfFgG":
                return "0"
            return ""

    def _parse_numeric_arg(self, arg: str) -> int:
        """Parse a numeric argument, handling hex, octal, and character notation."""
        if not arg:
            return 0
        # Character notation: 'c or "c
        if len(arg) >= 2 and arg[0] in ("'", '"'):
            return ord(arg[1])
        # Handle sign
        s = arg.strip()
        sign = 1
        if s.startswith("-"):
            sign = -1
            s = s[1:]
        elif s.startswith("+"):
            s = s[1:]
        try:
            # Hex: 0x or 0X
            if s.startswith("0x") or s.startswith("0X"):
                return sign * int(s, 16)
            # Octal: leading 0 followed by digits
            if len(s) > 1 and s[0] == "0" and all(c in "01234567" for c in s[1:]):
                return sign * int(s, 8)
            return sign * int(s)
        except ValueError:
            return 0

    def _build_format_string(self, spec_type: str, flags: str, width: int | None, precision: int | None) -> str:
        """Build a Python format string from components."""
        fmt = "%"
        fmt += flags
        if width is not None:
            fmt += str(abs(width))
            if width < 0:
                # Negative width means left-justify
                fmt = "%-" + fmt[1:]
        if precision is not None:
            fmt += f".{precision}"
        fmt += spec_type
        return fmt

    def _shell_quote(self, s: str) -> str:
        """Quote a string for shell use."""
        if not s:
            return "''"

        # Check if quoting is needed
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
        if all(c in safe_chars for c in s):
            return s

        # Use $'...' format for strings with special chars
        result = ["$'"]
        for c in s:
            if c == "'":
                result.append("\\'")
            elif c == "\\":
                result.append("\\\\")
            elif c == "\n":
                result.append("\\n")
            elif c == "\t":
                result.append("\\t")
            elif c == "\r":
                result.append("\\r")
            elif ord(c) < 32 or ord(c) > 126:
                result.append(f"\\x{ord(c):02x}")
            else:
                result.append(c)
        result.append("'")
        return "".join(result)

    def _process_escape(self, s: str, i: int) -> tuple[str, int]:
        """Process an escape sequence starting at position i.

        Returns (result_string, characters_consumed).
        """
        if i + 1 >= len(s):
            return ("\\", 1)

        escape_char = s[i + 1]
        escape_map = {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            "a": "\a",
            "b": "\b",
            "f": "\f",
            "v": "\v",
            "e": "\x1b",
            "E": "\x1b",
        }

        if escape_char in escape_map:
            return (escape_map[escape_char], 2)
        elif escape_char in "01234567":
            # Octal escape: \NNN - first digit plus up to 2 more (3 total)
            octal = escape_char
            j = i + 2
            while j < len(s) and len(octal) < 3 and s[j] in "01234567":
                octal += s[j]
                j += 1
            return (chr(int(octal, 8) & 0xFF), j - i)
        elif escape_char == "x":
            # Hex escape - collect consecutive \xHH sequences and try UTF-8 decoding
            hex_bytes = []
            j = i
            while j < len(s) and s[j:j+2] == "\\x":
                hex_digits = ""
                k = j + 2
                while k < len(s) and len(hex_digits) < 2 and s[k] in "0123456789abcdefABCDEF":
                    hex_digits += s[k]
                    k += 1
                if hex_digits:
                    hex_bytes.append(int(hex_digits, 16))
                    j = k
                else:
                    break

            if hex_bytes:
                # Try UTF-8 decoding first
                byte_data = bytes(hex_bytes)
                try:
                    decoded = byte_data.decode("utf-8")
                    return (decoded, j - i)
                except UnicodeDecodeError:
                    # Fall back to Latin-1 (1:1 byte to codepoint)
                    return (byte_data.decode("latin-1"), j - i)
            else:
                return (escape_char, 2)
        elif escape_char == "u":
            # Unicode escape \uHHHH
            hex_digits = ""
            j = i + 2
            while j < len(s) and len(hex_digits) < 4 and s[j] in "0123456789abcdefABCDEF":
                hex_digits += s[j]
                j += 1
            if hex_digits:
                try:
                    return (chr(int(hex_digits, 16)), j - i)
                except ValueError:
                    return (escape_char, 2)
            return (escape_char, 2)
        elif escape_char == "U":
            # Unicode escape \UHHHHHHHH
            hex_digits = ""
            j = i + 2
            while j < len(s) and len(hex_digits) < 8 and s[j] in "0123456789abcdefABCDEF":
                hex_digits += s[j]
                j += 1
            if hex_digits:
                try:
                    return (chr(int(hex_digits, 16)), j - i)
                except ValueError:
                    return (escape_char, 2)
            return (escape_char, 2)
        else:
            return (escape_char, 2)

    def _process_escapes(self, s: str) -> str:
        """Process escape sequences in a string."""
        result = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                escaped, consumed = self._process_escape(s, i)
                result.append(escaped)
                i += consumed
            else:
                result.append(s[i])
                i += 1
        return "".join(result)
