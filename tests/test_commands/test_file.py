"""Tests for file command."""

import pytest
from just_bash import Bash


class TestFileBasic:
    """Test basic file type detection."""

    @pytest.mark.asyncio
    async def test_file_text(self):
        """Detect plain text file."""
        bash = Bash(files={"/test.txt": "Hello, world!\n"})
        result = await bash.exec("file /test.txt")
        assert result.exit_code == 0
        assert "text" in result.stdout.lower() or "ascii" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_empty(self):
        """Detect empty file."""
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("file /empty.txt")
        assert result.exit_code == 0
        assert "empty" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_script(self):
        """Detect shell script."""
        bash = Bash(files={"/script.sh": "#!/bin/bash\necho hello\n"})
        result = await bash.exec("file /script.sh")
        assert result.exit_code == 0
        assert "script" in result.stdout.lower() or "bash" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_python(self):
        """Detect Python script."""
        bash = Bash(files={"/script.py": "#!/usr/bin/env python3\nprint('hello')\n"})
        result = await bash.exec("file /script.py")
        assert result.exit_code == 0
        assert "python" in result.stdout.lower() or "script" in result.stdout.lower()


class TestFileMagic:
    """Test magic byte detection."""

    @pytest.mark.asyncio
    async def test_file_xml(self):
        """Detect XML file."""
        bash = Bash(files={"/test.xml": '<?xml version="1.0"?>\n<root></root>\n'})
        result = await bash.exec("file /test.xml")
        assert result.exit_code == 0
        assert "xml" in result.stdout.lower() or "text" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_pdf(self):
        """Detect PDF by content."""
        bash = Bash(files={"/test.pdf": "%PDF-1.4\ntest content\n"})
        result = await bash.exec("file /test.pdf")
        assert result.exit_code == 0
        assert "pdf" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_json(self):
        """Detect JSON file."""
        bash = Bash(files={"/data.json": '{"key": "value"}\n'})
        result = await bash.exec("file /data.json")
        assert result.exit_code == 0
        assert "json" in result.stdout.lower() or "text" in result.stdout.lower()


class TestFileOptions:
    """Test file command options."""

    @pytest.mark.asyncio
    async def test_file_brief(self):
        """Brief output with -b."""
        bash = Bash(files={"/test.txt": "Hello\n"})
        result = await bash.exec("file -b /test.txt")
        assert result.exit_code == 0
        # Brief mode should not include filename
        assert "/test.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_file_multiple(self):
        """Check multiple files."""
        bash = Bash(files={
            "/a.txt": "text\n",
            "/b.txt": "more text\n",
        })
        result = await bash.exec("file /a.txt /b.txt")
        assert result.exit_code == 0
        assert "/a.txt" in result.stdout
        assert "/b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_file_nonexistent(self):
        """Error on nonexistent file."""
        bash = Bash()
        result = await bash.exec("file /nonexistent")
        assert result.exit_code != 0 or "cannot open" in result.stdout.lower() or "no such" in result.stdout.lower()
