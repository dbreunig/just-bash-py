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
                stderr="printf: usage: printf format [arguments]\n",
                exit_code=2,
            )

        format_str = args[0]
        arguments = args[1:]

        try:
            output = self._format(format_str, arguments)
            return ExecResult(stdout=output, stderr="", exit_code=0)
        except ValueError as e:
            return ExecResult(stdout="", stderr=f"printf: {e}\n", exit_code=1)

    def _format(self, format_str: str, arguments: list[str]) -> str:
        """Format the string with arguments."""
        result = []
        arg_index = 0
        i = 0

        while i < len(format_str):
            if format_str[i] == "\\" and i + 1 < len(format_str):
                # Handle escape sequences
                escape_char = format_str[i + 1]
                if escape_char == "n":
                    result.append("\n")
                elif escape_char == "t":
                    result.append("\t")
                elif escape_char == "r":
                    result.append("\r")
                elif escape_char == "\\":
                    result.append("\\")
                elif escape_char == "a":
                    result.append("\a")
                elif escape_char == "b":
                    result.append("\b")
                elif escape_char == "f":
                    result.append("\f")
                elif escape_char == "v":
                    result.append("\v")
                elif escape_char == "e" or escape_char == "E":
                    result.append("\x1b")
                elif escape_char == "0":
                    # Octal escape
                    octal = ""
                    j = i + 2
                    while j < len(format_str) and len(octal) < 3 and format_str[j] in "01234567":
                        octal += format_str[j]
                        j += 1
                    if octal:
                        result.append(chr(int(octal, 8)))
                        i = j
                        continue
                    else:
                        result.append("\0")
                elif escape_char == "x":
                    # Hex escape
                    hex_digits = ""
                    j = i + 2
                    while j < len(format_str) and len(hex_digits) < 2 and format_str[j] in "0123456789abcdefABCDEF":
                        hex_digits += format_str[j]
                        j += 1
                    if hex_digits:
                        result.append(chr(int(hex_digits, 16)))
                        i = j
                        continue
                    else:
                        result.append(escape_char)
                else:
                    result.append(escape_char)
                i += 2
            elif format_str[i] == "%" and i + 1 < len(format_str):
                # Handle format specifiers
                if format_str[i + 1] == "%":
                    result.append("%")
                    i += 2
                    continue

                # Parse format specifier
                spec_match = re.match(r"-?(\d+)?(\.\d+)?([diouxXeEfFgGsbc])", format_str[i + 1:])
                if spec_match:
                    spec = spec_match.group(0)
                    full_spec = "%" + spec
                    spec_type = spec_match.group(3)

                    # Get argument
                    if arg_index < len(arguments):
                        arg = arguments[arg_index]
                        arg_index += 1
                    else:
                        arg = ""

                    # Format based on type
                    try:
                        if spec_type in "diouxX":
                            val = int(arg) if arg else 0
                            result.append(full_spec % val)
                        elif spec_type in "eEfFgG":
                            val = float(arg) if arg else 0.0
                            result.append(full_spec % val)
                        elif spec_type == "s":
                            result.append(full_spec % arg)
                        elif spec_type == "c":
                            result.append(arg[0] if arg else "")
                        elif spec_type == "b":
                            # %b is like %s but interprets escapes
                            result.append(self._process_escapes(arg))
                    except (ValueError, TypeError):
                        result.append(full_spec % 0 if spec_type in "diouxXeEfFgG" else "")

                    i += 1 + len(spec)
                else:
                    result.append(format_str[i])
                    i += 1
            else:
                result.append(format_str[i])
                i += 1

        return "".join(result)

    def _process_escapes(self, s: str) -> str:
        """Process escape sequences in a string."""
        result = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                c = s[i + 1]
                if c == "n":
                    result.append("\n")
                elif c == "t":
                    result.append("\t")
                elif c == "r":
                    result.append("\r")
                elif c == "\\":
                    result.append("\\")
                else:
                    result.append(c)
                i += 2
            else:
                result.append(s[i])
                i += 1
        return "".join(result)
