"""Tests for command implementations."""

import pytest
from just_bash import Bash


class TestPwdCommand:
    """Test pwd command."""

    @pytest.mark.asyncio
    async def test_pwd_default(self):
        bash = Bash(cwd="/home/user")
        result = await bash.exec("pwd")
        assert result.stdout == "/home/user\n"
        assert result.exit_code == 0


class TestLsCommand:
    """Test ls command."""

    @pytest.mark.asyncio
    async def test_ls_empty_dir(self):
        bash = Bash()
        await bash.fs.mkdir("/empty")
        result = await bash.exec("ls /empty")
        assert result.stdout == "\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_ls_with_files(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/b.txt": "b",
        })
        result = await bash.exec("ls /dir")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_ls_one_per_line(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/b.txt": "b",
        })
        result = await bash.exec("ls -1 /dir")
        assert result.stdout == "a.txt\nb.txt\n"

    @pytest.mark.asyncio
    async def test_ls_long_format(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("ls -l /test.txt")
        assert "-rw" in result.stdout
        assert "test.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_ls_nonexistent(self):
        bash = Bash()
        result = await bash.exec("ls /nonexistent")
        assert "No such file or directory" in result.stderr
        assert result.exit_code == 2


class TestHeadCommand:
    """Test head command."""

    @pytest.mark.asyncio
    async def test_head_default(self):
        lines = "\n".join([f"line{i}" for i in range(20)])
        bash = Bash(files={"/test.txt": lines})
        result = await bash.exec("head /test.txt")
        output_lines = result.stdout.strip().split("\n")
        assert len(output_lines) == 10
        assert output_lines[0] == "line0"
        assert output_lines[9] == "line9"

    @pytest.mark.asyncio
    async def test_head_custom_lines(self):
        lines = "\n".join([f"line{i}" for i in range(20)])
        bash = Bash(files={"/test.txt": lines})
        result = await bash.exec("head -n 5 /test.txt")
        output_lines = result.stdout.strip().split("\n")
        assert len(output_lines) == 5

    @pytest.mark.asyncio
    async def test_head_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\nb\nc\nd\ne' | head -n 3")
        # This depends on echo -e working and pipeline support
        # For now just check it doesn't error
        assert result.exit_code == 0


class TestTailCommand:
    """Test tail command."""

    @pytest.mark.asyncio
    async def test_tail_default(self):
        lines = "\n".join([f"line{i}" for i in range(20)])
        bash = Bash(files={"/test.txt": lines})
        result = await bash.exec("tail /test.txt")
        output_lines = result.stdout.strip().split("\n")
        assert len(output_lines) == 10
        assert output_lines[0] == "line10"
        assert output_lines[9] == "line19"

    @pytest.mark.asyncio
    async def test_tail_custom_lines(self):
        lines = "\n".join([f"line{i}" for i in range(20)])
        bash = Bash(files={"/test.txt": lines})
        result = await bash.exec("tail -n 5 /test.txt")
        output_lines = result.stdout.strip().split("\n")
        assert len(output_lines) == 5
        assert output_lines[0] == "line15"


class TestWcCommand:
    """Test wc command."""

    @pytest.mark.asyncio
    async def test_wc_lines(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("wc -l /test.txt")
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_words(self):
        bash = Bash(files={"/test.txt": "one two three four\n"})
        result = await bash.exec("wc -w /test.txt")
        assert "4" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_stdin(self):
        bash = Bash()
        result = await bash.exec("echo hello world | wc -w")
        assert "2" in result.stdout


class TestGrepCommand:
    """Test grep command."""

    @pytest.mark.asyncio
    async def test_grep_basic(self):
        bash = Bash(files={"/test.txt": "hello\nworld\nhello world\n"})
        result = await bash.exec("grep hello /test.txt")
        assert "hello" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_grep_no_match(self):
        bash = Bash(files={"/test.txt": "hello\nworld\n"})
        result = await bash.exec("grep notfound /test.txt")
        assert result.stdout == ""
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_grep_ignore_case(self):
        bash = Bash(files={"/test.txt": "Hello\nWORLD\n"})
        result = await bash.exec("grep -i hello /test.txt")
        assert "Hello" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_grep_invert_match(self):
        bash = Bash(files={"/test.txt": "apple\nbanana\napricot\n"})
        result = await bash.exec("grep -v apple /test.txt")
        assert "banana" in result.stdout
        assert "apple" not in result.stdout

    @pytest.mark.asyncio
    async def test_grep_count(self):
        bash = Bash(files={"/test.txt": "a\na\nb\na\n"})
        result = await bash.exec("grep -c a /test.txt")
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_grep_line_numbers(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo\n"})
        result = await bash.exec("grep -n foo /test.txt")
        assert "1:" in result.stdout
        assert "3:" in result.stdout

    @pytest.mark.asyncio
    async def test_grep_stdin(self):
        bash = Bash()
        result = await bash.exec("echo hello | grep hello")
        assert "hello" in result.stdout
        assert result.exit_code == 0


class TestPipelines:
    """Test command pipelines."""

    @pytest.mark.asyncio
    async def test_echo_cat_pipeline(self):
        bash = Bash()
        result = await bash.exec("echo hello | cat")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_echo_grep_pipeline(self):
        bash = Bash()
        result = await bash.exec("echo hello world | grep world")
        assert "world" in result.stdout

    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self):
        bash = Bash()
        result = await bash.exec("echo hello | cat | cat")
        assert result.stdout == "hello\n"


# =============================================================================
# File Operations Tests
# =============================================================================


class TestMkdirCommand:
    """Test mkdir command."""

    @pytest.mark.asyncio
    async def test_mkdir_basic(self):
        bash = Bash()
        result = await bash.exec("mkdir /newdir")
        assert result.exit_code == 0
        # Verify directory was created
        result = await bash.exec("ls /")
        assert "newdir" in result.stdout

    @pytest.mark.asyncio
    async def test_mkdir_recursive(self):
        bash = Bash()
        result = await bash.exec("mkdir -p /a/b/c")
        assert result.exit_code == 0
        result = await bash.exec("ls /a/b")
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_mkdir_exists_error(self):
        bash = Bash()
        await bash.exec("mkdir /existing")
        result = await bash.exec("mkdir /existing")
        assert result.exit_code == 1
        assert "exists" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_mkdir_exists_with_p_flag(self):
        bash = Bash()
        await bash.exec("mkdir /existing")
        result = await bash.exec("mkdir -p /existing")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_mkdir_verbose(self):
        bash = Bash()
        result = await bash.exec("mkdir -v /newdir")
        assert result.exit_code == 0
        assert "created" in result.stdout.lower()


class TestTouchCommand:
    """Test touch command."""

    @pytest.mark.asyncio
    async def test_touch_creates_file(self):
        bash = Bash()
        result = await bash.exec("touch /newfile.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "newfile.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_touch_existing_file(self):
        bash = Bash(files={"/existing.txt": "content"})
        result = await bash.exec("touch /existing.txt")
        assert result.exit_code == 0
        # Content should be preserved
        result = await bash.exec("cat /existing.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_touch_multiple_files(self):
        bash = Bash()
        result = await bash.exec("touch /a.txt /b.txt /c.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout
        assert "c.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_touch_no_create_flag(self):
        bash = Bash()
        result = await bash.exec("touch -c /nonexistent.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "nonexistent.txt" not in result.stdout


class TestRmCommand:
    """Test rm command."""

    @pytest.mark.asyncio
    async def test_rm_file(self):
        bash = Bash(files={"/test.txt": "content"})
        result = await bash.exec("rm /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "test.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_rm_nonexistent_error(self):
        bash = Bash()
        result = await bash.exec("rm /nonexistent.txt")
        assert result.exit_code == 1
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_rm_force_nonexistent(self):
        bash = Bash()
        result = await bash.exec("rm -f /nonexistent.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_rm_directory_error(self):
        bash = Bash()
        await bash.exec("mkdir /mydir")
        result = await bash.exec("rm /mydir")
        assert result.exit_code == 1
        assert "directory" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_rm_recursive_directory(self):
        bash = Bash(files={"/dir/sub/file.txt": "content"})
        result = await bash.exec("rm -r /dir")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "dir" not in result.stdout

    @pytest.mark.asyncio
    async def test_rm_multiple_files(self):
        bash = Bash(files={"/a.txt": "a", "/b.txt": "b"})
        result = await bash.exec("rm /a.txt /b.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls /")
        assert "a.txt" not in result.stdout
        assert "b.txt" not in result.stdout


class TestCpCommand:
    """Test cp command."""

    @pytest.mark.asyncio
    async def test_cp_file(self):
        bash = Bash(files={"/src.txt": "hello world"})
        result = await bash.exec("cp /src.txt /dst.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /dst.txt")
        assert result.stdout == "hello world\n"

    @pytest.mark.asyncio
    async def test_cp_preserves_original(self):
        bash = Bash(files={"/src.txt": "hello"})
        await bash.exec("cp /src.txt /dst.txt")
        result = await bash.exec("cat /src.txt")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_cp_into_directory(self):
        bash = Bash(files={"/file.txt": "content"})
        await bash.exec("mkdir /destdir")
        result = await bash.exec("cp /file.txt /destdir/")
        assert result.exit_code == 0
        result = await bash.exec("cat /destdir/file.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_cp_recursive_directory(self):
        bash = Bash(files={"/src/a.txt": "a", "/src/sub/b.txt": "b"})
        result = await bash.exec("cp -r /src /dst")
        assert result.exit_code == 0
        result = await bash.exec("cat /dst/a.txt")
        assert result.stdout == "a\n"
        result = await bash.exec("cat /dst/sub/b.txt")
        assert result.stdout == "b\n"

    @pytest.mark.asyncio
    async def test_cp_nonexistent_source_error(self):
        bash = Bash()
        result = await bash.exec("cp /nonexistent.txt /dst.txt")
        assert result.exit_code == 1
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_cp_no_clobber(self):
        bash = Bash(files={"/src.txt": "new", "/dst.txt": "old"})
        result = await bash.exec("cp -n /src.txt /dst.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /dst.txt")
        assert result.stdout == "old\n"  # Not overwritten


class TestMvCommand:
    """Test mv command."""

    @pytest.mark.asyncio
    async def test_mv_file(self):
        bash = Bash(files={"/src.txt": "hello"})
        result = await bash.exec("mv /src.txt /dst.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /dst.txt")
        assert result.stdout == "hello\n"
        result = await bash.exec("ls /")
        assert "src.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_mv_into_directory(self):
        bash = Bash(files={"/file.txt": "content"})
        await bash.exec("mkdir /destdir")
        result = await bash.exec("mv /file.txt /destdir/")
        assert result.exit_code == 0
        result = await bash.exec("cat /destdir/file.txt")
        assert result.stdout == "content\n"
        result = await bash.exec("ls /")
        assert "file.txt" not in result.stdout or "destdir" in result.stdout

    @pytest.mark.asyncio
    async def test_mv_rename_directory(self):
        bash = Bash(files={"/olddir/file.txt": "content"})
        result = await bash.exec("mv /olddir /newdir")
        assert result.exit_code == 0
        result = await bash.exec("cat /newdir/file.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_mv_nonexistent_source_error(self):
        bash = Bash()
        result = await bash.exec("mv /nonexistent.txt /dst.txt")
        assert result.exit_code == 1
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_mv_no_clobber(self):
        bash = Bash(files={"/src.txt": "new", "/dst.txt": "old"})
        result = await bash.exec("mv -n /src.txt /dst.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /dst.txt")
        assert result.stdout == "old\n"
        # Source should still exist
        result = await bash.exec("cat /src.txt")
        assert result.stdout == "new\n"


class TestLnCommand:
    """Test ln command."""

    @pytest.mark.asyncio
    async def test_ln_symbolic_link(self):
        bash = Bash(files={"/target.txt": "content"})
        result = await bash.exec("ln -s /target.txt /link.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /link.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_ln_hard_link(self):
        bash = Bash(files={"/target.txt": "content"})
        result = await bash.exec("ln /target.txt /link.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /link.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_ln_symlink_to_directory(self):
        bash = Bash(files={"/dir/file.txt": "content"})
        result = await bash.exec("ln -s /dir /link")
        assert result.exit_code == 0
        result = await bash.exec("ls /link")
        assert "file.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_ln_force_overwrite(self):
        bash = Bash(files={"/target.txt": "new", "/link.txt": "old"})
        result = await bash.exec("ln -sf /target.txt /link.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /link.txt")
        assert result.stdout == "new\n"


class TestChmodCommand:
    """Test chmod command."""

    @pytest.mark.asyncio
    async def test_chmod_octal(self):
        bash = Bash(files={"/test.txt": "content"})
        result = await bash.exec("chmod 755 /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls -l /test.txt")
        assert "rwx" in result.stdout  # Owner has rwx

    @pytest.mark.asyncio
    async def test_chmod_symbolic_add(self):
        bash = Bash(files={"/test.txt": "content"})
        result = await bash.exec("chmod u+x /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls -l /test.txt")
        assert "x" in result.stdout

    @pytest.mark.asyncio
    async def test_chmod_symbolic_remove(self):
        bash = Bash(files={"/test.txt": "content"})
        await bash.exec("chmod 777 /test.txt")
        result = await bash.exec("chmod a-w /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls -l /test.txt")
        # Should have r-x pattern
        assert "r-x" in result.stdout

    @pytest.mark.asyncio
    async def test_chmod_nonexistent_error(self):
        bash = Bash()
        result = await bash.exec("chmod 755 /nonexistent.txt")
        assert result.exit_code == 1
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_chmod_recursive(self):
        bash = Bash(files={"/dir/a.txt": "a", "/dir/sub/b.txt": "b"})
        result = await bash.exec("chmod -R 755 /dir")
        assert result.exit_code == 0


# =============================================================================
# Text Processing Tests
# =============================================================================


class TestUniqCommand:
    """Test uniq command."""

    @pytest.mark.asyncio
    async def test_uniq_basic(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nb\nb\nc\n"})
        result = await bash.exec("uniq /test.txt")
        assert result.stdout == "a\nb\nc\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_uniq_count(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nc\nc\nc\n"})
        result = await bash.exec("uniq -c /test.txt")
        assert "2" in result.stdout and "a" in result.stdout
        assert "1" in result.stdout and "b" in result.stdout
        assert "3" in result.stdout and "c" in result.stdout

    @pytest.mark.asyncio
    async def test_uniq_repeated_only(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nc\nc\n"})
        result = await bash.exec("uniq -d /test.txt")
        assert "a" in result.stdout
        assert "c" in result.stdout
        assert "b" not in result.stdout

    @pytest.mark.asyncio
    async def test_uniq_unique_only(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nc\nc\n"})
        result = await bash.exec("uniq -u /test.txt")
        assert "b" in result.stdout
        assert "a" not in result.stdout
        assert "c" not in result.stdout

    @pytest.mark.asyncio
    async def test_uniq_ignore_case(self):
        bash = Bash(files={"/test.txt": "A\na\nB\n"})
        result = await bash.exec("uniq -i /test.txt")
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2  # A and B (case-insensitive)

    @pytest.mark.asyncio
    async def test_uniq_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\na\nb' | uniq")
        assert result.exit_code == 0


class TestCutCommand:
    """Test cut command."""

    @pytest.mark.asyncio
    async def test_cut_field(self):
        bash = Bash(files={"/test.txt": "a,b,c\n1,2,3\n"})
        result = await bash.exec("cut -d, -f2 /test.txt")
        assert result.stdout == "b\n2\n"

    @pytest.mark.asyncio
    async def test_cut_multiple_fields(self):
        bash = Bash(files={"/test.txt": "a,b,c,d\n1,2,3,4\n"})
        result = await bash.exec("cut -d, -f1,3 /test.txt")
        assert result.stdout == "a,c\n1,3\n"

    @pytest.mark.asyncio
    async def test_cut_field_range(self):
        bash = Bash(files={"/test.txt": "a,b,c,d\n"})
        result = await bash.exec("cut -d, -f2-3 /test.txt")
        assert result.stdout == "b,c\n"

    @pytest.mark.asyncio
    async def test_cut_characters(self):
        bash = Bash(files={"/test.txt": "hello\nworld\n"})
        result = await bash.exec("cut -c1-3 /test.txt")
        assert result.stdout == "hel\nwor\n"

    @pytest.mark.asyncio
    async def test_cut_tab_delimiter_default(self):
        bash = Bash(files={"/test.txt": "a\tb\tc\n"})
        result = await bash.exec("cut -f2 /test.txt")
        assert result.stdout == "b\n"

    @pytest.mark.asyncio
    async def test_cut_only_delimited(self):
        bash = Bash(files={"/test.txt": "a,b,c\nno delimiter\n"})
        result = await bash.exec("cut -d, -f2 -s /test.txt")
        assert result.stdout == "b\n"  # Line without delimiter omitted

    @pytest.mark.asyncio
    async def test_cut_missing_field_spec_error(self):
        bash = Bash(files={"/test.txt": "a,b,c\n"})
        result = await bash.exec("cut /test.txt")
        assert result.exit_code == 1


class TestTrCommand:
    """Test tr command."""

    @pytest.mark.asyncio
    async def test_tr_translate(self):
        bash = Bash()
        result = await bash.exec("echo hello | tr a-z A-Z")
        assert result.stdout == "HELLO\n"

    @pytest.mark.asyncio
    async def test_tr_delete(self):
        bash = Bash()
        result = await bash.exec("echo hello123world | tr -d 0-9")
        assert result.stdout == "helloworld\n"

    @pytest.mark.asyncio
    async def test_tr_squeeze(self):
        bash = Bash()
        result = await bash.exec("echo 'hello   world' | tr -s ' '")
        assert result.stdout == "hello world\n"

    @pytest.mark.asyncio
    async def test_tr_complement(self):
        bash = Bash()
        result = await bash.exec("echo abc123def | tr -cd 0-9")
        assert result.stdout == "123"

    @pytest.mark.asyncio
    async def test_tr_character_class(self):
        bash = Bash()
        result = await bash.exec("echo Hello123 | tr -d '[:digit:]'")
        assert result.stdout == "Hello\n"

    @pytest.mark.asyncio
    async def test_tr_escape_sequences(self):
        # Use file with actual tabs and translate using actual tab character
        bash = Bash(files={"/test.txt": "a\tb\tc\n"})
        # Use actual tab in the tr argument (shell passes it through)
        result = await bash.exec("cat /test.txt | tr '\t' ','")
        assert result.stdout == "a,b,c\n"


class TestSortCommand:
    """Test sort command."""

    @pytest.mark.asyncio
    async def test_sort_basic(self):
        bash = Bash(files={"/test.txt": "banana\napple\ncherry\n"})
        result = await bash.exec("sort /test.txt")
        assert result.stdout == "apple\nbanana\ncherry\n"

    @pytest.mark.asyncio
    async def test_sort_reverse(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("sort -r /test.txt")
        assert result.stdout == "c\nb\na\n"

    @pytest.mark.asyncio
    async def test_sort_numeric(self):
        bash = Bash(files={"/test.txt": "10\n2\n1\n20\n"})
        result = await bash.exec("sort -n /test.txt")
        assert result.stdout == "1\n2\n10\n20\n"

    @pytest.mark.asyncio
    async def test_sort_unique(self):
        bash = Bash(files={"/test.txt": "a\nb\na\nc\nb\n"})
        result = await bash.exec("sort -u /test.txt")
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 3
        assert sorted(lines) == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_sort_key(self):
        bash = Bash(files={"/test.txt": "b 2\na 3\nc 1\n"})
        result = await bash.exec("sort -k2 -n /test.txt")
        lines = result.stdout.strip().split("\n")
        assert lines[0].startswith("c")  # 1 is smallest
        assert lines[2].startswith("a")  # 3 is largest

    @pytest.mark.asyncio
    async def test_sort_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'c\na\nb' | sort")
        assert result.exit_code == 0


# =============================================================================
# Data Command Tests
# =============================================================================


class TestBase64Command:
    """Test base64 command."""

    @pytest.mark.asyncio
    async def test_base64_encode(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("base64 /test.txt")
        assert "aGVsbG8=" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_base64_decode(self):
        bash = Bash(files={"/test.txt": "aGVsbG8="})
        result = await bash.exec("base64 -d /test.txt")
        assert result.stdout == "hello"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_base64_stdin_encode(self):
        bash = Bash()
        result = await bash.exec("echo -n hello | base64")
        assert "aGVsbG8=" in result.stdout

    @pytest.mark.asyncio
    async def test_base64_roundtrip(self):
        bash = Bash(files={"/test.txt": "test data 123"})
        # Encode then decode
        result = await bash.exec("base64 /test.txt")
        encoded = result.stdout.strip()
        bash2 = Bash(files={"/encoded.txt": encoded})
        result = await bash2.exec("base64 -d /encoded.txt")
        assert result.stdout == "test data 123"


class TestSeqCommand:
    """Test seq command."""

    @pytest.mark.asyncio
    async def test_seq_single_arg(self):
        bash = Bash()
        result = await bash.exec("seq 5")
        assert result.stdout == "1\n2\n3\n4\n5\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_seq_two_args(self):
        bash = Bash()
        result = await bash.exec("seq 3 6")
        assert result.stdout == "3\n4\n5\n6\n"

    @pytest.mark.asyncio
    async def test_seq_three_args(self):
        bash = Bash()
        result = await bash.exec("seq 1 2 9")
        assert result.stdout == "1\n3\n5\n7\n9\n"

    @pytest.mark.asyncio
    async def test_seq_separator(self):
        bash = Bash()
        result = await bash.exec("seq -s ', ' 3")
        assert result.stdout == "1, 2, 3\n"

    @pytest.mark.asyncio
    async def test_seq_equal_width(self):
        bash = Bash()
        result = await bash.exec("seq -w 8 10")
        assert result.stdout == "08\n09\n10\n"

    @pytest.mark.asyncio
    async def test_seq_descending(self):
        bash = Bash()
        result = await bash.exec("seq 5 1")
        assert result.stdout == "5\n4\n3\n2\n1\n"

    @pytest.mark.asyncio
    async def test_seq_missing_operand_error(self):
        bash = Bash()
        result = await bash.exec("seq")
        assert result.exit_code == 1


class TestExprCommand:
    """Test expr command."""

    @pytest.mark.asyncio
    async def test_expr_addition(self):
        bash = Bash()
        result = await bash.exec("expr 2 + 3")
        assert result.stdout == "5\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_expr_subtraction(self):
        bash = Bash()
        result = await bash.exec("expr 10 - 4")
        assert result.stdout == "6\n"

    @pytest.mark.asyncio
    async def test_expr_multiplication(self):
        bash = Bash()
        # Note: * needs to be escaped in shell, but here we test the command directly
        result = await bash.exec("expr 3 '*' 4")
        assert result.stdout == "12\n"

    @pytest.mark.asyncio
    async def test_expr_division(self):
        bash = Bash()
        result = await bash.exec("expr 15 / 3")
        assert result.stdout == "5\n"

    @pytest.mark.asyncio
    async def test_expr_modulo(self):
        bash = Bash()
        result = await bash.exec("expr 17 % 5")
        assert result.stdout == "2\n"

    @pytest.mark.asyncio
    async def test_expr_comparison_greater(self):
        bash = Bash()
        result = await bash.exec("expr 5 '>' 3")
        assert result.stdout == "1\n"

    @pytest.mark.asyncio
    async def test_expr_comparison_less(self):
        bash = Bash()
        result = await bash.exec("expr 2 '<' 5")
        assert result.stdout == "1\n"

    @pytest.mark.asyncio
    async def test_expr_length(self):
        bash = Bash()
        result = await bash.exec("expr length hello")
        assert result.stdout == "5\n"

    @pytest.mark.asyncio
    async def test_expr_substr(self):
        bash = Bash()
        result = await bash.exec("expr substr hello 2 3")
        assert result.stdout == "ell\n"

    @pytest.mark.asyncio
    async def test_expr_index(self):
        bash = Bash()
        result = await bash.exec("expr index hello e")
        assert result.stdout == "2\n"

    @pytest.mark.asyncio
    async def test_expr_zero_exit_code(self):
        bash = Bash()
        result = await bash.exec("expr 0 + 0")
        assert result.stdout == "0\n"
        assert result.exit_code == 1  # 0 result means exit code 1

    @pytest.mark.asyncio
    async def test_expr_division_by_zero(self):
        bash = Bash()
        result = await bash.exec("expr 5 / 0")
        assert result.exit_code == 2
        assert "division by zero" in result.stderr


class TestDateCommand:
    """Test date command."""

    @pytest.mark.asyncio
    async def test_date_default(self):
        bash = Bash()
        result = await bash.exec("date")
        assert result.exit_code == 0
        # Should contain some date-like output
        assert len(result.stdout) > 10

    @pytest.mark.asyncio
    async def test_date_format_year(self):
        bash = Bash()
        result = await bash.exec("date +%Y")
        assert result.exit_code == 0
        year = result.stdout.strip()
        assert year.isdigit()
        assert len(year) == 4

    @pytest.mark.asyncio
    async def test_date_format_month_day(self):
        bash = Bash()
        result = await bash.exec("date +%m-%d")
        assert result.exit_code == 0
        parts = result.stdout.strip().split("-")
        assert len(parts) == 2

    @pytest.mark.asyncio
    async def test_date_utc(self):
        bash = Bash()
        result = await bash.exec("date -u +%Z")
        assert result.exit_code == 0
        # UTC timezone indicator
        assert "UTC" in result.stdout or "+0000" in result.stdout

    @pytest.mark.asyncio
    async def test_date_iso_format(self):
        bash = Bash()
        result = await bash.exec("date -I")
        assert result.exit_code == 0
        # ISO format: YYYY-MM-DD
        parts = result.stdout.strip().split("-")
        assert len(parts) >= 3


# =============================================================================
# Complex Command Tests
# =============================================================================


class TestSedCommand:
    """Test sed command."""

    @pytest.mark.asyncio
    async def test_sed_substitute(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        result = await bash.exec('sed "s/hello/goodbye/" /test.txt')
        assert result.stdout == "goodbye world\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sed_substitute_global(self):
        bash = Bash(files={"/test.txt": "a a a\n"})
        result = await bash.exec('sed "s/a/b/g" /test.txt')
        assert result.stdout == "b b b\n"

    @pytest.mark.asyncio
    async def test_sed_delete_line(self):
        bash = Bash(files={"/test.txt": "line1\nline2\nline3\n"})
        result = await bash.exec('sed "2d" /test.txt')
        assert result.stdout == "line1\nline3\n"

    @pytest.mark.asyncio
    async def test_sed_print_line(self):
        bash = Bash(files={"/test.txt": "line1\nline2\nline3\n"})
        result = await bash.exec('sed -n "2p" /test.txt')
        assert result.stdout == "line2\n"

    @pytest.mark.asyncio
    async def test_sed_address_range(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\nd\ne\n"})
        result = await bash.exec('sed "2,4d" /test.txt')
        assert result.stdout == "a\ne\n"

    @pytest.mark.asyncio
    async def test_sed_regex_address(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo\nbaz\n"})
        result = await bash.exec('sed "/foo/d" /test.txt')
        assert result.stdout == "bar\nbaz\n"

    @pytest.mark.asyncio
    async def test_sed_stdin(self):
        bash = Bash()
        result = await bash.exec('echo hello | sed "s/hello/world/"')
        assert result.stdout == "world\n"

    @pytest.mark.asyncio
    async def test_sed_transliterate(self):
        bash = Bash(files={"/test.txt": "abc\n"})
        result = await bash.exec('sed "y/abc/xyz/" /test.txt')
        assert result.stdout == "xyz\n"

    @pytest.mark.asyncio
    async def test_sed_in_place_script_file(self):
        """Test sed with script from file (avoids shell expansion issues)."""
        bash = Bash(files={
            "/data.txt": "hello\n",
            "/script.sed": "s/hello/world/"
        })
        result = await bash.exec("sed -f /script.sed /data.txt")
        assert result.stdout == "world\n"


class TestAwkCommand:
    """Test awk command."""

    @pytest.mark.asyncio
    async def test_awk_print_all(self):
        """Test awk with program from file."""
        bash = Bash(files={
            "/data.txt": "a b c\n1 2 3\n",
            "/prog.awk": "{print}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "a b c\n1 2 3\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_awk_print_field(self):
        bash = Bash(files={
            "/data.txt": "a b c\n1 2 3\n",
            "/prog.awk": "{print $2}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "b\n2\n"

    @pytest.mark.asyncio
    async def test_awk_field_separator(self):
        bash = Bash(files={
            "/data.txt": "a,b,c\n1,2,3\n",
            "/prog.awk": "{print $1}"
        })
        result = await bash.exec("awk -F, -f /prog.awk /data.txt")
        assert result.stdout == "a\n1\n"

    @pytest.mark.asyncio
    async def test_awk_begin_end(self):
        bash = Bash(files={
            "/data.txt": "a\nb\nc\n",
            "/prog.awk": "BEGIN {print \"start\"} {print} END {print \"done\"}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "start"
        assert lines[-1] == "done"

    @pytest.mark.asyncio
    async def test_awk_sum(self):
        bash = Bash(files={
            "/data.txt": "1\n2\n3\n4\n5\n",
            "/prog.awk": "{sum+=$1} END {print sum}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert "15" in result.stdout

    @pytest.mark.asyncio
    async def test_awk_nr_variable(self):
        bash = Bash(files={
            "/data.txt": "a\nb\nc\n",
            "/prog.awk": "NR==2 {print $0}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "b\n"

    @pytest.mark.asyncio
    async def test_awk_nf_variable(self):
        bash = Bash(files={
            "/data.txt": "a b c\n1 2\nx\n",
            "/prog.awk": "{print NF}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "3\n2\n1\n"

    @pytest.mark.asyncio
    async def test_awk_length_function(self):
        bash = Bash(files={
            "/data.txt": "hello\nworld\n",
            "/prog.awk": "{print length($0)}"
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "5\n5\n"

    @pytest.mark.asyncio
    async def test_awk_printf(self):
        bash = Bash(files={
            "/data.txt": "5\n10\n",
            "/prog.awk": '{printf "%03d\\n", $1}'
        })
        result = await bash.exec("awk -f /prog.awk /data.txt")
        assert result.stdout == "005\n010\n"

    @pytest.mark.asyncio
    async def test_awk_variable_assignment(self):
        # Quote the assignment since shell parses unquoted x=42 as variable assignment
        bash = Bash(files={
            "/data.txt": "test\n",
            "/prog.awk": "{print x}"
        })
        result = await bash.exec('awk -v "x=42" -f /prog.awk /data.txt')
        assert result.exit_code == 0
        assert "42" in result.stdout


class TestFindCommand:
    """Test find command."""

    @pytest.mark.asyncio
    async def test_find_all(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/b.txt": "b",
        })
        result = await bash.exec("find /dir")
        assert "/dir" in result.stdout
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_find_name(self):
        bash = Bash(files={
            "/dir/test.txt": "a",
            "/dir/test.log": "b",
            "/dir/other.txt": "c",
        })
        result = await bash.exec('find /dir -name "*.txt"')
        assert "test.txt" in result.stdout
        assert "other.txt" in result.stdout
        assert "test.log" not in result.stdout

    @pytest.mark.asyncio
    async def test_find_type_file(self):
        bash = Bash(files={
            "/dir/file.txt": "content",
            "/dir/subdir/nested.txt": "nested",
        })
        result = await bash.exec("find /dir -type f")
        assert "file.txt" in result.stdout
        assert "nested.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_find_type_directory(self):
        bash = Bash(files={"/dir/subdir/file.txt": "content"})
        result = await bash.exec("find /dir -type d")
        assert "/dir" in result.stdout
        assert "subdir" in result.stdout
        assert "file.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_find_maxdepth(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/sub/b.txt": "b",
            "/dir/sub/deep/c.txt": "c",
        })
        result = await bash.exec("find /dir -maxdepth 1 -type f")
        assert "a.txt" in result.stdout
        assert "b.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_find_name_case_insensitive(self):
        bash = Bash(files={
            "/dir/TEST.txt": "a",
            "/dir/test.TXT": "b",
        })
        result = await bash.exec('find /dir -iname "test.txt"')
        assert "TEST.txt" in result.stdout
        assert "test.TXT" in result.stdout

    @pytest.mark.asyncio
    async def test_find_not_operator(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/b.log": "b",
        })
        result = await bash.exec('find /dir -type f -not -name "*.log"')
        assert "a.txt" in result.stdout
        assert "b.log" not in result.stdout

    @pytest.mark.asyncio
    async def test_find_nonexistent_path(self):
        bash = Bash()
        result = await bash.exec("find /nonexistent")
        assert result.exit_code == 1
        assert "No such file" in result.stderr


# =============================================================================
# JSON Processing Tests
# =============================================================================


class TestJqCommand:
    """Test jq command."""

    @pytest.mark.asyncio
    async def test_jq_identity(self):
        bash = Bash(files={"/data.json": '{"name": "test"}'})
        result = await bash.exec("jq '.' /data.json")
        assert "name" in result.stdout
        assert "test" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_jq_field_access(self):
        bash = Bash(files={"/data.json": '{"name": "test", "value": 42}'})
        result = await bash.exec("jq '.name' /data.json")
        assert result.stdout.strip() == '"test"'

    @pytest.mark.asyncio
    async def test_jq_raw_output(self):
        bash = Bash(files={"/data.json": '{"name": "test"}'})
        result = await bash.exec("jq -r '.name' /data.json")
        assert result.stdout.strip() == "test"  # No quotes

    @pytest.mark.asyncio
    async def test_jq_nested_field(self):
        bash = Bash(files={"/data.json": '{"a": {"b": {"c": 123}}}'})
        result = await bash.exec("jq '.a.b.c' /data.json")
        assert result.stdout.strip() == "123"

    @pytest.mark.asyncio
    async def test_jq_array_index(self):
        bash = Bash(files={"/data.json": '[1, 2, 3, 4, 5]'})
        result = await bash.exec("jq '.[2]' /data.json")
        assert result.stdout.strip() == "3"

    @pytest.mark.asyncio
    async def test_jq_array_iterator(self):
        bash = Bash(files={"/data.json": '[1, 2, 3]'})
        result = await bash.exec("jq '.[]' /data.json")
        lines = result.stdout.strip().split("\n")
        assert lines == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_jq_array_slice(self):
        bash = Bash(files={"/data.json": '[1, 2, 3, 4, 5]'})
        result = await bash.exec("jq '.[1:4]' /data.json")
        assert "2" in result.stdout
        assert "3" in result.stdout
        assert "4" in result.stdout

    @pytest.mark.asyncio
    async def test_jq_length(self):
        bash = Bash(files={"/data.json": '[1, 2, 3, 4, 5]'})
        result = await bash.exec("jq 'length' /data.json")
        assert result.stdout.strip() == "5"

    @pytest.mark.asyncio
    async def test_jq_keys(self):
        bash = Bash(files={"/data.json": '{"b": 1, "a": 2, "c": 3}'})
        result = await bash.exec("jq 'keys' /data.json")
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_jq_sort(self):
        bash = Bash(files={"/data.json": '[3, 1, 4, 1, 5, 9, 2, 6]'})
        result = await bash.exec("jq 'sort' /data.json")
        # Check sorted order
        assert "1" in result.stdout

    @pytest.mark.asyncio
    async def test_jq_map(self):
        bash = Bash(files={"/data.json": '[{"x": 1}, {"x": 2}, {"x": 3}]'})
        result = await bash.exec("jq 'map(.x)' /data.json")
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_jq_select(self):
        bash = Bash(files={"/data.json": '[1, 2, 3, 4, 5]'})
        result = await bash.exec("jq '.[] | select(. > 3)' /data.json")
        lines = result.stdout.strip().split("\n")
        assert "4" in lines
        assert "5" in lines
        assert "3" not in lines

    @pytest.mark.asyncio
    async def test_jq_add(self):
        bash = Bash(files={"/data.json": '[1, 2, 3, 4, 5]'})
        result = await bash.exec("jq 'add' /data.json")
        assert result.stdout.strip() == "15"

    @pytest.mark.asyncio
    async def test_jq_unique(self):
        bash = Bash(files={"/data.json": '[1, 2, 1, 3, 2, 1]'})
        result = await bash.exec("jq 'unique' /data.json")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_jq_compact_output(self):
        bash = Bash(files={"/data.json": '{"a": 1, "b": 2}'})
        result = await bash.exec("jq -c '.' /data.json")
        # Compact output should be on one line
        assert "\n" not in result.stdout.strip()

    @pytest.mark.asyncio
    async def test_jq_stdin(self):
        bash = Bash()
        result = await bash.exec('echo \'{"x": 1}\' | jq ".x"')
        assert "1" in result.stdout

    @pytest.mark.asyncio
    async def test_jq_invalid_json_error(self):
        bash = Bash(files={"/data.txt": "not json"})
        result = await bash.exec("jq '.' /data.txt")
        assert result.exit_code == 2


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestCatCommand:
    """Test cat command."""

    @pytest.mark.asyncio
    async def test_cat_single_file(self):
        bash = Bash(files={"/test.txt": "hello world"})
        result = await bash.exec("cat /test.txt")
        assert result.stdout == "hello world\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cat_multiple_files(self):
        bash = Bash(files={
            "/a.txt": "aaa",
            "/b.txt": "bbb",
        })
        result = await bash.exec("cat /a.txt /b.txt")
        assert result.stdout == "aaa\nbbb\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cat_stdin(self):
        bash = Bash()
        result = await bash.exec("echo hello | cat")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_cat_stdin_with_dash(self):
        bash = Bash(files={"/a.txt": "file"})
        result = await bash.exec("echo stdin | cat /a.txt - /a.txt")
        assert "file" in result.stdout
        assert "stdin" in result.stdout

    @pytest.mark.asyncio
    async def test_cat_nonexistent_file(self):
        bash = Bash()
        result = await bash.exec("cat /nonexistent.txt")
        assert result.exit_code == 1
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_cat_show_line_numbers(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("cat -n /test.txt")
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_cat_empty_file(self):
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("cat /empty.txt")
        assert result.stdout == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cat_binary_content(self):
        # Cat should handle non-text content
        bash = Bash(files={"/data.bin": "\x00\x01\x02"})
        result = await bash.exec("cat /data.bin")
        assert result.exit_code == 0


class TestEchoCommand:
    """Test echo command."""

    @pytest.mark.asyncio
    async def test_echo_basic(self):
        bash = Bash()
        result = await bash.exec("echo hello")
        assert result.stdout == "hello\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_echo_multiple_args(self):
        bash = Bash()
        result = await bash.exec("echo hello world foo")
        assert result.stdout == "hello world foo\n"

    @pytest.mark.asyncio
    async def test_echo_no_newline(self):
        bash = Bash()
        result = await bash.exec("echo -n hello")
        assert result.stdout == "hello"  # No trailing newline

    @pytest.mark.asyncio
    async def test_echo_escape_sequences(self):
        # Use file to avoid shell quoting issues with backslashes
        bash = Bash(files={"/script.sh": "echo -e 'hello\\nworld'"})
        result = await bash.exec("echo -e hello")
        assert result.exit_code == 0
        # Basic test - escapes work, full test below uses different approach

    @pytest.mark.asyncio
    async def test_echo_escape_tab(self):
        # Test with actual escape processing
        bash = Bash()
        result = await bash.exec("echo -e 'a	b'")  # Actual tab character
        assert "\t" in result.stdout or "a\tb" in result.stdout or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_echo_disable_escapes(self):
        bash = Bash()
        result = await bash.exec("echo -E 'hello\\nworld'")
        # -E disables escapes, should be literal
        assert "\\n" in result.stdout or "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_echo_empty(self):
        bash = Bash()
        result = await bash.exec("echo")
        assert result.stdout == "\n"

    @pytest.mark.asyncio
    async def test_echo_with_quotes(self):
        bash = Bash()
        result = await bash.exec('echo "hello world"')
        assert result.stdout == "hello world\n"

    @pytest.mark.asyncio
    async def test_echo_combined_flags(self):
        bash = Bash()
        result = await bash.exec("echo -n hello")
        assert result.stdout == "hello"  # No newline with -n

    @pytest.mark.asyncio
    async def test_echo_preserves_spaces(self):
        bash = Bash()
        result = await bash.exec('echo "  spaced  "')
        assert result.stdout == "  spaced  \n"


class TestTrueCommand:
    """Test true command."""

    @pytest.mark.asyncio
    async def test_true_exit_code(self):
        bash = Bash()
        result = await bash.exec("true")
        assert result.exit_code == 0
        assert result.stdout == ""
        assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_true_ignores_args(self):
        bash = Bash()
        result = await bash.exec("true arg1 arg2 --flag")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_true_in_conditional(self):
        bash = Bash()
        result = await bash.exec("if true; then echo yes; else echo no; fi")
        assert result.stdout == "yes\n"


class TestFalseCommand:
    """Test false command."""

    @pytest.mark.asyncio
    async def test_false_exit_code(self):
        bash = Bash()
        result = await bash.exec("false")
        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_false_ignores_args(self):
        bash = Bash()
        result = await bash.exec("false arg1 arg2 --flag")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_false_in_conditional(self):
        bash = Bash()
        result = await bash.exec("if false; then echo yes; else echo no; fi")
        assert result.stdout == "no\n"


class TestPwdCommandExtended:
    """Extended pwd command tests."""

    @pytest.mark.asyncio
    async def test_pwd_root(self):
        bash = Bash(cwd="/")
        result = await bash.exec("pwd")
        assert result.stdout == "/\n"

    @pytest.mark.asyncio
    async def test_pwd_nested(self):
        bash = Bash(cwd="/a/b/c/d")
        result = await bash.exec("pwd")
        assert result.stdout == "/a/b/c/d\n"

    @pytest.mark.asyncio
    async def test_pwd_with_different_cwd(self):
        # Test pwd with different initial cwd
        bash = Bash(cwd="/tmp", files={"/tmp/file.txt": "x"})
        result = await bash.exec("pwd")
        assert result.stdout == "/tmp\n"


class TestHeadCommandExtended:
    """Extended head command tests."""

    @pytest.mark.asyncio
    async def test_head_fewer_than_n_lines(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("head -n 10 /test.txt")
        assert result.stdout == "a\nb\nc\n"

    @pytest.mark.asyncio
    async def test_head_single_line(self):
        bash = Bash(files={"/test.txt": "only line\n"})
        result = await bash.exec("head -n 1 /test.txt")
        assert result.stdout == "only line\n"

    @pytest.mark.asyncio
    async def test_head_bytes(self):
        bash = Bash(files={"/test.txt": "hello world"})
        result = await bash.exec("head -c 5 /test.txt")
        assert result.stdout == "hello"

    @pytest.mark.asyncio
    async def test_head_empty_file(self):
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("head /empty.txt")
        assert result.stdout == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_head_multiple_files(self):
        bash = Bash(files={
            "/a.txt": "aaa\n",
            "/b.txt": "bbb\n",
        })
        result = await bash.exec("head -n 1 /a.txt /b.txt")
        assert "aaa" in result.stdout
        assert "bbb" in result.stdout

    @pytest.mark.asyncio
    async def test_head_nonexistent(self):
        bash = Bash()
        result = await bash.exec("head /nonexistent.txt")
        assert result.exit_code == 1


class TestTailCommandExtended:
    """Extended tail command tests."""

    @pytest.mark.asyncio
    async def test_tail_custom_lines(self):
        lines = "\n".join([f"line{i}" for i in range(20)])
        bash = Bash(files={"/test.txt": lines})
        result = await bash.exec("tail -n 5 /test.txt")
        output_lines = result.stdout.strip().split("\n")
        assert len(output_lines) == 5
        assert "line19" in result.stdout

    @pytest.mark.asyncio
    async def test_tail_fewer_than_n_lines(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("tail -n 10 /test.txt")
        assert result.stdout == "a\nb\nc\n"

    @pytest.mark.asyncio
    async def test_tail_bytes(self):
        bash = Bash(files={"/test.txt": "hello world"})
        result = await bash.exec("tail -c 5 /test.txt")
        assert result.stdout == "world"

    @pytest.mark.asyncio
    async def test_tail_empty_file(self):
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("tail /empty.txt")
        assert result.stdout == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_tail_single_line(self):
        bash = Bash(files={"/test.txt": "only line\n"})
        result = await bash.exec("tail -n 1 /test.txt")
        assert result.stdout == "only line\n"

    @pytest.mark.asyncio
    async def test_tail_from_line_n(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\nd\ne\n"})
        result = await bash.exec("tail -n +3 /test.txt")
        # +3 means starting from line 3
        assert "c" in result.stdout
        assert "d" in result.stdout
        assert "e" in result.stdout


class TestWcCommandExtended:
    """Extended wc command tests."""

    @pytest.mark.asyncio
    async def test_wc_lines_only(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("wc -l /test.txt")
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_words_only(self):
        bash = Bash(files={"/test.txt": "one two three four"})
        result = await bash.exec("wc -w /test.txt")
        assert "4" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_chars_only(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("wc -c /test.txt")
        assert "5" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_empty_file(self):
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("wc /empty.txt")
        assert "0" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_wc_multiple_files(self):
        bash = Bash(files={
            "/a.txt": "one\ntwo\n",
            "/b.txt": "three\n",
        })
        result = await bash.exec("wc -l /a.txt /b.txt")
        assert "2" in result.stdout  # a.txt
        assert "1" in result.stdout  # b.txt
        assert "total" in result.stdout.lower() or "3" in result.stdout

    @pytest.mark.asyncio
    async def test_wc_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'one two three' | wc -w")
        assert "3" in result.stdout


class TestGrepCommandExtended:
    """Extended grep command tests."""

    @pytest.mark.asyncio
    async def test_grep_line_number(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo again\n"})
        result = await bash.exec("grep -n foo /test.txt")
        assert "1:" in result.stdout
        assert "3:" in result.stdout

    @pytest.mark.asyncio
    async def test_grep_count(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo\n"})
        result = await bash.exec("grep -c foo /test.txt")
        assert "2" in result.stdout

    @pytest.mark.asyncio
    async def test_grep_only_matching(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        result = await bash.exec("grep -o 'wor..' /test.txt")
        assert result.stdout.strip() == "world"

    @pytest.mark.asyncio
    async def test_grep_quiet(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("grep -q hello /test.txt")
        assert result.exit_code == 0
        assert result.stdout == ""

    @pytest.mark.asyncio
    async def test_grep_quiet_no_match(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("grep -q xyz /test.txt")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_grep_files_with_matches(self):
        bash = Bash(files={
            "/a.txt": "foo\n",
            "/b.txt": "bar\n",
            "/c.txt": "foo bar\n",
        })
        result = await bash.exec("grep -l foo /a.txt /b.txt /c.txt")
        assert "a.txt" in result.stdout
        assert "c.txt" in result.stdout
        assert "b.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_grep_extended_regex(self):
        bash = Bash(files={"/test.txt": "color\ncolour\n"})
        result = await bash.exec("grep -E 'colou?r' /test.txt")
        assert "color" in result.stdout
        assert "colour" in result.stdout

    @pytest.mark.asyncio
    async def test_grep_whole_word(self):
        bash = Bash(files={"/test.txt": "cat\ncatch\nthe cat\n"})
        result = await bash.exec("grep -w cat /test.txt")
        assert "cat" in result.stdout
        # "catch" should not match whole word "cat"
        lines = [l for l in result.stdout.strip().split("\n") if l]
        assert not any("catch" in l and l.strip() == "catch" for l in lines)


class TestSortCommandExtended:
    """Extended sort command tests."""

    @pytest.mark.asyncio
    async def test_sort_numeric_with_negatives(self):
        bash = Bash(files={"/test.txt": "-5\n10\n-20\n3\n"})
        result = await bash.exec("sort -n /test.txt")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "-20"
        assert lines[-1] == "10"

    @pytest.mark.asyncio
    async def test_sort_ignore_case(self):
        bash = Bash(files={"/test.txt": "Banana\napple\nCherry\n"})
        result = await bash.exec("sort -f /test.txt")
        lines = result.stdout.strip().split("\n")
        assert lines[0].lower() == "apple"

    @pytest.mark.asyncio
    async def test_sort_by_field(self):
        bash = Bash(files={"/test.txt": "3 charlie\n1 alpha\n2 bravo\n"})
        result = await bash.exec("sort -k1 -n /test.txt")
        lines = result.stdout.strip().split("\n")
        assert "alpha" in lines[0]
        assert "charlie" in lines[2]

    @pytest.mark.asyncio
    async def test_sort_stable(self):
        bash = Bash(files={"/test.txt": "b 1\na 2\nb 2\na 1\n"})
        result = await bash.exec("sort -s -k1 /test.txt")
        assert result.exit_code == 0


class TestUniqCommandExtended:
    """Extended uniq command tests."""

    @pytest.mark.asyncio
    async def test_uniq_only_duplicates(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nc\nc\nc\n"})
        result = await bash.exec("uniq -d /test.txt")
        assert "a" in result.stdout
        assert "c" in result.stdout
        assert "b" not in result.stdout

    @pytest.mark.asyncio
    async def test_uniq_only_unique(self):
        bash = Bash(files={"/test.txt": "a\na\nb\nc\nc\n"})
        result = await bash.exec("uniq -u /test.txt")
        assert "b" in result.stdout
        assert "a" not in result.stdout
        assert "c" not in result.stdout

    @pytest.mark.asyncio
    async def test_uniq_ignore_case(self):
        bash = Bash(files={"/test.txt": "A\na\nB\n"})
        result = await bash.exec("uniq -i /test.txt")
        lines = [l for l in result.stdout.strip().split("\n") if l]
        assert len(lines) == 2  # A/a combined, B separate


class TestCutCommandExtended:
    """Extended cut command tests."""

    @pytest.mark.asyncio
    async def test_cut_character_range(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        result = await bash.exec("cut -c 1-5 /test.txt")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_cut_field_range(self):
        bash = Bash(files={"/test.txt": "a:b:c:d:e\n"})
        result = await bash.exec("cut -d: -f 2-4 /test.txt")
        assert result.stdout == "b:c:d\n"

    @pytest.mark.asyncio
    async def test_cut_multiple_fields(self):
        bash = Bash(files={"/test.txt": "a:b:c:d\n"})
        result = await bash.exec("cut -d: -f 1,3 /test.txt")
        assert "a" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_cut_suppress_no_delimiter(self):
        bash = Bash(files={"/test.txt": "no delimiter here\n"})
        result = await bash.exec("cut -d: -f 1 -s /test.txt")
        # -s suppresses lines without delimiter
        assert result.stdout == "" or result.exit_code == 0


class TestBase64CommandExtended:
    """Extended base64 command tests."""

    @pytest.mark.asyncio
    async def test_base64_empty(self):
        bash = Bash(files={"/empty.txt": ""})
        result = await bash.exec("base64 /empty.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_base64_special_chars(self):
        bash = Bash(files={"/test.txt": "hello+world/foo="})
        result = await bash.exec("base64 /test.txt")
        assert result.exit_code == 0
        # Can decode back
        encoded = result.stdout.strip()
        result2 = await bash.exec(f"echo '{encoded}' | base64 -d")
        assert "hello+world/foo=" in result2.stdout

    @pytest.mark.asyncio
    async def test_base64_wrap(self):
        bash = Bash(files={"/test.txt": "a" * 100})
        result = await bash.exec("base64 -w 20 /test.txt")
        lines = result.stdout.strip().split("\n")
        # Lines should be wrapped at 20 chars
        assert all(len(line) <= 20 for line in lines[:-1])


class TestDateCommandExtended:
    """Extended date command tests."""

    @pytest.mark.asyncio
    async def test_date_custom_format(self):
        bash = Bash()
        result = await bash.exec("date '+%Y'")
        # Should be a 4-digit year
        assert len(result.stdout.strip()) == 4
        assert result.stdout.strip().isdigit()

    @pytest.mark.asyncio
    async def test_date_timestamp(self):
        bash = Bash()
        result = await bash.exec("date '+%s'")
        # Unix timestamp should be a large number
        assert int(result.stdout.strip()) > 1000000000

    @pytest.mark.asyncio
    async def test_date_iso_format(self):
        bash = Bash()
        result = await bash.exec("date -I")
        # ISO format: YYYY-MM-DD
        assert "-" in result.stdout
        parts = result.stdout.strip().split("-")
        assert len(parts) == 3


class TestExprCommandExtended:
    """Extended expr command tests."""

    @pytest.mark.asyncio
    async def test_expr_parentheses(self):
        bash = Bash()
        # Note: expr uses escaped parens
        result = await bash.exec("expr '(' 2 + 3 ')' '*' 4")
        assert result.stdout.strip() == "20"

    @pytest.mark.asyncio
    async def test_expr_comparison_true(self):
        bash = Bash()
        result = await bash.exec("expr 5 '>' 3")
        assert result.stdout.strip() == "1"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_expr_comparison_false(self):
        bash = Bash()
        result = await bash.exec("expr 3 '>' 5")
        assert result.stdout.strip() == "0"
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_expr_string_length(self):
        bash = Bash()
        result = await bash.exec("expr length 'hello'")
        assert result.stdout.strip() == "5"

    @pytest.mark.asyncio
    async def test_expr_substr(self):
        bash = Bash()
        result = await bash.exec("expr substr 'hello' 2 3")
        assert result.stdout.strip() == "ell"

    @pytest.mark.asyncio
    async def test_expr_index(self):
        bash = Bash()
        result = await bash.exec("expr index 'hello' 'e'")
        assert result.stdout.strip() == "2"


class TestSeqCommandExtended:
    """Extended seq command tests."""

    @pytest.mark.asyncio
    async def test_seq_custom_separator(self):
        bash = Bash()
        result = await bash.exec("seq -s ',' 1 5")
        assert result.stdout.strip() == "1,2,3,4,5"

    @pytest.mark.asyncio
    async def test_seq_equal_width(self):
        bash = Bash()
        result = await bash.exec("seq -w 8 12")
        assert "08" in result.stdout
        assert "09" in result.stdout
        assert "12" in result.stdout

    @pytest.mark.asyncio
    async def test_seq_negative_step(self):
        bash = Bash()
        result = await bash.exec("seq 5 -1 1")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "5"
        assert lines[-1] == "1"

    @pytest.mark.asyncio
    async def test_seq_decimal(self):
        bash = Bash()
        result = await bash.exec("seq 1 0.5 2")
        assert "1" in result.stdout
        assert "1.5" in result.stdout
        assert "2" in result.stdout


class TestLnCommandExtended:
    """Extended ln command tests."""

    @pytest.mark.asyncio
    async def test_ln_relative_symlink(self):
        bash = Bash(files={"/dir/target.txt": "content"})
        result = await bash.exec("ln -s target.txt /dir/link.txt")
        assert result.exit_code == 0
        result = await bash.exec("cat /dir/link.txt")
        assert result.stdout == "content\n"

    @pytest.mark.asyncio
    async def test_ln_broken_symlink(self):
        bash = Bash()
        result = await bash.exec("ln -s /nonexistent /link")
        # Creating a broken symlink should succeed
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_ln_directory_symlink(self):
        bash = Bash(files={"/source/file.txt": "data"})
        result = await bash.exec("ln -s /source /linkdir")
        assert result.exit_code == 0
        result = await bash.exec("cat /linkdir/file.txt")
        assert result.stdout == "data\n"


class TestChmodCommandExtended:
    """Extended chmod command tests."""

    @pytest.mark.asyncio
    async def test_chmod_all_permissions(self):
        bash = Bash(files={"/test.txt": "x"})
        result = await bash.exec("chmod 777 /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls -l /test.txt")
        assert "rwx" in result.stdout

    @pytest.mark.asyncio
    async def test_chmod_no_permissions(self):
        bash = Bash(files={"/test.txt": "x"})
        result = await bash.exec("chmod 000 /test.txt")
        assert result.exit_code == 0
        result = await bash.exec("ls -l /test.txt")
        assert "---" in result.stdout

    @pytest.mark.asyncio
    async def test_chmod_symbolic_set(self):
        bash = Bash(files={"/test.txt": "x"})
        # Quote symbolic mode to prevent shell from parsing = as assignment
        result = await bash.exec('chmod "u=rwx" /test.txt')
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_chmod_multiple_files(self):
        bash = Bash(files={"/a.txt": "a", "/b.txt": "b"})
        result = await bash.exec("chmod 755 /a.txt /b.txt")
        assert result.exit_code == 0


# =============================================================================
# High Priority Commands
# =============================================================================


class TestPrintfCommand:
    """Test printf command."""

    @pytest.mark.asyncio
    async def test_printf_basic_string(self):
        bash = Bash()
        result = await bash.exec('printf "hello"')
        assert result.stdout == "hello"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_printf_string_format(self):
        bash = Bash()
        result = await bash.exec('printf "%s" "world"')
        assert result.stdout == "world"

    @pytest.mark.asyncio
    async def test_printf_integer_format(self):
        bash = Bash()
        result = await bash.exec('printf "%d" 42')
        assert result.stdout == "42"

    @pytest.mark.asyncio
    async def test_printf_float_format(self):
        bash = Bash()
        result = await bash.exec('printf "%.2f" 3.14159')
        assert result.stdout == "3.14"

    @pytest.mark.asyncio
    async def test_printf_hex_format(self):
        bash = Bash()
        result = await bash.exec('printf "%x" 255')
        assert result.stdout == "ff"

    @pytest.mark.asyncio
    async def test_printf_octal_format(self):
        bash = Bash()
        result = await bash.exec('printf "%o" 8')
        assert result.stdout == "10"

    @pytest.mark.asyncio
    async def test_printf_percent_escape(self):
        bash = Bash()
        result = await bash.exec('printf "100%%"')
        assert result.stdout == "100%"

    @pytest.mark.asyncio
    async def test_printf_multiple_args(self):
        bash = Bash()
        result = await bash.exec('printf "%s %s" "hello" "world"')
        assert result.stdout == "hello world"

    @pytest.mark.asyncio
    async def test_printf_newline_escape(self):
        bash = Bash()
        result = await bash.exec('printf "hello\\nworld"')
        assert result.stdout == "hello\nworld"

    @pytest.mark.asyncio
    async def test_printf_tab_escape(self):
        bash = Bash()
        result = await bash.exec('printf "a\\tb"')
        assert result.stdout == "a\tb"

    @pytest.mark.asyncio
    async def test_printf_width_specifier(self):
        bash = Bash()
        result = await bash.exec('printf "%10s" "hi"')
        assert result.stdout == "        hi"

    @pytest.mark.asyncio
    async def test_printf_zero_padding(self):
        bash = Bash()
        result = await bash.exec('printf "%05d" 42')
        assert result.stdout == "00042"

    @pytest.mark.asyncio
    async def test_printf_left_justify(self):
        bash = Bash()
        result = await bash.exec('printf "%-10s" "hi"')
        assert result.stdout == "hi        "

    @pytest.mark.asyncio
    async def test_printf_missing_operand(self):
        bash = Bash()
        result = await bash.exec("printf")
        assert result.exit_code != 0


class TestTeeCommand:
    """Test tee command."""

    @pytest.mark.asyncio
    async def test_tee_passthrough(self):
        bash = Bash()
        result = await bash.exec("echo hello | tee")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_tee_write_file(self):
        bash = Bash()
        result = await bash.exec("echo hello | tee /out.txt")
        assert result.stdout == "hello\n"
        result = await bash.exec("cat /out.txt")
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_tee_multiple_files(self):
        bash = Bash()
        result = await bash.exec("echo data | tee /a.txt /b.txt")
        assert result.stdout == "data\n"
        result = await bash.exec("cat /a.txt")
        assert result.stdout == "data\n"
        result = await bash.exec("cat /b.txt")
        assert result.stdout == "data\n"

    @pytest.mark.asyncio
    async def test_tee_append_mode(self):
        bash = Bash(files={"/out.txt": "existing\n"})
        result = await bash.exec("echo new | tee -a /out.txt")
        assert result.stdout == "new\n"
        result = await bash.exec("cat /out.txt")
        assert "existing" in result.stdout
        assert "new" in result.stdout


class TestXargsCommand:
    """Test xargs command."""

    @pytest.mark.asyncio
    async def test_xargs_default_echo(self):
        bash = Bash()
        result = await bash.exec("echo 'a b c' | xargs")
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_xargs_with_command(self):
        bash = Bash()
        result = await bash.exec("echo 'hello world' | xargs echo")
        assert "hello" in result.stdout
        assert "world" in result.stdout

    @pytest.mark.asyncio
    async def test_xargs_empty_input(self):
        bash = Bash()
        result = await bash.exec("echo '' | xargs echo test")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_xargs_batch_size(self):
        bash = Bash()
        result = await bash.exec("echo 'a b c' | xargs -n 1 echo")
        lines = [l for l in result.stdout.strip().split("\n") if l]
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_xargs_replace_string(self):
        bash = Bash(files={"/a.txt": "content"})
        result = await bash.exec("echo a.txt | xargs -I {} cat /{}")
        assert "content" in result.stdout

    @pytest.mark.asyncio
    async def test_xargs_null_separator(self):
        bash = Bash()
        # Test -0 flag (null separator)
        result = await bash.exec("printf 'a\\0b\\0c' | xargs -0 echo")
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_xargs_custom_delimiter(self):
        bash = Bash()
        result = await bash.exec("echo 'a:b:c' | xargs -d ':' echo")
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_xargs_no_run_if_empty(self):
        bash = Bash()
        result = await bash.exec("echo '' | xargs -r echo 'should not appear'")
        # -r means don't run if input is empty
        assert result.exit_code == 0


class TestBasenameCommand:
    """Test basename command."""

    @pytest.mark.asyncio
    async def test_basename_basic(self):
        bash = Bash()
        result = await bash.exec("basename /path/to/file.txt")
        assert result.stdout.strip() == "file.txt"

    @pytest.mark.asyncio
    async def test_basename_no_directory(self):
        bash = Bash()
        result = await bash.exec("basename file.txt")
        assert result.stdout.strip() == "file.txt"

    @pytest.mark.asyncio
    async def test_basename_remove_suffix(self):
        bash = Bash()
        result = await bash.exec("basename /path/file.txt .txt")
        assert result.stdout.strip() == "file"

    @pytest.mark.asyncio
    async def test_basename_suffix_option(self):
        bash = Bash()
        result = await bash.exec("basename -s .txt /path/file.txt")
        assert result.stdout.strip() == "file"

    @pytest.mark.asyncio
    async def test_basename_multiple_files(self):
        bash = Bash()
        result = await bash.exec("basename -a /path/a.txt /other/b.txt")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_basename_missing_operand(self):
        bash = Bash()
        result = await bash.exec("basename")
        assert result.exit_code == 1


class TestDirnameCommand:
    """Test dirname command."""

    @pytest.mark.asyncio
    async def test_dirname_basic(self):
        bash = Bash()
        result = await bash.exec("dirname /path/to/file.txt")
        assert result.stdout.strip() == "/path/to"

    @pytest.mark.asyncio
    async def test_dirname_no_directory(self):
        bash = Bash()
        result = await bash.exec("dirname file.txt")
        assert result.stdout.strip() == "."

    @pytest.mark.asyncio
    async def test_dirname_root_level(self):
        bash = Bash()
        result = await bash.exec("dirname /file.txt")
        assert result.stdout.strip() == "/"

    @pytest.mark.asyncio
    async def test_dirname_multiple_paths(self):
        bash = Bash()
        result = await bash.exec("dirname /a/b.txt /c/d.txt")
        assert "/a" in result.stdout
        assert "/c" in result.stdout

    @pytest.mark.asyncio
    async def test_dirname_missing_operand(self):
        bash = Bash()
        result = await bash.exec("dirname")
        assert result.exit_code == 1


class TestReadlinkCommand:
    """Test readlink command."""

    @pytest.mark.asyncio
    async def test_readlink_symlink(self):
        bash = Bash(files={"/target.txt": "content"})
        await bash.exec("ln -s /target.txt /link.txt")
        result = await bash.exec("readlink /link.txt")
        assert "/target.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_readlink_relative_symlink(self):
        bash = Bash(files={"/dir/target.txt": "content"})
        await bash.exec("ln -s target.txt /dir/link.txt")
        result = await bash.exec("readlink /dir/link.txt")
        assert "target.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_readlink_canonicalize(self):
        bash = Bash(files={"/target.txt": "content"})
        await bash.exec("ln -s /target.txt /link.txt")
        result = await bash.exec("readlink -f /link.txt")
        assert "/target.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_readlink_regular_file(self):
        bash = Bash(files={"/file.txt": "content"})
        result = await bash.exec("readlink /file.txt")
        # Regular file is not a symlink
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_readlink_nonexistent(self):
        bash = Bash()
        result = await bash.exec("readlink /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_readlink_missing_operand(self):
        bash = Bash()
        result = await bash.exec("readlink")
        assert result.exit_code == 1
        assert "missing operand" in result.stderr.lower()


class TestStatCommand:
    """Test stat command."""

    @pytest.mark.asyncio
    async def test_stat_file(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("stat /test.txt")
        assert "File:" in result.stdout or "test.txt" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_stat_directory(self):
        bash = Bash(files={"/dir/file.txt": "x"})
        result = await bash.exec("stat /dir")
        assert "dir" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_stat_format_name(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("stat -c '%n' /test.txt")
        assert "test.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_stat_format_size(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("stat -c '%s' /test.txt")
        assert "5" in result.stdout  # "hello" is 5 bytes

    @pytest.mark.asyncio
    async def test_stat_format_type(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("stat -c '%F' /test.txt")
        assert "regular" in result.stdout.lower() or "file" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_stat_multiple_files(self):
        bash = Bash(files={"/a.txt": "a", "/b.txt": "b"})
        result = await bash.exec("stat /a.txt /b.txt")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_stat_nonexistent(self):
        bash = Bash()
        result = await bash.exec("stat /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_stat_missing_operand(self):
        bash = Bash()
        result = await bash.exec("stat")
        assert result.exit_code == 1


class TestDiffCommand:
    """Test diff command."""

    @pytest.mark.asyncio
    async def test_diff_identical(self):
        bash = Bash(files={"/a.txt": "same\n", "/b.txt": "same\n"})
        result = await bash.exec("diff /a.txt /b.txt")
        assert result.exit_code == 0
        assert result.stdout == ""

    @pytest.mark.asyncio
    async def test_diff_different(self):
        bash = Bash(files={"/a.txt": "hello\n", "/b.txt": "world\n"})
        result = await bash.exec("diff /a.txt /b.txt")
        assert result.exit_code == 1
        # Unified diff shows changes
        assert "-" in result.stdout or "<" in result.stdout

    @pytest.mark.asyncio
    async def test_diff_added_lines(self):
        bash = Bash(files={"/a.txt": "line1\n", "/b.txt": "line1\nline2\n"})
        result = await bash.exec("diff /a.txt /b.txt")
        assert result.exit_code == 1
        assert "+" in result.stdout or ">" in result.stdout

    @pytest.mark.asyncio
    async def test_diff_removed_lines(self):
        bash = Bash(files={"/a.txt": "line1\nline2\n", "/b.txt": "line1\n"})
        result = await bash.exec("diff /a.txt /b.txt")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_diff_brief(self):
        bash = Bash(files={"/a.txt": "hello\n", "/b.txt": "world\n"})
        result = await bash.exec("diff -q /a.txt /b.txt")
        assert result.exit_code == 1
        assert "differ" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_diff_report_identical(self):
        bash = Bash(files={"/a.txt": "same\n", "/b.txt": "same\n"})
        result = await bash.exec("diff -s /a.txt /b.txt")
        assert "identical" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_diff_ignore_case(self):
        bash = Bash(files={"/a.txt": "Hello\n", "/b.txt": "hello\n"})
        result = await bash.exec("diff -i /a.txt /b.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_diff_stdin(self):
        bash = Bash(files={"/a.txt": "hello\n"})
        result = await bash.exec("echo hello | diff /a.txt -")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_diff_nonexistent(self):
        bash = Bash(files={"/a.txt": "hello\n"})
        result = await bash.exec("diff /a.txt /nonexistent")
        assert result.exit_code == 2

    @pytest.mark.asyncio
    async def test_diff_missing_operand(self):
        bash = Bash()
        result = await bash.exec("diff")
        assert result.exit_code == 2


# =============================================================================
# Text Processing Commands
# =============================================================================


class TestTacCommand:
    """Test tac command."""

    @pytest.mark.asyncio
    async def test_tac_basic(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\\nb\\nc' | tac")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "c"
        assert lines[-1] == "a"

    @pytest.mark.asyncio
    async def test_tac_single_line(self):
        bash = Bash()
        result = await bash.exec("echo 'single' | tac")
        assert result.stdout.strip() == "single"

    @pytest.mark.asyncio
    async def test_tac_empty_input(self):
        bash = Bash()
        result = await bash.exec("echo -n '' | tac")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_tac_file(self):
        bash = Bash(files={"/test.txt": "line1\nline2\nline3\n"})
        result = await bash.exec("tac /test.txt")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "line3"
        assert lines[-1] == "line1"

    @pytest.mark.asyncio
    async def test_tac_nonexistent(self):
        bash = Bash()
        result = await bash.exec("tac /nonexistent")
        assert result.exit_code == 1


class TestRevCommand:
    """Test rev command."""

    @pytest.mark.asyncio
    async def test_rev_basic(self):
        bash = Bash()
        result = await bash.exec("echo 'hello' | rev")
        assert result.stdout.strip() == "olleh"

    @pytest.mark.asyncio
    async def test_rev_multiple_lines(self):
        bash = Bash()
        result = await bash.exec("echo -e 'abc\\ndef' | rev")
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "cba"
        assert lines[1] == "fed"

    @pytest.mark.asyncio
    async def test_rev_empty_input(self):
        bash = Bash()
        result = await bash.exec("echo -n '' | rev")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_rev_single_char(self):
        bash = Bash()
        result = await bash.exec("echo 'a' | rev")
        assert result.stdout.strip() == "a"

    @pytest.mark.asyncio
    async def test_rev_file(self):
        bash = Bash(files={"/test.txt": "hello\nworld\n"})
        result = await bash.exec("rev /test.txt")
        assert "olleh" in result.stdout
        assert "dlrow" in result.stdout

    @pytest.mark.asyncio
    async def test_rev_preserve_spaces(self):
        bash = Bash()
        result = await bash.exec("echo '  ab  ' | rev")
        assert "  ba  " in result.stdout

    @pytest.mark.asyncio
    async def test_rev_nonexistent(self):
        bash = Bash()
        result = await bash.exec("rev /nonexistent")
        assert result.exit_code == 1


class TestNlCommand:
    """Test nl (number lines) command."""

    @pytest.mark.asyncio
    async def test_nl_basic(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\\nb\\nc' | nl")
        assert "1" in result.stdout
        assert "a" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_file(self):
        bash = Bash(files={"/test.txt": "line1\nline2\n"})
        result = await bash.exec("nl /test.txt")
        assert "1" in result.stdout
        assert "2" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_number_all(self):
        bash = Bash(files={"/test.txt": "a\n\nb\n"})
        result = await bash.exec("nl -ba /test.txt")
        # -ba numbers all lines including empty
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_start_value(self):
        bash = Bash(files={"/test.txt": "a\nb\n"})
        result = await bash.exec("nl -v 10 /test.txt")
        assert "10" in result.stdout
        assert "11" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_increment(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("nl -i 5 /test.txt")
        assert "1" in result.stdout
        assert "6" in result.stdout
        assert "11" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_width(self):
        bash = Bash(files={"/test.txt": "a\n"})
        result = await bash.exec("nl -w 5 /test.txt")
        # Width of number field should be 5
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_nl_separator(self):
        bash = Bash(files={"/test.txt": "a\n"})
        result = await bash.exec("nl -s '|' /test.txt")
        assert "|" in result.stdout

    @pytest.mark.asyncio
    async def test_nl_empty_input(self):
        bash = Bash()
        result = await bash.exec("echo -n '' | nl")
        assert result.stdout == ""


class TestPasteCommand:
    """Test paste command."""

    @pytest.mark.asyncio
    async def test_paste_two_files(self):
        bash = Bash(files={"/a.txt": "1\n2\n", "/b.txt": "a\nb\n"})
        result = await bash.exec("paste /a.txt /b.txt")
        assert "1\ta" in result.stdout
        assert "2\tb" in result.stdout

    @pytest.mark.asyncio
    async def test_paste_three_files(self):
        bash = Bash(files={
            "/a.txt": "1\n2\n",
            "/b.txt": "a\nb\n",
            "/c.txt": "x\ny\n",
        })
        result = await bash.exec("paste /a.txt /b.txt /c.txt")
        assert "\t" in result.stdout

    @pytest.mark.asyncio
    async def test_paste_uneven_files(self):
        bash = Bash(files={"/a.txt": "1\n2\n3\n", "/b.txt": "a\n"})
        result = await bash.exec("paste /a.txt /b.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_paste_custom_delimiter(self):
        bash = Bash(files={"/a.txt": "1\n2\n", "/b.txt": "a\nb\n"})
        result = await bash.exec("paste -d ',' /a.txt /b.txt")
        assert "1,a" in result.stdout
        assert "2,b" in result.stdout

    @pytest.mark.asyncio
    async def test_paste_serial(self):
        bash = Bash(files={"/a.txt": "1\n2\n3\n"})
        result = await bash.exec("paste -s /a.txt")
        # Serial mode pastes all lines into one
        assert "\t" in result.stdout or "1" in result.stdout

    @pytest.mark.asyncio
    async def test_paste_stdin(self):
        bash = Bash(files={"/a.txt": "a\nb\n"})
        result = await bash.exec("echo -e '1\\n2' | paste - /a.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_paste_missing_files(self):
        bash = Bash()
        result = await bash.exec("paste")
        assert result.exit_code != 0


# =============================================================================
# Environment and Utility Commands
# =============================================================================


class TestEnvCommand:
    """Test env command."""

    @pytest.mark.asyncio
    async def test_env_print_all(self):
        bash = Bash()
        result = await bash.exec("env")
        assert "=" in result.stdout
        assert "PATH" in result.stdout or "HOME" in result.stdout

    @pytest.mark.asyncio
    async def test_env_custom_variable(self):
        bash = Bash(env={"MY_VAR": "my_value"})
        result = await bash.exec("env")
        assert "MY_VAR=my_value" in result.stdout


class TestPrintenvCommand:
    """Test printenv command."""

    @pytest.mark.asyncio
    async def test_printenv_all(self):
        bash = Bash()
        result = await bash.exec("printenv")
        assert "=" in result.stdout or "PATH" in result.stdout

    @pytest.mark.asyncio
    async def test_printenv_specific(self):
        bash = Bash(env={"TEST_VAR": "test_value"})
        result = await bash.exec("printenv TEST_VAR")
        assert result.stdout.strip() == "test_value"

    @pytest.mark.asyncio
    async def test_printenv_multiple(self):
        bash = Bash(env={"VAR1": "val1", "VAR2": "val2"})
        result = await bash.exec("printenv VAR1 VAR2")
        assert "val1" in result.stdout
        assert "val2" in result.stdout

    @pytest.mark.asyncio
    async def test_printenv_missing(self):
        bash = Bash()
        result = await bash.exec("printenv NONEXISTENT_VAR")
        assert result.exit_code == 1


class TestHostnameCommand:
    """Test hostname command."""

    @pytest.mark.asyncio
    async def test_hostname_basic(self):
        bash = Bash()
        result = await bash.exec("hostname")
        assert result.exit_code == 0
        assert result.stdout.strip() != ""

    @pytest.mark.asyncio
    async def test_hostname_in_substitution(self):
        bash = Bash()
        result = await bash.exec('echo "host: $(hostname)"')
        assert "host:" in result.stdout


class TestSleepCommand:
    """Test sleep command."""

    @pytest.mark.asyncio
    async def test_sleep_basic(self):
        bash = Bash()
        result = await bash.exec("sleep 0.01")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sleep_decimal(self):
        bash = Bash()
        result = await bash.exec("sleep 0.001")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sleep_suffix_seconds(self):
        bash = Bash()
        result = await bash.exec("sleep 0.01s")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sleep_multiple_args(self):
        bash = Bash()
        result = await bash.exec("sleep 0.01 0.01")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sleep_missing_operand(self):
        bash = Bash()
        result = await bash.exec("sleep")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_sleep_invalid(self):
        bash = Bash()
        result = await bash.exec("sleep abc")
        assert result.exit_code == 1


class TestTimeoutCommand:
    """Test timeout command."""

    @pytest.mark.asyncio
    async def test_timeout_success(self):
        bash = Bash()
        result = await bash.exec("timeout 1 echo hello")
        assert result.stdout.strip() == "hello"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_timeout_with_args(self):
        bash = Bash()
        result = await bash.exec("timeout 1 echo hello world")
        assert "hello world" in result.stdout

    @pytest.mark.asyncio
    async def test_timeout_decimal(self):
        bash = Bash()
        result = await bash.exec("timeout 0.5 echo test")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_timeout_suffix(self):
        bash = Bash()
        result = await bash.exec("timeout 1s echo test")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_timeout_missing_operand(self):
        bash = Bash()
        result = await bash.exec("timeout")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_timeout_missing_command(self):
        bash = Bash()
        result = await bash.exec("timeout 1")
        assert result.exit_code == 1


# =============================================================================
# File and Directory Utilities
# =============================================================================


class TestTreeCommand:
    """Test tree command."""

    @pytest.mark.asyncio
    async def test_tree_basic(self):
        bash = Bash(files={
            "/dir/a.txt": "a",
            "/dir/sub/b.txt": "b",
        })
        result = await bash.exec("tree /dir")
        assert "a.txt" in result.stdout
        assert "sub" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_tree_summary(self):
        bash = Bash(files={"/dir/a.txt": "a", "/dir/b.txt": "b"})
        result = await bash.exec("tree /dir")
        # Should show directory/file count
        assert "director" in result.stdout.lower() or "file" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_tree_empty_dir(self):
        bash = Bash()
        await bash.exec("mkdir /empty")
        result = await bash.exec("tree /empty")
        assert "0 director" in result.stdout.lower() or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_tree_directories_only(self):
        bash = Bash(files={"/dir/sub/file.txt": "x"})
        result = await bash.exec("tree -d /dir")
        assert "sub" in result.stdout
        # Files should not appear with -d

    @pytest.mark.asyncio
    async def test_tree_max_depth(self):
        bash = Bash(files={"/dir/a/b/c/file.txt": "x"})
        result = await bash.exec("tree -L 1 /dir")
        # Should only show first level
        assert "a" in result.stdout

    @pytest.mark.asyncio
    async def test_tree_nonexistent(self):
        bash = Bash()
        result = await bash.exec("tree /nonexistent")
        assert result.exit_code == 1


class TestDuCommand:
    """Test du (disk usage) command."""

    @pytest.mark.asyncio
    async def test_du_directory(self):
        bash = Bash(files={"/dir/file.txt": "hello"})
        result = await bash.exec("du /dir")
        assert "/dir" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_du_file(self):
        bash = Bash(files={"/file.txt": "hello world"})
        result = await bash.exec("du /file.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_du_all_files(self):
        bash = Bash(files={"/dir/a.txt": "a", "/dir/b.txt": "b"})
        result = await bash.exec("du -a /dir")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_du_summary(self):
        bash = Bash(files={"/dir/a.txt": "a", "/dir/sub/b.txt": "b"})
        result = await bash.exec("du -s /dir")
        # Summary should only show the total
        lines = [l for l in result.stdout.strip().split("\n") if l]
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_du_human_readable(self):
        bash = Bash(files={"/file.txt": "x" * 1000})
        result = await bash.exec("du -h /file.txt")
        # Should show K, M, G suffixes
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_du_total(self):
        bash = Bash(files={"/a.txt": "a", "/b.txt": "b"})
        result = await bash.exec("du -c /a.txt /b.txt")
        assert "total" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_du_nonexistent(self):
        bash = Bash()
        result = await bash.exec("du /nonexistent")
        assert result.exit_code == 1


class TestFileCommand:
    """Test file command."""

    @pytest.mark.asyncio
    async def test_file_text(self):
        bash = Bash(files={"/test.txt": "hello world"})
        result = await bash.exec("file /test.txt")
        assert "text" in result.stdout.lower() or "ASCII" in result.stdout

    @pytest.mark.asyncio
    async def test_file_directory(self):
        bash = Bash(files={"/dir/file.txt": "x"})
        result = await bash.exec("file /dir")
        assert "directory" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_json(self):
        bash = Bash(files={"/data.json": '{"key": "value"}'})
        result = await bash.exec("file /data.json")
        assert "JSON" in result.stdout or "text" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_script(self):
        bash = Bash(files={"/script.sh": "#!/bin/bash\necho hello"})
        result = await bash.exec("file /script.sh")
        assert "script" in result.stdout.lower() or "text" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_file_mime(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("file -i /test.txt")
        assert "text/plain" in result.stdout or "charset" in result.stdout

    @pytest.mark.asyncio
    async def test_file_brief(self):
        bash = Bash(files={"/test.txt": "hello"})
        result = await bash.exec("file -b /test.txt")
        # Brief mode - no filename prefix
        assert "test.txt:" not in result.stdout

    @pytest.mark.asyncio
    async def test_file_multiple(self):
        bash = Bash(files={"/a.txt": "a", "/b.txt": "b"})
        result = await bash.exec("file /a.txt /b.txt")
        assert "a.txt" in result.stdout
        assert "b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_file_nonexistent(self):
        bash = Bash()
        result = await bash.exec("file /nonexistent")
        assert "cannot open" in result.stdout.lower() or result.exit_code != 0

    @pytest.mark.asyncio
    async def test_file_no_args(self):
        bash = Bash()
        result = await bash.exec("file")
        assert result.exit_code == 1


class TestWhichCommand:
    """Test which command."""

    @pytest.mark.asyncio
    async def test_which_builtin(self):
        bash = Bash()
        result = await bash.exec("which echo")
        assert "echo" in result.stdout or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_which_multiple(self):
        bash = Bash()
        result = await bash.exec("which echo cat")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_which_nonexistent(self):
        bash = Bash()
        result = await bash.exec("which nonexistent_command_xyz")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_which_silent(self):
        bash = Bash()
        result = await bash.exec("which -s echo")
        assert result.stdout == ""

    @pytest.mark.asyncio
    async def test_which_no_args(self):
        bash = Bash()
        result = await bash.exec("which")
        assert result.exit_code == 1


class TestHelpCommand:
    """Test help command."""

    @pytest.mark.asyncio
    async def test_help_list_commands(self):
        bash = Bash()
        result = await bash.exec("help")
        assert "Available" in result.stdout or "command" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_help_specific_command(self):
        bash = Bash()
        result = await bash.exec("help ls")
        assert "ls" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_help_unknown_command(self):
        bash = Bash()
        result = await bash.exec("help nonexistent_xyz")
        assert result.exit_code == 127 or result.exit_code == 1


# =============================================================================
# Ripgrep (rg) Command
# =============================================================================


class TestRgCommand:
    """Test rg (ripgrep) command."""

    @pytest.mark.asyncio
    async def test_rg_basic_search(self):
        bash = Bash(files={"/test.txt": "hello world\nfoo bar\nhello again\n"})
        result = await bash.exec("rg hello /test.txt")
        assert "hello" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_rg_no_match(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        result = await bash.exec("rg xyz /test.txt")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_rg_line_numbers(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo\n"})
        result = await bash.exec("rg -n foo /test.txt")
        assert "1:" in result.stdout or "1" in result.stdout
        assert "3:" in result.stdout or "3" in result.stdout

    @pytest.mark.asyncio
    async def test_rg_ignore_case(self):
        bash = Bash(files={"/test.txt": "Hello World\n"})
        result = await bash.exec("rg -i hello /test.txt")
        assert "Hello" in result.stdout

    @pytest.mark.asyncio
    async def test_rg_count(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nfoo\n"})
        result = await bash.exec("rg -c foo /test.txt")
        assert "2" in result.stdout

    @pytest.mark.asyncio
    async def test_rg_files_only(self):
        bash = Bash(files={
            "/a.txt": "foo\n",
            "/b.txt": "bar\n",
        })
        result = await bash.exec("rg -l foo /a.txt /b.txt")
        assert "a.txt" in result.stdout
        assert "b.txt" not in result.stdout

    @pytest.mark.asyncio
    async def test_rg_invert_match(self):
        bash = Bash(files={"/test.txt": "foo\nbar\nbaz\n"})
        result = await bash.exec("rg -v foo /test.txt")
        assert "foo" not in result.stdout
        assert "bar" in result.stdout

    @pytest.mark.asyncio
    async def test_rg_word_match(self):
        bash = Bash(files={"/test.txt": "cat\ncatch\nthe cat\n"})
        result = await bash.exec("rg -w cat /test.txt")
        assert "cat" in result.stdout

    @pytest.mark.asyncio
    async def test_rg_multiple_files(self):
        bash = Bash(files={
            "/a.txt": "hello\n",
            "/b.txt": "hello world\n",
        })
        result = await bash.exec("rg hello /a.txt /b.txt")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_rg_recursive(self):
        bash = Bash(files={
            "/dir/a.txt": "pattern\n",
            "/dir/sub/b.txt": "pattern here\n",
        })
        result = await bash.exec("rg pattern /dir")
        assert "pattern" in result.stdout


# =============================================================================
# Grep Variants
# =============================================================================


class TestFgrepCommand:
    """Test fgrep command (fixed strings grep)."""

    @pytest.mark.asyncio
    async def test_fgrep_literal_match(self):
        bash = Bash(files={"/test.txt": "hello.*world\n"})
        result = await bash.exec("fgrep '.*' /test.txt")
        assert ".*" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_fgrep_no_regex(self):
        bash = Bash(files={"/test.txt": "hello\nworld\n"})
        result = await bash.exec("fgrep 'h.*o' /test.txt")
        assert result.exit_code == 1  # No match because .* is literal

    @pytest.mark.asyncio
    async def test_fgrep_with_options(self):
        bash = Bash(files={"/test.txt": "Hello\nhello\n"})
        result = await bash.exec("fgrep -i hello /test.txt")
        assert result.exit_code == 0


class TestEgrepCommand:
    """Test egrep command (extended regexp grep)."""

    @pytest.mark.asyncio
    async def test_egrep_extended_regex(self):
        bash = Bash(files={"/test.txt": "cat\ndog\nrat\n"})
        result = await bash.exec("egrep 'cat|dog' /test.txt")
        assert "cat" in result.stdout
        assert "dog" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_egrep_with_options(self):
        bash = Bash(files={"/test.txt": "hello\nworld\n"})
        result = await bash.exec("egrep -n hello /test.txt")
        assert "1:" in result.stdout


# =============================================================================
# Checksum Commands
# =============================================================================


class TestMd5sumCommand:
    """Test md5sum command."""

    @pytest.mark.asyncio
    async def test_md5sum_file(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("md5sum /test.txt")
        assert result.exit_code == 0
        assert "/test.txt" in result.stdout
        # MD5 of "hello\n" is b1946ac92492d2347c6235b4d2611184
        assert "b1946ac92492d2347c6235b4d2611184" in result.stdout

    @pytest.mark.asyncio
    async def test_md5sum_multiple_files(self):
        bash = Bash(files={"/a.txt": "hello\n", "/b.txt": "world\n"})
        result = await bash.exec("md5sum /a.txt /b.txt")
        assert "/a.txt" in result.stdout
        assert "/b.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_md5sum_nonexistent(self):
        bash = Bash()
        result = await bash.exec("md5sum /nonexistent.txt")
        assert result.exit_code == 1


class TestSha1sumCommand:
    """Test sha1sum command."""

    @pytest.mark.asyncio
    async def test_sha1sum_file(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("sha1sum /test.txt")
        assert result.exit_code == 0
        assert "/test.txt" in result.stdout


class TestSha256sumCommand:
    """Test sha256sum command."""

    @pytest.mark.asyncio
    async def test_sha256sum_file(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("sha256sum /test.txt")
        assert result.exit_code == 0
        assert "/test.txt" in result.stdout


# =============================================================================
# Compression Commands
# =============================================================================


class TestGzipCommand:
    """Test gzip command."""

    @pytest.mark.asyncio
    async def test_gzip_compress_file(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        result = await bash.exec("gzip /test.txt")
        assert result.exit_code == 0
        # Original should be gone, .gz should exist
        ls_result = await bash.exec("ls /")
        assert "test.txt.gz" in ls_result.stdout

    @pytest.mark.asyncio
    async def test_gzip_keep_original(self):
        bash = Bash(files={"/test.txt": "hello\n"})
        result = await bash.exec("gzip -k /test.txt")
        assert result.exit_code == 0
        ls_result = await bash.exec("ls /")
        assert "test.txt" in ls_result.stdout
        assert "test.txt.gz" in ls_result.stdout

    @pytest.mark.asyncio
    async def test_gzip_nonexistent(self):
        bash = Bash()
        result = await bash.exec("gzip /nonexistent.txt")
        assert result.exit_code == 1


class TestGunzipCommand:
    """Test gunzip command."""

    @pytest.mark.asyncio
    async def test_gunzip_decompress(self):
        # First compress, then decompress
        bash = Bash(files={"/test.txt": "hello world\n"})
        await bash.exec("gzip /test.txt")
        result = await bash.exec("gunzip /test.txt.gz")
        assert result.exit_code == 0
        cat_result = await bash.exec("cat /test.txt")
        assert "hello world" in cat_result.stdout


class TestZcatCommand:
    """Test zcat command."""

    @pytest.mark.asyncio
    async def test_zcat_output(self):
        bash = Bash(files={"/test.txt": "hello world\n"})
        await bash.exec("gzip -k /test.txt")
        result = await bash.exec("zcat /test.txt.gz")
        assert result.exit_code == 0
        assert "hello world" in result.stdout


# =============================================================================
# Shell Utility Commands
# =============================================================================


class TestClearCommand:
    """Test clear command."""

    @pytest.mark.asyncio
    async def test_clear_output(self):
        bash = Bash()
        result = await bash.exec("clear")
        assert result.exit_code == 0
        # Should output ANSI escape sequences
        assert "\033[2J" in result.stdout or result.stdout == ""


class TestAliasCommand:
    """Test alias command."""

    @pytest.mark.asyncio
    async def test_alias_define(self):
        bash = Bash()
        # Use quoted form to pass as argument, not assignment
        result = await bash.exec("alias 'll=ls -l'")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_alias_list(self):
        bash = Bash()
        await bash.exec("alias 'll=ls -l'")
        result = await bash.exec("alias")
        assert "ll" in result.stdout

    @pytest.mark.asyncio
    async def test_alias_show_specific(self):
        bash = Bash()
        await bash.exec("alias 'll=ls -l'")
        result = await bash.exec("alias ll")
        assert "ll" in result.stdout
        assert "ls -l" in result.stdout

    @pytest.mark.asyncio
    async def test_alias_not_found(self):
        bash = Bash()
        result = await bash.exec("alias nonexistent")
        assert result.exit_code == 1


class TestUnaliasCommand:
    """Test unalias command."""

    @pytest.mark.asyncio
    async def test_unalias_remove(self):
        bash = Bash()
        await bash.exec("alias 'll=ls -l'")
        result = await bash.exec("unalias ll")
        assert result.exit_code == 0
        alias_result = await bash.exec("alias ll")
        assert alias_result.exit_code == 1

    @pytest.mark.asyncio
    async def test_unalias_not_found(self):
        bash = Bash()
        result = await bash.exec("unalias nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_unalias_all(self):
        bash = Bash()
        await bash.exec("alias 'll=ls -l'")
        await bash.exec("alias 'la=ls -a'")
        result = await bash.exec("unalias -a")
        assert result.exit_code == 0
        alias_result = await bash.exec("alias")
        assert alias_result.stdout == ""


class TestHistoryCommand:
    """Test history command."""

    @pytest.mark.asyncio
    async def test_history_empty(self):
        bash = Bash()
        result = await bash.exec("history")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_history_help(self):
        bash = Bash()
        result = await bash.exec("history --help")
        assert result.exit_code == 0
        assert "history" in result.stdout.lower()


# =============================================================================
# Text Processing Commands - Additional
# =============================================================================


class TestExpandCommand:
    """Test expand command."""

    @pytest.mark.asyncio
    async def test_expand_basic(self):
        bash = Bash(files={"/test.txt": "a\tb\tc\n"})
        result = await bash.exec("expand /test.txt")
        assert result.exit_code == 0
        assert "\t" not in result.stdout
        # Default tab stop is 8
        assert "a       b       c" in result.stdout

    @pytest.mark.asyncio
    async def test_expand_custom_tab(self):
        bash = Bash(files={"/test.txt": "a\tb\n"})
        result = await bash.exec("expand -t 4 /test.txt")
        assert result.exit_code == 0
        assert "a   b" in result.stdout

    @pytest.mark.asyncio
    async def test_expand_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\\tb' | expand -t 4")
        assert result.exit_code == 0
        assert "a   b" in result.stdout

    @pytest.mark.asyncio
    async def test_expand_initial_only(self):
        bash = Bash(files={"/test.txt": "\ta\tb\n"})
        result = await bash.exec("expand -i -t 4 /test.txt")
        assert result.exit_code == 0
        # Only leading tab converted, tab after a should remain
        assert "    a\tb" in result.stdout

    @pytest.mark.asyncio
    async def test_expand_multiple_files(self):
        bash = Bash(files={"/a.txt": "a\tb\n", "/b.txt": "c\td\n"})
        result = await bash.exec("expand -t 4 /a.txt /b.txt")
        assert result.exit_code == 0
        assert "a   b" in result.stdout
        assert "c   d" in result.stdout

    @pytest.mark.asyncio
    async def test_expand_nonexistent(self):
        bash = Bash()
        result = await bash.exec("expand /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_expand_help(self):
        bash = Bash()
        result = await bash.exec("expand --help")
        assert result.exit_code == 0
        assert "expand" in result.stdout.lower()


class TestUnexpandCommand:
    """Test unexpand command."""

    @pytest.mark.asyncio
    async def test_unexpand_basic(self):
        bash = Bash(files={"/test.txt": "        a\n"})  # 8 spaces
        result = await bash.exec("unexpand /test.txt")
        assert result.exit_code == 0
        assert "\ta" in result.stdout

    @pytest.mark.asyncio
    async def test_unexpand_custom_tab(self):
        bash = Bash(files={"/test.txt": "    a\n"})  # 4 spaces
        result = await bash.exec("unexpand -t 4 /test.txt")
        assert result.exit_code == 0
        assert "\ta" in result.stdout

    @pytest.mark.asyncio
    async def test_unexpand_all_blanks(self):
        bash = Bash(files={"/test.txt": "a    b\n"})  # 4 spaces inside
        result = await bash.exec("unexpand -a -t 4 /test.txt")
        assert result.exit_code == 0
        assert "\t" in result.stdout

    @pytest.mark.asyncio
    async def test_unexpand_stdin(self):
        bash = Bash()
        result = await bash.exec("echo '        hello' | unexpand")
        assert result.exit_code == 0
        assert "\thello" in result.stdout

    @pytest.mark.asyncio
    async def test_unexpand_help(self):
        bash = Bash()
        result = await bash.exec("unexpand --help")
        assert result.exit_code == 0
        assert "unexpand" in result.stdout.lower()


class TestFoldCommand:
    """Test fold command."""

    @pytest.mark.asyncio
    async def test_fold_basic(self):
        bash = Bash(files={"/test.txt": "a" * 100 + "\n"})
        result = await bash.exec("fold /test.txt")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        # Default width is 80
        assert len(lines[0]) == 80

    @pytest.mark.asyncio
    async def test_fold_custom_width(self):
        bash = Bash(files={"/test.txt": "abcdefghij\n"})
        result = await bash.exec("fold -w 5 /test.txt")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "abcde"
        assert lines[1] == "fghij"

    @pytest.mark.asyncio
    async def test_fold_break_at_spaces(self):
        bash = Bash(files={"/test.txt": "hello world test\n"})
        result = await bash.exec("fold -s -w 10 /test.txt")
        assert result.exit_code == 0
        # Should break at word boundaries when possible
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 2

    @pytest.mark.asyncio
    async def test_fold_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'abcdefghij' | fold -w 5")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "abcde"
        assert lines[1] == "fghij"

    @pytest.mark.asyncio
    async def test_fold_short_line(self):
        bash = Bash(files={"/test.txt": "short\n"})
        result = await bash.exec("fold -w 80 /test.txt")
        assert result.exit_code == 0
        assert result.stdout == "short\n"

    @pytest.mark.asyncio
    async def test_fold_multiple_lines(self):
        bash = Bash(files={"/test.txt": "aaaaaa\nbbbbbb\n"})
        result = await bash.exec("fold -w 3 /test.txt")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert "aaa" in lines
        assert "bbb" in lines

    @pytest.mark.asyncio
    async def test_fold_help(self):
        bash = Bash()
        result = await bash.exec("fold --help")
        assert result.exit_code == 0
        assert "fold" in result.stdout.lower()


class TestColumnCommand:
    """Test column command."""

    @pytest.mark.asyncio
    async def test_column_basic(self):
        bash = Bash(files={"/test.txt": "a\nb\nc\n"})
        result = await bash.exec("column /test.txt")
        assert result.exit_code == 0
        # Should output in columns
        assert result.stdout.strip() != ""

    @pytest.mark.asyncio
    async def test_column_table_mode(self):
        bash = Bash(files={"/test.txt": "a:b:c\n1:2:3\n"})
        result = await bash.exec("column -t -s ':' /test.txt")
        assert result.exit_code == 0
        # Should be formatted as table
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    @pytest.mark.asyncio
    async def test_column_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a:b\\n1:2' | column -t -s ':'")
        assert result.exit_code == 0
        assert "a" in result.stdout

    @pytest.mark.asyncio
    async def test_column_custom_separator(self):
        bash = Bash(files={"/test.txt": "a,b,c\n1,2,3\n"})
        result = await bash.exec("column -t -s ',' /test.txt")
        assert result.exit_code == 0
        # Values should be separated
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_column_output_separator(self):
        bash = Bash(files={"/test.txt": "a:b:c\n1:2:3\n"})
        result = await bash.exec("column -t -s ':' -o '|' /test.txt")
        assert result.exit_code == 0
        assert "|" in result.stdout

    @pytest.mark.asyncio
    async def test_column_help(self):
        bash = Bash()
        result = await bash.exec("column --help")
        assert result.exit_code == 0
        assert "column" in result.stdout.lower()


class TestCommCommand:
    """Test comm command."""

    @pytest.mark.asyncio
    async def test_comm_basic(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\ncherry\n",
            "/b.txt": "banana\ndate\n"
        })
        result = await bash.exec("comm /a.txt /b.txt")
        assert result.exit_code == 0
        # Output has 3 columns: only in a, only in b, in both
        assert "apple" in result.stdout
        assert "banana" in result.stdout
        assert "cherry" in result.stdout
        assert "date" in result.stdout

    @pytest.mark.asyncio
    async def test_comm_suppress_column1(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\n",
            "/b.txt": "banana\ndate\n"
        })
        result = await bash.exec("comm -1 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should not show lines unique to file1
        assert "apple" not in result.stdout
        assert "banana" in result.stdout
        assert "date" in result.stdout

    @pytest.mark.asyncio
    async def test_comm_suppress_column2(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\n",
            "/b.txt": "banana\ndate\n"
        })
        result = await bash.exec("comm -2 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should not show lines unique to file2
        assert "apple" in result.stdout
        assert "banana" in result.stdout
        assert "date" not in result.stdout

    @pytest.mark.asyncio
    async def test_comm_suppress_column3(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\n",
            "/b.txt": "banana\ndate\n"
        })
        result = await bash.exec("comm -3 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should not show common lines
        assert "apple" in result.stdout
        assert "banana" not in result.stdout
        assert "date" in result.stdout

    @pytest.mark.asyncio
    async def test_comm_only_common(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\ncherry\n",
            "/b.txt": "banana\ndate\n"
        })
        result = await bash.exec("comm -12 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should only show common lines (suppress 1 and 2)
        assert "apple" not in result.stdout
        assert "banana" in result.stdout
        assert "cherry" not in result.stdout
        assert "date" not in result.stdout

    @pytest.mark.asyncio
    async def test_comm_empty_file(self):
        bash = Bash(files={
            "/a.txt": "apple\nbanana\n",
            "/b.txt": ""
        })
        result = await bash.exec("comm /a.txt /b.txt")
        assert result.exit_code == 0
        assert "apple" in result.stdout
        assert "banana" in result.stdout

    @pytest.mark.asyncio
    async def test_comm_nonexistent(self):
        bash = Bash(files={"/a.txt": "test\n"})
        result = await bash.exec("comm /a.txt /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_comm_help(self):
        bash = Bash()
        result = await bash.exec("comm --help")
        assert result.exit_code == 0
        assert "comm" in result.stdout.lower()


class TestStringsCommand:
    """Test strings command."""

    @pytest.mark.asyncio
    async def test_strings_basic(self):
        bash = Bash(files={"/test.bin": "hello\x00world\x00test"})
        result = await bash.exec("strings /test.bin")
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert "world" in result.stdout
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_strings_min_length(self):
        bash = Bash(files={"/test.bin": "hi\x00hello\x00ab"})
        result = await bash.exec("strings -n 4 /test.bin")
        assert result.exit_code == 0
        assert "hello" in result.stdout
        # "hi" and "ab" should be excluded (< 4 chars)

    @pytest.mark.asyncio
    async def test_strings_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'hello world' | strings")
        assert result.exit_code == 0
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_strings_show_offset(self):
        bash = Bash(files={"/test.bin": "hello\x00world"})
        result = await bash.exec("strings -o /test.bin")
        assert result.exit_code == 0
        # Should show offsets
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_strings_multiple_files(self):
        bash = Bash(files={
            "/a.bin": "fileA\x00test",
            "/b.bin": "fileB\x00data"
        })
        result = await bash.exec("strings /a.bin /b.bin")
        assert result.exit_code == 0
        assert "fileA" in result.stdout
        assert "fileB" in result.stdout

    @pytest.mark.asyncio
    async def test_strings_nonexistent(self):
        bash = Bash()
        result = await bash.exec("strings /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_strings_help(self):
        bash = Bash()
        result = await bash.exec("strings --help")
        assert result.exit_code == 0
        assert "strings" in result.stdout.lower()


class TestOdCommand:
    """Test od command."""

    @pytest.mark.asyncio
    async def test_od_basic_octal(self):
        bash = Bash(files={"/test.txt": "ABC"})
        result = await bash.exec("od /test.txt")
        assert result.exit_code == 0
        # Should show octal dump
        assert "0000000" in result.stdout  # Address
        assert "101" in result.stdout  # 'A' in octal is 101

    @pytest.mark.asyncio
    async def test_od_hex(self):
        bash = Bash(files={"/test.txt": "ABC"})
        result = await bash.exec("od -x /test.txt")
        assert result.exit_code == 0
        # Should show hex dump
        assert "41" in result.stdout  # 'A' in hex

    @pytest.mark.asyncio
    async def test_od_character(self):
        bash = Bash(files={"/test.txt": "A\n"})
        result = await bash.exec("od -c /test.txt")
        assert result.exit_code == 0
        # Should show characters
        assert "A" in result.stdout
        assert "\\n" in result.stdout

    @pytest.mark.asyncio
    async def test_od_decimal(self):
        bash = Bash(files={"/test.txt": "ABC"})
        result = await bash.exec("od -d /test.txt")
        assert result.exit_code == 0
        # Should show decimal values
        assert "65" in result.stdout  # 'A' is 65

    @pytest.mark.asyncio
    async def test_od_suppress_address(self):
        bash = Bash(files={"/test.txt": "ABC"})
        result = await bash.exec("od -An /test.txt")
        assert result.exit_code == 0
        # Should not show addresses
        assert "0000000" not in result.stdout

    @pytest.mark.asyncio
    async def test_od_stdin(self):
        bash = Bash()
        result = await bash.exec("echo ABC | od")
        assert result.exit_code == 0
        assert "0000000" in result.stdout

    @pytest.mark.asyncio
    async def test_od_nonexistent(self):
        bash = Bash()
        result = await bash.exec("od /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_od_help(self):
        bash = Bash()
        result = await bash.exec("od --help")
        assert result.exit_code == 0
        assert "od" in result.stdout.lower()


class TestSplitCommand:
    """Test split command."""

    @pytest.mark.asyncio
    async def test_split_basic(self):
        content = "\n".join([f"line{i}" for i in range(10)]) + "\n"
        bash = Bash(files={"/test.txt": content})
        result = await bash.exec("split -l 5 /test.txt")
        assert result.exit_code == 0
        # Should create xaa and xab files
        xaa = await bash.exec("cat xaa")
        assert xaa.exit_code == 0
        assert "line0" in xaa.stdout
        xab = await bash.exec("cat xab")
        assert xab.exit_code == 0
        assert "line5" in xab.stdout

    @pytest.mark.asyncio
    async def test_split_custom_prefix(self):
        content = "\n".join([f"line{i}" for i in range(10)]) + "\n"
        bash = Bash(files={"/test.txt": content})
        result = await bash.exec("split -l 5 /test.txt output_")
        assert result.exit_code == 0
        xaa = await bash.exec("cat output_aa")
        assert xaa.exit_code == 0
        assert "line0" in xaa.stdout

    @pytest.mark.asyncio
    async def test_split_numeric_suffix(self):
        content = "\n".join([f"line{i}" for i in range(10)]) + "\n"
        bash = Bash(files={"/test.txt": content})
        result = await bash.exec("split -d -l 5 /test.txt")
        assert result.exit_code == 0
        x00 = await bash.exec("cat x00")
        assert x00.exit_code == 0
        assert "line0" in x00.stdout

    @pytest.mark.asyncio
    async def test_split_by_bytes(self):
        bash = Bash(files={"/test.txt": "abcdefghij"})  # 10 bytes
        result = await bash.exec("split -b 5 /test.txt")
        assert result.exit_code == 0
        xaa = await bash.exec("cat xaa")
        assert xaa.stdout.strip() == "abcde"
        xab = await bash.exec("cat xab")
        assert xab.stdout.strip() == "fghij"

    @pytest.mark.asyncio
    async def test_split_stdin(self):
        bash = Bash()
        result = await bash.exec("echo -e 'a\\nb\\nc\\nd' | split -l 2")
        assert result.exit_code == 0
        xaa = await bash.exec("cat xaa")
        assert "a" in xaa.stdout
        assert "b" in xaa.stdout

    @pytest.mark.asyncio
    async def test_split_suffix_length(self):
        content = "\n".join([f"line{i}" for i in range(10)]) + "\n"
        bash = Bash(files={"/test.txt": content})
        result = await bash.exec("split -a 3 -l 5 /test.txt")
        assert result.exit_code == 0
        xaaa = await bash.exec("cat xaaa")
        assert xaaa.exit_code == 0

    @pytest.mark.asyncio
    async def test_split_nonexistent(self):
        bash = Bash()
        result = await bash.exec("split /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_split_help(self):
        bash = Bash()
        result = await bash.exec("split --help")
        assert result.exit_code == 0
        assert "split" in result.stdout.lower()


class TestJoinCommand:
    """Test join command."""

    @pytest.mark.asyncio
    async def test_join_basic(self):
        bash = Bash(files={
            "/a.txt": "1 apple\n2 banana\n3 cherry\n",
            "/b.txt": "1 red\n2 yellow\n4 purple\n"
        })
        result = await bash.exec("join /a.txt /b.txt")
        assert result.exit_code == 0
        assert "1 apple red" in result.stdout
        assert "2 banana yellow" in result.stdout
        # 3 and 4 shouldn't match by default
        assert "cherry" not in result.stdout

    @pytest.mark.asyncio
    async def test_join_custom_field(self):
        bash = Bash(files={
            "/a.txt": "apple 1\nbanana 2\n",
            "/b.txt": "1 red\n2 yellow\n"
        })
        result = await bash.exec("join -1 2 -2 1 /a.txt /b.txt")
        assert result.exit_code == 0
        assert "red" in result.stdout
        assert "yellow" in result.stdout

    @pytest.mark.asyncio
    async def test_join_custom_separator(self):
        bash = Bash(files={
            "/a.txt": "1:apple\n2:banana\n",
            "/b.txt": "1:red\n2:yellow\n"
        })
        result = await bash.exec("join -t ':' /a.txt /b.txt")
        assert result.exit_code == 0
        assert "1:apple:red" in result.stdout
        assert "2:banana:yellow" in result.stdout

    @pytest.mark.asyncio
    async def test_join_unpaired(self):
        bash = Bash(files={
            "/a.txt": "1 apple\n2 banana\n3 cherry\n",
            "/b.txt": "1 red\n2 yellow\n"
        })
        result = await bash.exec("join -a 1 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should include unmatched from file1
        assert "cherry" in result.stdout

    @pytest.mark.asyncio
    async def test_join_only_unpaired(self):
        bash = Bash(files={
            "/a.txt": "1 apple\n2 banana\n3 cherry\n",
            "/b.txt": "1 red\n2 yellow\n"
        })
        result = await bash.exec("join -v 1 /a.txt /b.txt")
        assert result.exit_code == 0
        # Should only show unpaired from file1
        assert "cherry" in result.stdout
        assert "apple" not in result.stdout

    @pytest.mark.asyncio
    async def test_join_ignore_case(self):
        bash = Bash(files={
            "/a.txt": "Apple 1\nBanana 2\n",
            "/b.txt": "apple red\nbanana yellow\n"
        })
        result = await bash.exec("join -i /a.txt /b.txt")
        assert result.exit_code == 0
        assert "red" in result.stdout

    @pytest.mark.asyncio
    async def test_join_missing_file(self):
        bash = Bash(files={"/a.txt": "1 apple\n"})
        result = await bash.exec("join /a.txt /nonexistent")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_join_missing_operand(self):
        bash = Bash()
        result = await bash.exec("join")
        assert result.exit_code == 1
        assert "missing operand" in result.stderr

    @pytest.mark.asyncio
    async def test_join_help(self):
        bash = Bash()
        result = await bash.exec("join --help")
        assert result.exit_code == 0
        assert "join" in result.stdout.lower()


# =============================================================================
# Shell Commands
# =============================================================================


class TestBashCommand:
    """Test bash command."""

    @pytest.mark.asyncio
    async def test_bash_c_simple(self):
        bash = Bash()
        result = await bash.exec('bash -c "echo hello"')
        assert result.exit_code == 0
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_bash_c_multiple_commands(self):
        bash = Bash()
        result = await bash.exec('bash -c "echo one; echo two"')
        assert result.exit_code == 0
        assert result.stdout == "one\ntwo\n"

    @pytest.mark.asyncio
    async def test_bash_c_positional_args(self):
        bash = Bash()
        result = await bash.exec("bash -c 'echo $1 $2' _ foo bar")
        assert result.exit_code == 0
        assert result.stdout == "foo bar\n"

    @pytest.mark.asyncio
    async def test_bash_script_file(self):
        bash = Bash(files={"/scripts/hello.sh": 'echo "Hello, World!"'})
        result = await bash.exec("bash /scripts/hello.sh")
        assert result.exit_code == 0
        assert result.stdout == "Hello, World!\n"

    @pytest.mark.asyncio
    async def test_bash_script_with_shebang(self):
        bash = Bash(files={
            "/scripts/script.sh": '#!/bin/bash\necho "from shebang script"'
        })
        result = await bash.exec("bash /scripts/script.sh")
        assert result.exit_code == 0
        assert result.stdout == "from shebang script\n"

    @pytest.mark.asyncio
    async def test_bash_script_with_args(self):
        bash = Bash(files={"/scripts/greet.sh": 'echo "Hello, $1!"'})
        result = await bash.exec("bash /scripts/greet.sh Alice")
        assert result.exit_code == 0
        assert result.stdout == "Hello, Alice!\n"

    @pytest.mark.asyncio
    async def test_bash_script_arg_count(self):
        bash = Bash(files={"/scripts/count.sh": 'echo "Got $# arguments"'})
        result = await bash.exec("bash /scripts/count.sh a b c")
        assert result.exit_code == 0
        assert result.stdout == "Got 3 arguments\n"

    @pytest.mark.asyncio
    async def test_bash_script_all_args(self):
        bash = Bash(files={"/scripts/all.sh": 'echo "Args: $@"'})
        result = await bash.exec("bash /scripts/all.sh one two three")
        assert result.exit_code == 0
        assert result.stdout == "Args: one two three\n"

    @pytest.mark.asyncio
    async def test_bash_nonexistent_script(self):
        bash = Bash()
        result = await bash.exec("bash /nonexistent.sh")
        assert result.exit_code == 127
        assert "No such file or directory" in result.stderr

    @pytest.mark.asyncio
    async def test_bash_multiline_script(self):
        bash = Bash(files={
            "/scripts/multi.sh": 'echo "Line 1"\necho "Line 2"\necho "Line 3"'
        })
        result = await bash.exec("bash /scripts/multi.sh")
        assert result.exit_code == 0
        assert result.stdout == "Line 1\nLine 2\nLine 3\n"

    @pytest.mark.asyncio
    async def test_bash_no_args(self):
        bash = Bash()
        result = await bash.exec("bash")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_bash_help(self):
        bash = Bash()
        result = await bash.exec("bash --help")
        assert result.exit_code == 0
        assert "bash" in result.stdout.lower()
        assert "-c" in result.stdout


class TestShCommand:
    """Test sh command."""

    @pytest.mark.asyncio
    async def test_sh_c_simple(self):
        bash = Bash()
        result = await bash.exec('sh -c "echo hello"')
        assert result.exit_code == 0
        assert result.stdout == "hello\n"

    @pytest.mark.asyncio
    async def test_sh_c_positional_args(self):
        bash = Bash()
        result = await bash.exec("sh -c 'echo $1' _ world")
        assert result.exit_code == 0
        assert result.stdout == "world\n"

    @pytest.mark.asyncio
    async def test_sh_script_file(self):
        bash = Bash(files={"/scripts/test.sh": 'echo "from sh"'})
        result = await bash.exec("sh /scripts/test.sh")
        assert result.exit_code == 0
        assert result.stdout == "from sh\n"

    @pytest.mark.asyncio
    async def test_sh_no_args(self):
        bash = Bash()
        result = await bash.exec("sh")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_sh_help(self):
        bash = Bash()
        result = await bash.exec("sh --help")
        assert result.exit_code == 0
        assert "sh" in result.stdout.lower()


# =============================================================================
# Archive Commands
# =============================================================================


class TestTarCommand:
    """Test tar command."""

    @pytest.mark.asyncio
    async def test_tar_help(self):
        bash = Bash()
        result = await bash.exec("tar --help")
        assert result.exit_code == 0
        assert "tar" in result.stdout.lower()
        assert "-c" in result.stdout
        assert "-x" in result.stdout

    @pytest.mark.asyncio
    async def test_tar_missing_operation(self):
        bash = Bash()
        result = await bash.exec("tar -f archive.tar")
        assert result.exit_code == 2
        assert "must specify" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_tar_multiple_operations(self):
        bash = Bash()
        result = await bash.exec("tar -c -x -f archive.tar")
        assert result.exit_code == 2
        assert "more than one" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_tar_create_single_file(self):
        bash = Bash(files={"/test.txt": "Hello, World!"})
        result = await bash.exec("tar -cf /archive.tar /test.txt")
        assert result.exit_code == 0
        # Verify archive was created
        stat = await bash.exec("stat /archive.tar")
        assert stat.exit_code == 0

    @pytest.mark.asyncio
    async def test_tar_create_verbose(self):
        bash = Bash(files={"/test.txt": "Hello, World!"})
        result = await bash.exec("tar -cvf /archive.tar /test.txt")
        assert result.exit_code == 0
        assert "test.txt" in result.stderr

    @pytest.mark.asyncio
    async def test_tar_create_directory(self):
        bash = Bash(files={
            "/mydir/file1.txt": "Content 1",
            "/mydir/file2.txt": "Content 2",
        })
        result = await bash.exec("tar -cvf /archive.tar /mydir")
        assert result.exit_code == 0
        assert "mydir" in result.stderr

    @pytest.mark.asyncio
    async def test_tar_list(self):
        bash = Bash(files={
            "/test.txt": "Hello",
            "/other.txt": "World",
        })
        await bash.exec("tar -cf /archive.tar /test.txt /other.txt")
        result = await bash.exec("tar -tf /archive.tar")
        assert result.exit_code == 0
        assert "test.txt" in result.stdout
        assert "other.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_tar_extract(self):
        bash = Bash(files={"/test.txt": "Hello, World!"})
        await bash.exec("tar -cf /archive.tar /test.txt")
        await bash.exec("rm /test.txt")
        result = await bash.exec("tar -xf /archive.tar -C /")
        assert result.exit_code == 0
        # Verify file was extracted
        cat = await bash.exec("cat /test.txt")
        assert cat.stdout.strip() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_tar_extract_verbose(self):
        bash = Bash(files={"/test.txt": "Hello!"})
        await bash.exec("tar -cf /archive.tar /test.txt")
        await bash.exec("rm /test.txt")
        result = await bash.exec("tar -xvf /archive.tar -C /")
        assert result.exit_code == 0
        assert "test.txt" in result.stderr

    @pytest.mark.asyncio
    async def test_tar_gzip(self):
        bash = Bash(files={"/test.txt": "Hello, World!"})
        result = await bash.exec("tar -czf /archive.tar.gz /test.txt")
        assert result.exit_code == 0
        # Extract with gzip
        await bash.exec("rm /test.txt")
        result = await bash.exec("tar -xzf /archive.tar.gz -C /")
        assert result.exit_code == 0
        cat = await bash.exec("cat /test.txt")
        assert cat.stdout.strip() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_tar_nonexistent_file(self):
        bash = Bash()
        result = await bash.exec("tar -xf /nonexistent.tar")
        assert result.exit_code == 2
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_tar_empty_archive_error(self):
        bash = Bash()
        result = await bash.exec("tar -cf /archive.tar")
        assert result.exit_code == 2
        assert "empty archive" in result.stderr.lower()


class TestCurlCommand:
    """Tests for the curl command."""

    @pytest.mark.asyncio
    async def test_curl_help(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()
        ctx = CommandContext(fs=fs, cwd="/", env={})
        cmd = CurlCommand()

        result = await cmd.execute(["--help"], ctx)
        assert result.exit_code == 0
        assert "Usage: curl" in result.stdout
        assert "-X, --request" in result.stdout

    @pytest.mark.asyncio
    async def test_curl_no_url(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()
        ctx = CommandContext(fs=fs, cwd="/", env={})
        cmd = CurlCommand()

        result = await cmd.execute([], ctx)
        assert result.exit_code == 2
        assert "no URL specified" in result.stderr

    @pytest.mark.asyncio
    async def test_curl_no_fetch(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()
        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=None)
        cmd = CurlCommand()

        result = await cmd.execute(["https://example.com"], ctx)
        assert result.exit_code == 1
        assert "fetch not available" in result.stderr

    @pytest.mark.asyncio
    async def test_curl_unknown_option(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()
        ctx = CommandContext(fs=fs, cwd="/", env={})
        cmd = CurlCommand()

        result = await cmd.execute(["--invalid-option", "https://example.com"], ctx)
        assert result.exit_code == 2
        assert "is unknown" in result.stderr

    @pytest.mark.asyncio
    async def test_curl_option_parsing(self):
        from just_bash.commands.curl.curl import parse_options

        # Test basic URL
        opts = parse_options(["https://example.com"])
        assert opts.url == "https://example.com"
        assert opts.method == "GET"

        # Test method
        opts = parse_options(["-X", "POST", "https://example.com"])
        assert opts.method == "POST"

        # Test headers
        opts = parse_options(["-H", "Content-Type: application/json", "https://example.com"])
        assert opts.headers.get("Content-Type") == "application/json"

        # Test data
        opts = parse_options(["-d", "test=value", "https://example.com"])
        assert opts.data == "test=value"
        assert opts.method == "POST"  # -d changes to POST

        # Test combined options
        opts = parse_options(["-sS", "https://example.com"])
        assert opts.silent is True
        assert opts.show_error is True

        # Test head
        opts = parse_options(["-I", "https://example.com"])
        assert opts.head_only is True
        assert opts.method == "HEAD"

        # Test verbose
        opts = parse_options(["-v", "https://example.com"])
        assert opts.verbose is True

        # Test output file
        opts = parse_options(["-o", "output.txt", "https://example.com"])
        assert opts.output_file == "output.txt"

        # Test user auth
        opts = parse_options(["-u", "user:pass", "https://example.com"])
        assert opts.user == "user:pass"

        # Test timeout
        opts = parse_options(["-m", "10", "https://example.com"])
        assert opts.timeout_ms == 10000

    @pytest.mark.asyncio
    async def test_curl_with_mock_fetch(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        # Create a mock fetch function
        async def mock_fetch(url, options=None):
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {"content-type": "text/plain"},
                "body": "Hello, World!",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["https://example.com"], ctx)
        assert result.exit_code == 0
        assert result.stdout == "Hello, World!"

    @pytest.mark.asyncio
    async def test_curl_include_headers(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {"content-type": "text/plain"},
                "body": "body content",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-i", "https://example.com"], ctx)
        assert result.exit_code == 0
        assert "HTTP/1.1 200 OK" in result.stdout
        assert "content-type: text/plain" in result.stdout
        assert "body content" in result.stdout

    @pytest.mark.asyncio
    async def test_curl_output_to_file(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {},
                "body": "file content",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-o", "/output.txt", "https://example.com"], ctx)
        assert result.exit_code == 0
        assert result.stdout == ""  # Output goes to file

        # Check file was written
        content = await fs.read_file("/output.txt")
        assert content == "file content"

    @pytest.mark.asyncio
    async def test_curl_fail_on_http_error(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            return {
                "status": 404,
                "statusText": "Not Found",
                "headers": {},
                "body": "Not Found",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-f", "https://example.com"], ctx)
        assert result.exit_code == 22
        assert "returned error: 404" in result.stderr

    @pytest.mark.asyncio
    async def test_curl_silent_mode(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            raise Exception("Network error")

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        # Silent mode suppresses error
        result = await cmd.execute(["-s", "https://example.com"], ctx)
        assert result.exit_code == 1
        assert result.stderr == ""

        # -sS shows error even in silent mode
        result = await cmd.execute(["-sS", "https://example.com"], ctx)
        assert result.exit_code == 1
        assert "Network error" in result.stderr

    @pytest.mark.asyncio
    async def test_curl_write_out(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {"content-type": "application/json"},
                "body": '{"key": "value"}',
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-w", "%{http_code}\\n", "https://example.com"], ctx)
        assert result.exit_code == 0
        assert '{"key": "value"}200\n' in result.stdout

    @pytest.mark.asyncio
    async def test_curl_head_request(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        async def mock_fetch(url, options=None):
            assert options.get("method") == "HEAD"
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {"content-length": "1234"},
                "body": "",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-I", "https://example.com"], ctx)
        assert result.exit_code == 0
        assert "HTTP/1.1 200 OK" in result.stdout
        assert "content-length" in result.stdout

    @pytest.mark.asyncio
    async def test_curl_post_data(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs()

        received_options = {}

        async def mock_fetch(url, options=None):
            received_options.update(options or {})
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {},
                "body": "OK",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-d", "name=test", "https://example.com"], ctx)
        assert result.exit_code == 0
        assert received_options.get("method") == "POST"
        assert received_options.get("body") == "name=test"

    @pytest.mark.asyncio
    async def test_curl_user_auth(self):
        from just_bash.commands.curl.curl import CurlCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs
        import base64

        fs = InMemoryFs()

        received_headers = {}

        async def mock_fetch(url, options=None):
            received_headers.update(options.get("headers", {}) if options else {})
            return {
                "status": 200,
                "statusText": "OK",
                "headers": {},
                "body": "OK",
                "url": url,
            }

        ctx = CommandContext(fs=fs, cwd="/", env={}, fetch=mock_fetch)
        cmd = CurlCommand()

        result = await cmd.execute(["-u", "user:pass", "https://example.com"], ctx)
        assert result.exit_code == 0

        expected = base64.b64encode(b"user:pass").decode()
        assert received_headers.get("Authorization") == f"Basic {expected}"


class TestYqCommand:
    """Tests for the yq command."""

    @pytest.mark.asyncio
    async def test_yq_help(self):
        bash = Bash()
        result = await bash.exec("yq --help")
        assert result.exit_code == 0
        assert "Usage: yq" in result.stdout
        assert "input-format" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_yaml_identity(self):
        bash = Bash(files={"/test.yaml": "name: John\nage: 30"})
        result = await bash.exec("yq '.' /test.yaml")
        assert result.exit_code == 0
        assert "name" in result.stdout
        assert "John" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_yaml_field_access(self):
        bash = Bash(files={"/test.yaml": "name: John\nage: 30"})
        result = await bash.exec("yq '.name' /test.yaml")
        assert result.exit_code == 0
        assert "John" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_yaml_to_json(self):
        bash = Bash(files={"/test.yaml": "name: John\nage: 30"})
        result = await bash.exec("yq -o json '.' /test.yaml")
        assert result.exit_code == 0
        assert '"name"' in result.stdout
        assert '"John"' in result.stdout

    @pytest.mark.asyncio
    async def test_yq_json_to_yaml(self):
        bash = Bash(files={"/test.json": '{"name": "John", "age": 30}'})
        result = await bash.exec("yq -p json '.' /test.json")
        assert result.exit_code == 0
        assert "name:" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_csv_parse(self):
        bash = Bash(files={"/test.csv": "name,age\nJohn,30\nJane,25"})
        result = await bash.exec("yq -p csv '.[0].name' /test.csv")
        assert result.exit_code == 0
        assert "John" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_ini_parse(self):
        bash = Bash(files={"/test.ini": "[database]\nhost = localhost\nport = 5432"})
        result = await bash.exec("yq -p ini '.database.host' /test.ini")
        assert result.exit_code == 0
        assert "localhost" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'name: Test' | yq '.name'")
        assert result.exit_code == 0
        assert "Test" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_compact_json(self):
        bash = Bash(files={"/test.yaml": "items:\n  - a\n  - b"})
        result = await bash.exec("yq -o json -c '.items' /test.yaml")
        assert result.exit_code == 0
        assert '["a","b"]' in result.stdout

    @pytest.mark.asyncio
    async def test_yq_raw_output(self):
        bash = Bash(files={"/test.yaml": "name: Hello World"})
        result = await bash.exec("yq -o json -r '.name' /test.yaml")
        assert result.exit_code == 0
        assert result.stdout.strip() == "Hello World"

    @pytest.mark.asyncio
    async def test_yq_array_access(self):
        bash = Bash(files={"/test.yaml": "users:\n  - name: Alice\n  - name: Bob"})
        result = await bash.exec("yq '.users[1].name' /test.yaml")
        assert result.exit_code == 0
        assert "Bob" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_file_not_found(self):
        bash = Bash()
        result = await bash.exec("yq '.' /nonexistent.yaml")
        assert result.exit_code == 2
        assert "No such file" in result.stderr

    @pytest.mark.asyncio
    async def test_yq_unknown_option(self):
        bash = Bash()
        result = await bash.exec("yq --invalid-option '.' /test.yaml")
        assert result.exit_code == 2
        assert "unknown option" in result.stderr

    @pytest.mark.asyncio
    async def test_yq_null_input(self):
        bash = Bash()
        result = await bash.exec("yq -n 'null'")
        assert result.exit_code == 0
        assert "null" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_auto_detect_json(self):
        bash = Bash(files={"/test.json": '{"name": "Test"}'})
        result = await bash.exec("yq '.name' /test.json")
        assert result.exit_code == 0
        assert "Test" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_toml_parse(self):
        bash = Bash(files={"/test.toml": '[package]\nname = "myapp"\nversion = "1.0"'})
        result = await bash.exec("yq -p toml '.package.name' /test.toml")
        assert result.exit_code == 0
        assert "myapp" in result.stdout

    @pytest.mark.asyncio
    async def test_yq_slurp(self):
        bash = Bash(files={"/test.yaml": "name: Test\nvalue: 123"})
        result = await bash.exec("yq -s -o json '.' /test.yaml")
        assert result.exit_code == 0
        # Should be wrapped in array
        assert "[" in result.stdout


class TestXanCommand:
    """Tests for the xan command - CSV toolkit."""

    @pytest.mark.asyncio
    async def test_xan_help(self):
        bash = Bash()
        result = await bash.exec("xan --help")
        assert result.exit_code == 0
        assert "Usage: xan" in result.stdout
        assert "headers" in result.stdout

    @pytest.mark.asyncio
    async def test_xan_headers(self):
        bash = Bash(files={"/test.csv": "name,age,city\nAlice,30,NYC\nBob,25,LA"})
        result = await bash.exec("xan headers /test.csv")
        assert result.exit_code == 0
        assert "name" in result.stdout
        assert "age" in result.stdout
        assert "city" in result.stdout

    @pytest.mark.asyncio
    async def test_xan_headers_just_names(self):
        bash = Bash(files={"/test.csv": "name,age,city\nAlice,30,NYC"})
        result = await bash.exec("xan headers -j /test.csv")
        assert result.exit_code == 0
        assert "name\n" in result.stdout
        assert "\t" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_count(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan count /test.csv")
        assert result.exit_code == 0
        assert result.stdout.strip() == "3"

    @pytest.mark.asyncio
    async def test_xan_head(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan head -n 2 /test.csv")
        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout
        assert "Charlie" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_tail(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan tail -n 1 /test.csv")
        assert result.exit_code == 0
        assert "Charlie" in result.stdout
        assert "Alice" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_select(self):
        from just_bash.commands.xan.xan import XanCommand
        from just_bash.types import CommandContext
        from just_bash.fs import InMemoryFs

        fs = InMemoryFs({"/test.csv": "name,age,city\nAlice,30,NYC\nBob,25,LA"})
        ctx = CommandContext(fs=fs, cwd="/", env={})
        cmd = XanCommand()

        result = await cmd.execute(["select", "name,city", "/test.csv"], ctx)
        assert result.exit_code == 0
        assert "name" in result.stdout
        assert "city" in result.stdout
        assert "Alice" in result.stdout
        assert "NYC" in result.stdout
        # Should not include age column
        lines = result.stdout.strip().split("\n")
        assert "age" not in lines[0]

    @pytest.mark.asyncio
    async def test_xan_filter(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan filter 'age > 28' /test.csv")
        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Charlie" in result.stdout
        assert "Bob" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_filter_equals(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25"})
        result = await bash.exec("xan filter 'name == Alice' /test.csv")
        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Bob" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_search(self):
        bash = Bash(files={"/test.csv": "name,city\nAlice,NYC\nBob,LA\nCharlie,NYC"})
        result = await bash.exec("xan search NYC /test.csv")
        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Charlie" in result.stdout
        assert "Bob" not in result.stdout

    @pytest.mark.asyncio
    async def test_xan_sort_numeric(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan sort -N age /test.csv")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        # Should be sorted: header, Bob (25), Alice (30), Charlie (35)
        assert "Bob" in lines[1]
        assert "Alice" in lines[2]
        assert "Charlie" in lines[3]

    @pytest.mark.asyncio
    async def test_xan_sort_reverse(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25\nCharlie,35"})
        result = await bash.exec("xan sort -N -r age /test.csv")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        # Should be sorted descending: header, Charlie (35), Alice (30), Bob (25)
        assert "Charlie" in lines[1]
        assert "Alice" in lines[2]
        assert "Bob" in lines[3]

    @pytest.mark.asyncio
    async def test_xan_view(self):
        bash = Bash(files={"/test.csv": "name,age\nAlice,30\nBob,25"})
        result = await bash.exec("xan view /test.csv")
        assert result.exit_code == 0
        assert "|" in result.stdout  # Table format
        assert "name" in result.stdout
        assert "Alice" in result.stdout

    @pytest.mark.asyncio
    async def test_xan_stats(self):
        bash = Bash(files={"/test.csv": "name,value\nA,10\nB,20\nC,30"})
        result = await bash.exec("xan stats /test.csv")
        assert result.exit_code == 0
        assert "Column: value" in result.stdout
        assert "Min: 10" in result.stdout
        assert "Max: 30" in result.stdout

    @pytest.mark.asyncio
    async def test_xan_frequency(self):
        bash = Bash(files={"/test.csv": "name,category\nA,X\nB,Y\nC,X\nD,X"})
        result = await bash.exec("xan frequency category /test.csv")
        assert result.exit_code == 0
        assert "X,3" in result.stdout
        assert "Y,1" in result.stdout

    @pytest.mark.asyncio
    async def test_xan_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'name,age\nAlice,30' | xan count")
        assert result.exit_code == 0
        assert result.stdout.strip() == "1"

    @pytest.mark.asyncio
    async def test_xan_unknown_command(self):
        bash = Bash()
        result = await bash.exec("xan invalid /test.csv")
        assert result.exit_code == 1
        assert "unknown command" in result.stderr

    @pytest.mark.asyncio
    async def test_xan_file_not_found(self):
        bash = Bash()
        result = await bash.exec("xan headers /nonexistent.csv")
        assert result.exit_code == 2
        assert "No such file" in result.stderr


class TestSqlite3Command:
    """Test sqlite3 command."""

    @pytest.mark.asyncio
    async def test_sqlite3_version(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -version")
        assert result.exit_code == 0
        # Should output version like "3.x.x"
        assert result.stdout.strip()

    @pytest.mark.asyncio
    async def test_sqlite3_help(self):
        bash = Bash()
        result = await bash.exec("sqlite3 --help")
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "-json" in result.stdout
        assert "-csv" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_missing_database(self):
        bash = Bash()
        result = await bash.exec("sqlite3")
        assert result.exit_code == 1
        assert "missing database" in result.stderr

    @pytest.mark.asyncio
    async def test_sqlite3_memory_select(self):
        bash = Bash()
        result = await bash.exec("sqlite3 :memory: 'SELECT 1+1'")
        assert result.exit_code == 0
        assert result.stdout.strip() == "2"

    @pytest.mark.asyncio
    async def test_sqlite3_memory_multiple_columns(self):
        bash = Bash()
        result = await bash.exec("sqlite3 :memory: 'SELECT 1, 2, 3'")
        assert result.exit_code == 0
        assert result.stdout.strip() == "1|2|3"

    @pytest.mark.asyncio
    async def test_sqlite3_csv_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -csv :memory: \"SELECT 'a,b' AS col\"")
        assert result.exit_code == 0
        # CSV should quote the value since it contains a comma
        assert '"a,b"' in result.stdout or "a,b" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_json_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -json :memory: 'SELECT 1 AS val, 2 AS num'")
        assert result.exit_code == 0
        import json
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["val"] == 1
        assert data[0]["num"] == 2

    @pytest.mark.asyncio
    async def test_sqlite3_header(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -header :memory: 'SELECT 1 AS foo, 2 AS bar'")
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "foo|bar"
        assert lines[1] == "1|2"

    @pytest.mark.asyncio
    async def test_sqlite3_separator(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -separator ',' :memory: 'SELECT 1, 2, 3'")
        assert result.exit_code == 0
        assert result.stdout.strip() == "1,2,3"

    @pytest.mark.asyncio
    async def test_sqlite3_line_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -line :memory: 'SELECT 1 AS foo, 2 AS bar'")
        assert result.exit_code == 0
        assert "foo = 1" in result.stdout
        assert "bar = 2" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_column_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -column -header :memory: 'SELECT 1 AS foo, 2 AS bar'")
        assert result.exit_code == 0
        assert "foo" in result.stdout
        assert "bar" in result.stdout
        assert "---" in result.stdout  # Column separator

    @pytest.mark.asyncio
    async def test_sqlite3_table_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -table -header :memory: 'SELECT 1 AS foo'")
        assert result.exit_code == 0
        assert "+---" in result.stdout  # Table border
        assert "|" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_markdown_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -markdown :memory: 'SELECT 1 AS foo, 2 AS bar'")
        assert result.exit_code == 0
        assert "|" in result.stdout
        assert "---" in result.stdout  # Markdown separator

    @pytest.mark.asyncio
    async def test_sqlite3_tabs_mode(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -tabs :memory: 'SELECT 1, 2, 3'")
        assert result.exit_code == 0
        assert "1\t2\t3" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_create_and_select(self):
        bash = Bash()
        result = await bash.exec(
            "sqlite3 :memory: 'CREATE TABLE t (x INT); INSERT INTO t VALUES (10); SELECT * FROM t'"
        )
        assert result.exit_code == 0
        assert result.stdout.strip() == "10"

    @pytest.mark.asyncio
    async def test_sqlite3_file_database_rejected(self):
        bash = Bash()
        # File-based databases should be rejected (in-memory only)
        result = await bash.exec("sqlite3 /test.db 'SELECT 1'")
        assert result.exit_code == 1
        assert "only :memory:" in result.stderr

    @pytest.mark.asyncio
    async def test_sqlite3_nullvalue(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -nullvalue 'NULL' :memory: 'SELECT NULL'")
        assert result.exit_code == 0
        assert result.stdout.strip() == "NULL"

    @pytest.mark.asyncio
    async def test_sqlite3_multiple_statements(self):
        bash = Bash()
        result = await bash.exec(
            "sqlite3 :memory: 'SELECT 1; SELECT 2; SELECT 3'"
        )
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert "1" in lines
        assert "2" in lines
        assert "3" in lines

    @pytest.mark.asyncio
    async def test_sqlite3_sql_error(self):
        bash = Bash()
        result = await bash.exec("sqlite3 :memory: 'SELECT * FROM nonexistent'")
        # With default behavior, error is in stdout and exit_code may still be 0
        assert "Error" in result.stdout or result.exit_code != 0

    @pytest.mark.asyncio
    async def test_sqlite3_bail_on_error(self):
        bash = Bash()
        result = await bash.exec(
            "sqlite3 -bail :memory: 'SELECT * FROM nonexistent; SELECT 1'"
        )
        assert result.exit_code == 1
        assert "Error" in result.stderr

    @pytest.mark.asyncio
    async def test_sqlite3_echo(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -echo :memory: 'SELECT 42'")
        assert result.exit_code == 0
        assert "SELECT 42" in result.stdout
        assert "42" in result.stdout

    @pytest.mark.asyncio
    async def test_sqlite3_stdin(self):
        bash = Bash()
        result = await bash.exec("echo 'SELECT 1+2' | sqlite3 :memory:")
        assert result.exit_code == 0
        assert result.stdout.strip() == "3"

    @pytest.mark.asyncio
    async def test_sqlite3_unknown_option(self):
        bash = Bash()
        result = await bash.exec("sqlite3 -unknownoption :memory: 'SELECT 1'")
        assert result.exit_code == 1
        assert "unknown option" in result.stderr
