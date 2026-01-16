"""File command implementation - determine file type."""

from ...types import CommandContext, ExecResult


class FileCommand:
    """The file command - determine file type."""

    name = "file"

    # Magic bytes for common file types
    MAGIC_BYTES = {
        b"\x89PNG\r\n\x1a\n": "PNG image data",
        b"GIF87a": "GIF image data",
        b"GIF89a": "GIF image data",
        b"PK\x03\x04": "Zip archive data",
        b"%PDF": "PDF document",
        b"\xff\xd8\xff": "JPEG image data",
        b"RIFF": "RIFF data",
        b"\x1f\x8b": "gzip compressed data",
        b"BZ": "bzip2 compressed data",
    }

    MIME_TYPES = {
        "PNG image data": "image/png",
        "GIF image data": "image/gif",
        "JPEG image data": "image/jpeg",
        "Zip archive data": "application/zip",
        "PDF document": "application/pdf",
        "gzip compressed data": "application/gzip",
        "ASCII text": "text/plain",
        "directory": "inode/directory",
    }

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the file command."""
        mime_mode = False
        brief_mode = False
        paths: list[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ("-i", "--mime"):
                mime_mode = True
            elif arg in ("-b", "--brief"):
                brief_mode = True
            elif arg == "--help":
                return ExecResult(
                    stdout="Usage: file [OPTION...] [FILE...]\n",
                    stderr="",
                    exit_code=0,
                )
            elif arg.startswith("-"):
                pass  # Ignore unknown options
            else:
                paths.append(arg)
            i += 1

        if not paths:
            return ExecResult(
                stdout="",
                stderr="file: missing file operand\n",
                exit_code=1,
            )

        output_lines = []
        exit_code = 0

        for path in paths:
            try:
                resolved = ctx.fs.resolve_path(ctx.cwd, path)
                stat = await ctx.fs.stat(resolved)

                if stat.is_directory:
                    file_type = "directory"
                else:
                    content = await ctx.fs.read_file(resolved)
                    file_type = self._detect_type(path, content)

                if mime_mode:
                    mime = self.MIME_TYPES.get(file_type, "application/octet-stream")
                    if file_type == "ASCII text":
                        mime += "; charset=us-ascii"
                    result = mime
                else:
                    result = file_type

                if brief_mode:
                    output_lines.append(result)
                else:
                    output_lines.append(f"{path}: {result}")

            except FileNotFoundError:
                output_lines.append(f"{path}: cannot open (No such file or directory)")
                exit_code = 1
            except Exception as e:
                output_lines.append(f"{path}: cannot open ({e})")
                exit_code = 1

        return ExecResult(
            stdout="\n".join(output_lines) + "\n",
            stderr="",
            exit_code=exit_code,
        )

    def _detect_type(self, path: str, content: str) -> str:
        """Detect file type from content."""
        # Try binary detection first
        try:
            content_bytes = content.encode("latin-1")

            for magic, file_type in self.MAGIC_BYTES.items():
                if content_bytes.startswith(magic):
                    return file_type
        except Exception:
            pass

        # Check for shebang
        if content.startswith("#!"):
            first_line = content.split("\n")[0]
            if "bash" in first_line:
                return "Bash script, ASCII text executable"
            elif "python" in first_line:
                return "Python script, ASCII text executable"
            elif "node" in first_line or "javascript" in first_line:
                return "Node.js script, ASCII text executable"
            else:
                return "script, ASCII text executable"

        # Check extension
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext == "json":
            return "JSON text data"
        elif ext == "md":
            return "Markdown text"
        elif ext == "ts":
            return "TypeScript source, ASCII text"
        elif ext == "js":
            return "JavaScript source, ASCII text"

        # Check for text
        try:
            content.encode("ascii")
            if "\r\n" in content:
                return "ASCII text, with CRLF line terminators"
            return "ASCII text"
        except UnicodeEncodeError:
            return "UTF-8 Unicode text"

        return "data"
