"""Od command implementation."""

from ...types import CommandContext, ExecResult


class OdCommand:
    """The od command - dump files in various formats."""

    name = "od"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the od command."""
        format_type = "o"  # octal (default)
        address_format = "o"  # octal addresses
        suppress_address = False
        files: list[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--help":
                return ExecResult(
                    stdout="Usage: od [OPTION]... [FILE]...\nDump files in various formats.\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg == "-c":
                format_type = "c"  # character
            elif arg == "-x":
                format_type = "x"  # hexadecimal
            elif arg == "-o":
                format_type = "o"  # octal
            elif arg == "-d":
                format_type = "d"  # decimal
            elif arg == "-An":
                suppress_address = True
            elif arg == "-Ad":
                address_format = "d"
            elif arg == "-Ao":
                address_format = "o"
            elif arg == "-Ax":
                address_format = "x"
            elif arg == "--":
                files.extend(args[i + 1:])
                break
            elif arg.startswith("-") and len(arg) > 1:
                return ExecResult(
                    stdout="",
                    stderr=f"od: invalid option -- '{arg[1]}'\n",
                    exit_code=1,
                )
            else:
                files.append(arg)
            i += 1

        # Read from stdin if no files
        if not files:
            content = ctx.stdin.encode("utf-8", errors="replace")
            result = self._dump(content, format_type, address_format, suppress_address)
            return ExecResult(stdout=result, stderr="", exit_code=0)

        stdout_parts = []
        stderr = ""
        exit_code = 0

        for file in files:
            try:
                if file == "-":
                    content = ctx.stdin.encode("utf-8", errors="replace")
                else:
                    path = ctx.fs.resolve_path(ctx.cwd, file)
                    content = await ctx.fs.read_file_bytes(path)

                result = self._dump(content, format_type, address_format, suppress_address)
                stdout_parts.append(result)

            except FileNotFoundError:
                stderr += f"od: {file}: No such file or directory\n"
                exit_code = 1

        return ExecResult(stdout="".join(stdout_parts), stderr=stderr, exit_code=exit_code)

    def _dump(
        self, data: bytes, format_type: str, address_format: str, suppress_address: bool
    ) -> str:
        """Dump data in specified format."""
        result_lines = []
        bytes_per_line = 16
        offset = 0

        while offset < len(data):
            line_data = data[offset:offset + bytes_per_line]
            parts = []

            # Add address
            if not suppress_address:
                if address_format == "d":
                    parts.append(f"{offset:07d}")
                elif address_format == "x":
                    parts.append(f"{offset:07x}")
                else:
                    parts.append(f"{offset:07o}")

            # Add data
            if format_type == "c":
                # Character format
                chars = []
                for byte in line_data:
                    if byte == 0:
                        chars.append("\\0")
                    elif byte == 7:
                        chars.append("\\a")
                    elif byte == 8:
                        chars.append("\\b")
                    elif byte == 9:
                        chars.append("\\t")
                    elif byte == 10:
                        chars.append("\\n")
                    elif byte == 11:
                        chars.append("\\v")
                    elif byte == 12:
                        chars.append("\\f")
                    elif byte == 13:
                        chars.append("\\r")
                    elif 32 <= byte <= 126:
                        chars.append(f"  {chr(byte)}")
                    else:
                        chars.append(f"{byte:03o}")
                parts.append(" ".join(chars))
            elif format_type == "x":
                # Hexadecimal format
                hex_vals = [f"{byte:02x}" for byte in line_data]
                parts.append(" ".join(hex_vals))
            elif format_type == "d":
                # Decimal format
                dec_vals = [f"{byte:3d}" for byte in line_data]
                parts.append(" ".join(dec_vals))
            else:
                # Octal format (default)
                oct_vals = [f"{byte:03o}" for byte in line_data]
                parts.append(" ".join(oct_vals))

            result_lines.append(" ".join(parts))
            offset += bytes_per_line

        # Final address marker
        if not suppress_address and data:
            if address_format == "d":
                result_lines.append(f"{len(data):07d}")
            elif address_format == "x":
                result_lines.append(f"{len(data):07x}")
            else:
                result_lines.append(f"{len(data):07o}")

        if result_lines:
            return "\n".join(result_lines) + "\n"
        return ""
