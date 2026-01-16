# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

just-bash-py is a Python port of the just-bash TypeScript library - a pure Python bash interpreter with an in-memory virtual filesystem. Designed for AI agents needing a secure, sandboxed bash environment.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_commands/test_commands.py -v

# Run tests matching pattern
pytest tests/ -v -k "grep"

# Type checking
mypy src/

# Format code
ruff format src/ tests/
ruff check src/ tests/ --fix
```

## Test-Driven Development (TDD)

**CRITICAL: Always write tests FIRST, before implementing features.**

### TDD Workflow

1. **Write a failing test first** - Define the expected behavior before writing any implementation code
2. **Run the test and watch it fail** - Verify the test fails for the right reason
3. **Write minimal code to pass** - Implement just enough to make the test pass
4. **Refactor** - Clean up while keeping tests green
5. **Repeat** - Add more tests for edge cases and additional features

### Test Structure

```python
import pytest
from just_bash import Bash

class TestNewCommand:
    """Test new_command implementation."""

    @pytest.mark.asyncio
    async def test_basic_usage(self):
        bash = Bash(files={"/input.txt": "content"})
        result = await bash.exec("new_command /input.txt")
        assert result.stdout == "expected output\n"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_with_flag(self):
        bash = Bash(files={"/input.txt": "content"})
        result = await bash.exec("new_command -f /input.txt")
        assert result.stdout == "expected with flag\n"

    @pytest.mark.asyncio
    async def test_error_case(self):
        bash = Bash()
        result = await bash.exec("new_command /nonexistent")
        assert "No such file" in result.stderr
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_stdin(self):
        bash = Bash()
        result = await bash.exec("echo input | new_command")
        assert result.stdout == "processed input\n"
```

### Test Guidelines

- **Assert full stdout/stderr** - Don't use partial matches when exact output is known
- **Test error cases** - Always test what happens with invalid input
- **Test stdin** - If the command reads from stdin, test it with pipes
- **Test flags** - Each flag should have at least one test
- **Use descriptive test names** - `test_grep_ignore_case_flag` not `test_grep_2`

## Architecture

### Core Pipeline

```
Input Script → Parser (src/just_bash/parser/) → AST → Interpreter (src/just_bash/interpreter/) → ExecResult
```

### Key Modules

- **Parser** (`src/just_bash/parser/`): Lexer and recursive descent parser
- **Interpreter** (`src/just_bash/interpreter/`): AST execution, expansion, builtins
- **Commands** (`src/just_bash/commands/`): External command implementations
- **Filesystem** (`src/just_bash/fs/`): In-memory virtual filesystem

### Adding Commands

1. **Write tests first** in `tests/test_commands/test_commands.py`
2. Run tests to see them fail
3. Create command in `src/just_bash/commands/<name>/<name>.py`
4. Add to registry in `src/just_bash/commands/registry.py`
5. Run tests to see them pass

Command implementation pattern:
```python
from ...types import CommandContext, ExecResult

class NewCommand:
    """The new_command."""

    name = "new_command"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        # Parse arguments
        # Execute logic using ctx.fs, ctx.stdin, ctx.cwd, ctx.env
        return ExecResult(stdout=output, stderr=errors, exit_code=code)
```

## File Locations

- Commands: `src/just_bash/commands/<name>/<name>.py`
- Command registry: `src/just_bash/commands/registry.py`
- Tests: `tests/test_commands/test_commands.py`
- Parser: `src/just_bash/parser/`
- Interpreter: `src/just_bash/interpreter/`
- Types: `src/just_bash/types.py`

## Development Guidelines

- **TDD first** - Write tests before implementation
- Match real bash behavior, not convenience
- Keep implementations simple and focused
- Use `ctx.fs` for all filesystem operations
- Handle errors gracefully with appropriate exit codes
- Verify with `pytest tests/ -v` before finishing

## Known Issues

1. **Single-quote variable expansion** - Variables like `$0` are expanded even in single quotes. Workaround: use `-f` to load scripts from files, or escape with `\$`.
