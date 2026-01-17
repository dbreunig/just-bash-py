"""Test / [ builtin implementation.

The test command evaluates conditional expressions and returns
exit code 0 (true) or 1 (false).

Usage: test expression
       [ expression ]

File operators:
  -f FILE     True if FILE exists and is a regular file
  -d FILE     True if FILE exists and is a directory
  -e FILE     True if FILE exists
  -s FILE     True if FILE exists and has size > 0
  -r FILE     True if FILE exists and is readable
  -w FILE     True if FILE exists and is writable
  -x FILE     True if FILE exists and is executable
  -h/-L FILE  True if FILE exists and is a symbolic link

String operators:
  -z STRING   True if STRING is empty
  -n STRING   True if STRING is not empty
  STRING      True if STRING is not empty
  S1 = S2     True if strings are equal
  S1 != S2    True if strings are not equal
  S1 < S2     True if S1 sorts before S2
  S1 > S2     True if S1 sorts after S2

Numeric operators:
  N1 -eq N2   True if N1 equals N2
  N1 -ne N2   True if N1 does not equal N2
  N1 -lt N2   True if N1 is less than N2
  N1 -le N2   True if N1 is less or equal to N2
  N1 -gt N2   True if N1 is greater than N2
  N1 -ge N2   True if N1 is greater or equal to N2

Logical operators:
  ! EXPR      True if EXPR is false
  ( EXPR )    Grouping
  EXPR -a EXPR  True if both EXPRs are true (AND)
  EXPR -o EXPR  True if either EXPR is true (OR)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import InterpreterContext
    from ...types import ExecResult


# Known unary operators that require an operand
_UNARY_OPS = {
    "-f", "-d", "-e", "-s", "-r", "-w", "-x", "-h", "-L",
    "-z", "-n", "-b", "-c", "-g", "-G", "-k", "-O", "-p",
    "-S", "-t", "-u", "-N", "-v", "-o",
}


async def handle_test(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the test builtin."""
    from ...types import ExecResult

    # Empty test is false
    if not args:
        return ExecResult(stdout="", stderr="", exit_code=1)

    try:
        result = await _evaluate(ctx, args)
        return ExecResult(stdout="", stderr="", exit_code=0 if result else 1)
    except ValueError as e:
        return ExecResult(stdout="", stderr=f"bash: test: {e}\n", exit_code=2)


async def handle_bracket(ctx: "InterpreterContext", args: list[str]) -> "ExecResult":
    """Execute the [ builtin (requires closing ])."""
    from ...types import ExecResult

    # [ requires closing ]
    if not args or args[-1] != "]":
        return ExecResult(stdout="", stderr="bash: [: missing `]'\n", exit_code=2)
    args = args[:-1]

    # Empty test is false
    if not args:
        return ExecResult(stdout="", stderr="", exit_code=1)

    try:
        result = await _evaluate(ctx, args)
        return ExecResult(stdout="", stderr="", exit_code=0 if result else 1)
    except ValueError as e:
        return ExecResult(stdout="", stderr=f"bash: [: {e}\n", exit_code=2)


async def _evaluate(ctx: "InterpreterContext", args: list[str]) -> bool:
    """Evaluate a test expression."""
    if not args:
        return False

    # Handle negation
    if args[0] == "!":
        return not await _evaluate(ctx, args[1:])

    # Handle parentheses
    if args[0] == "(":
        # Find matching )
        depth = 1
        end_idx = 1
        while end_idx < len(args) and depth > 0:
            if args[end_idx] == "(":
                depth += 1
            elif args[end_idx] == ")":
                depth -= 1
            end_idx += 1

        if depth != 0:
            raise ValueError("missing ')'")

        inner_result = await _evaluate(ctx, args[1:end_idx - 1])

        # Check for -a or -o after the parentheses
        if end_idx < len(args):
            return await _evaluate_compound(ctx, inner_result, args[end_idx:])

        return inner_result

    # Handle -a and -o (lowest precedence)
    for i, arg in enumerate(args):
        if arg == "-a" and i > 0:
            left = await _evaluate(ctx, args[:i])
            right = await _evaluate(ctx, args[i + 1:])
            return left and right
        if arg == "-o" and i > 0:
            left = await _evaluate(ctx, args[:i])
            right = await _evaluate(ctx, args[i + 1:])
            return left or right

    # Single argument: non-empty string is true, but check for misused operators
    if len(args) == 1:
        arg = args[0]
        # If it looks like an operator (starts with -) but isn't followed by
        # an operand, it could be a misused unary operator
        if arg.startswith("-") and len(arg) > 1:
            # Check if this looks like an operator that needs an operand
            if arg in _UNARY_OPS:
                raise ValueError(f"{arg}: unary operator expected")
        return arg != ""

    # Two arguments: unary operators
    if len(args) == 2:
        return await _unary_test(ctx, args[0], args[1])

    # Three arguments: binary operators
    if len(args) == 3:
        return await _binary_test(ctx, args[0], args[1], args[2])

    # More than 3 args should be handled by -a/-o above
    raise ValueError("too many arguments")


async def _evaluate_compound(
    ctx: "InterpreterContext", left_result: bool, remaining: list[str]
) -> bool:
    """Evaluate compound expression with -a or -o."""
    if not remaining:
        return left_result

    op = remaining[0]
    rest = remaining[1:]

    if op == "-a":
        if not left_result:
            return False
        return await _evaluate(ctx, rest)
    elif op == "-o":
        if left_result:
            return True
        return await _evaluate(ctx, rest)
    else:
        raise ValueError(f"unexpected '{op}'")


async def _unary_test(ctx: "InterpreterContext", op: str, arg: str) -> bool:
    """Evaluate a unary test."""
    # File tests
    if op == "-f":
        return await _file_test(ctx, arg, "file")
    if op == "-d":
        return await _file_test(ctx, arg, "directory")
    if op == "-e":
        return await _file_test(ctx, arg, "exists")
    if op == "-s":
        return await _file_test(ctx, arg, "size")
    if op == "-r":
        return await _file_test(ctx, arg, "readable")
    if op == "-w":
        return await _file_test(ctx, arg, "writable")
    if op == "-x":
        return await _file_test(ctx, arg, "executable")
    if op in ("-h", "-L"):
        return await _file_test(ctx, arg, "symlink")

    # String tests
    if op == "-z":
        return arg == ""
    if op == "-n":
        return arg != ""

    # Default: two non-operator args means binary comparison
    raise ValueError(f"unknown unary operator '{op}'")


async def _binary_test(
    ctx: "InterpreterContext", left: str, op: str, right: str
) -> bool:
    """Evaluate a binary test."""
    # String comparisons
    if op == "=":
        return left == right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "<":
        return left < right
    if op == ">":
        return left > right

    # Numeric comparisons
    if op in ("-eq", "-ne", "-lt", "-le", "-gt", "-ge"):
        try:
            left_num = int(left)
            right_num = int(right)
        except ValueError:
            raise ValueError(f"integer expression expected")

        if op == "-eq":
            return left_num == right_num
        if op == "-ne":
            return left_num != right_num
        if op == "-lt":
            return left_num < right_num
        if op == "-le":
            return left_num <= right_num
        if op == "-gt":
            return left_num > right_num
        if op == "-ge":
            return left_num >= right_num

    raise ValueError(f"unknown binary operator '{op}'")


async def _file_test(ctx: "InterpreterContext", path: str, test_type: str) -> bool:
    """Perform a file test."""
    # Resolve path relative to cwd
    full_path = ctx.fs.resolve_path(ctx.state.cwd, path)

    try:
        # For symlink test, use lstat (doesn't follow symlinks)
        if test_type == "symlink":
            try:
                stat_info = await ctx.fs.lstat(full_path)
                return stat_info.is_symbolic_link
            except FileNotFoundError:
                return False

        exists = await ctx.fs.exists(full_path)

        if test_type == "exists":
            return exists

        if not exists:
            return False

        if test_type == "directory":
            return await ctx.fs.is_directory(full_path)

        if test_type == "file":
            return not await ctx.fs.is_directory(full_path)

        if test_type == "size":
            content = await ctx.fs.read_file(full_path)
            return len(content) > 0

        # For readable/writable/executable, we assume true if exists
        # (virtual filesystem doesn't track permissions)
        if test_type in ("readable", "writable", "executable"):
            return exists

        return False
    except Exception:
        return False
