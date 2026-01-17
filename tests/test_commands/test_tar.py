"""Tests for tar command."""

import pytest
from just_bash import Bash


class TestTarBasic:
    """Test basic tar functionality."""

    @pytest.mark.asyncio
    async def test_tar_create(self):
        """Create archive with -c."""
        bash = Bash(files={
            "/dir/a.txt": "aaa\n",
            "/dir/b.txt": "bbb\n",
        })
        result = await bash.exec("tar -cf /archive.tar /dir")
        assert result.exit_code == 0
        assert await bash.fs.exists("/archive.tar")

    @pytest.mark.asyncio
    async def test_tar_list(self):
        """List archive contents with -t."""
        bash = Bash(files={
            "/dir/a.txt": "aaa\n",
            "/dir/b.txt": "bbb\n",
        })
        await bash.exec("tar -cf /archive.tar /dir")
        result = await bash.exec("tar -tf /archive.tar")
        assert result.exit_code == 0
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_tar_extract(self):
        """Extract archive with -x."""
        bash = Bash(files={"/dir/test.txt": "content\n"})
        await bash.exec("tar -cf /archive.tar /dir")
        await bash.exec("rm -rf /dir")
        result = await bash.exec("tar -xf /archive.tar")
        assert result.exit_code == 0
        assert await bash.fs.exists("/dir/test.txt")

    @pytest.mark.asyncio
    async def test_tar_verbose(self):
        """Verbose output with -v."""
        bash = Bash(files={"/dir/a.txt": "aaa\n"})
        result = await bash.exec("tar -cvf /archive.tar /dir")
        assert result.exit_code == 0
        # Should show files being added (verbose goes to stderr)
        assert "a.txt" in result.stderr or "dir" in result.stderr


class TestTarCompression:
    """Test compression options."""

    @pytest.mark.asyncio
    async def test_tar_gzip(self):
        """Create gzip archive with -z."""
        bash = Bash(files={"/dir/test.txt": "content\n"})
        result = await bash.exec("tar -czf /archive.tar.gz /dir")
        assert result.exit_code == 0
        assert await bash.fs.exists("/archive.tar.gz")

    @pytest.mark.asyncio
    async def test_tar_extract_gzip(self):
        """Extract gzip archive with -z."""
        bash = Bash(files={"/dir/test.txt": "content\n"})
        await bash.exec("tar -czf /archive.tar.gz /dir")
        await bash.exec("rm -rf /dir")
        result = await bash.exec("tar -xzf /archive.tar.gz")
        assert result.exit_code == 0


class TestTarOptions:
    """Test additional tar options."""

    @pytest.mark.asyncio
    async def test_tar_exclude(self):
        """Exclude files with --exclude."""
        bash = Bash(files={
            "/dir/keep.txt": "keep\n",
            "/dir/skip.log": "skip\n",
        })
        result = await bash.exec("tar -cf /archive.tar --exclude='*.log' /dir")
        assert result.exit_code == 0
        list_result = await bash.exec("tar -tf /archive.tar")
        assert "keep.txt" in list_result.stdout
        assert "skip.log" not in list_result.stdout

    @pytest.mark.asyncio
    async def test_tar_strip_components(self):
        """Strip path components with --strip-components."""
        bash = Bash(files={"/a/b/c/file.txt": "content\n"})
        await bash.exec("tar -cf /archive.tar /a")
        result = await bash.exec("tar -xf /archive.tar --strip-components=2 -C /out")
        # With strip=2, /a/b/c/file.txt becomes c/file.txt
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_tar_change_dir(self):
        """Change directory with -C."""
        bash = Bash(files={"/src/file.txt": "content\n"})
        await bash.exec("mkdir -p /dest")
        await bash.exec("tar -cf /archive.tar -C /src file.txt")
        result = await bash.exec("tar -tf /archive.tar")
        assert result.exit_code == 0
        # Should be file.txt, not /src/file.txt
        assert "file.txt" in result.stdout
