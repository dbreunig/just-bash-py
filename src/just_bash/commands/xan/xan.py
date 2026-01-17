"""Xan command implementation - CSV toolkit.

Usage: xan <COMMAND> [OPTIONS] [FILE]

Commands:
  headers    Show column names
  count      Count rows
  head       Show first N rows
  tail       Show last N rows
  slice      Extract row range
  select     Select columns
  filter     Filter rows by expression
  search     Filter rows by regex
  sort       Sort rows
  view       Pretty print as table
  stats      Show column statistics
  frequency  Count value occurrences
"""

import csv
import io
import re
from typing import Any

from ...types import CommandContext, ExecResult


def parse_csv(content: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV content into headers and data rows."""
    if not content.strip():
        return [], []

    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []
    data = list(reader)
    return list(headers), data


def format_csv(headers: list[str], data: list[dict[str, Any]]) -> str:
    """Format data as CSV."""
    if not headers:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in data:
        writer.writerow({h: row.get(h, "") for h in headers})
    return output.getvalue()


def format_value(v: Any) -> str:
    """Format a value for CSV output."""
    if v is None:
        return ""
    s = str(v)
    if "," in s or '"' in s or "\n" in s:
        escaped = s.replace('"', '""')
        return f'"{escaped}"'
    return s


async def read_csv_input(
    file_args: list[str], ctx: CommandContext
) -> tuple[list[str], list[dict[str, str]], ExecResult | None]:
    """Read CSV from file or stdin."""
    if not file_args or file_args[0] == "-":
        content = ctx.stdin
    else:
        try:
            path = ctx.fs.resolve_path(ctx.cwd, file_args[0])
            content = await ctx.fs.read_file(path)
        except FileNotFoundError:
            return [], [], ExecResult(
                stdout="",
                stderr=f"xan: {file_args[0]}: No such file or directory\n",
                exit_code=2,
            )

    headers, data = parse_csv(content)
    return headers, data, None


async def cmd_headers(args: list[str], ctx: CommandContext) -> ExecResult:
    """Show column names."""
    just_names = "-j" in args or "--just-names" in args
    file_args = [a for a in args if not a.startswith("-")]

    headers, _, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    if just_names:
        output = "\n".join(headers) + "\n" if headers else ""
    else:
        output = "\n".join(f"{i}\t{h}" for i, h in enumerate(headers)) + "\n" if headers else ""

    return ExecResult(stdout=output, stderr="", exit_code=0)


async def cmd_count(args: list[str], ctx: CommandContext) -> ExecResult:
    """Count rows."""
    file_args = [a for a in args if not a.startswith("-")]

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    return ExecResult(stdout=f"{len(data)}\n", stderr="", exit_code=0)


async def cmd_head(args: list[str], ctx: CommandContext) -> ExecResult:
    """Show first N rows."""
    n = 10
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-n" and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        elif arg.startswith("-n"):
            try:
                n = int(arg[2:])
            except ValueError:
                pass
        elif not arg.startswith("-"):
            file_args.append(arg)
        i += 1

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    return ExecResult(stdout=format_csv(headers, data[:n]), stderr="", exit_code=0)


async def cmd_tail(args: list[str], ctx: CommandContext) -> ExecResult:
    """Show last N rows."""
    n = 10
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-n" and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        elif arg.startswith("-n"):
            try:
                n = int(arg[2:])
            except ValueError:
                pass
        elif not arg.startswith("-"):
            file_args.append(arg)
        i += 1

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    return ExecResult(stdout=format_csv(headers, data[-n:]), stderr="", exit_code=0)


async def cmd_slice(args: list[str], ctx: CommandContext) -> ExecResult:
    """Extract row range."""
    start = 0
    end = None
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-s" or arg == "--start":
            if i + 1 < len(args):
                try:
                    start = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
        elif arg == "-e" or arg == "--end":
            if i + 1 < len(args):
                try:
                    end = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
        elif not arg.startswith("-"):
            file_args.append(arg)
        i += 1

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    return ExecResult(stdout=format_csv(headers, data[start:end]), stderr="", exit_code=0)


async def cmd_select(args: list[str], ctx: CommandContext) -> ExecResult:
    """Select columns."""
    cols_spec = ""
    file_args = []

    for arg in args:
        if not arg.startswith("-"):
            if not cols_spec:
                cols_spec = arg
            else:
                file_args.append(arg)

    if not cols_spec:
        return ExecResult(
            stdout="",
            stderr="xan select: no columns specified\n",
            exit_code=1,
        )

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    # Parse column specification (comma-separated names or indices)
    selected_headers = []
    for col in cols_spec.split(","):
        col = col.strip()
        if not col:
            continue

        # Check if it's an index
        try:
            idx = int(col)
            if 0 <= idx < len(headers):
                selected_headers.append(headers[idx])
            continue
        except ValueError:
            pass

        # Check for glob pattern
        if "*" in col:
            pattern = col.replace("*", ".*")
            for h in headers:
                if re.match(f"^{pattern}$", h) and h not in selected_headers:
                    selected_headers.append(h)
            continue

        # Direct column name
        if col in headers:
            selected_headers.append(col)

    # Filter data to selected columns
    selected_data = []
    for row in data:
        selected_data.append({h: row.get(h, "") for h in selected_headers})

    return ExecResult(stdout=format_csv(selected_headers, selected_data), stderr="", exit_code=0)


async def cmd_filter(args: list[str], ctx: CommandContext) -> ExecResult:
    """Filter rows by expression."""
    expr = ""
    invert = False
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-v", "--invert"):
            invert = True
        elif not arg.startswith("-"):
            if not expr:
                expr = arg
            else:
                file_args.append(arg)
        i += 1

    if not expr:
        return ExecResult(
            stdout="",
            stderr="xan filter: no expression specified\n",
            exit_code=1,
        )

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    # Parse simple expressions: col op value
    # Supported: ==, !=, <, <=, >, >=, contains, startswith, endswith
    filtered = []
    for row in data:
        match = evaluate_filter_expr(expr, row)
        if (match and not invert) or (not match and invert):
            filtered.append(row)

    return ExecResult(stdout=format_csv(headers, filtered), stderr="", exit_code=0)


def evaluate_filter_expr(expr: str, row: dict[str, str]) -> bool:
    """Evaluate a filter expression against a row."""
    expr = expr.strip()

    # Try different operators
    for op, op_func in [
        ("==", lambda a, b: str(a) == str(b)),
        ("!=", lambda a, b: str(a) != str(b)),
        (">=", lambda a, b: try_compare(a, b, "ge")),
        ("<=", lambda a, b: try_compare(a, b, "le")),
        (">", lambda a, b: try_compare(a, b, "gt")),
        ("<", lambda a, b: try_compare(a, b, "lt")),
    ]:
        if f" {op} " in expr:
            parts = expr.split(f" {op} ", 1)
            col = parts[0].strip()
            val = parts[1].strip().strip('"').strip("'")
            if col in row:
                return op_func(row[col], val)
            return False

    # Check for function-style expressions
    if "contains(" in expr.lower():
        match = re.match(r"(\w+)\s+contains\s*\(([^)]+)\)", expr, re.IGNORECASE)
        if match:
            col, val = match.groups()
            val = val.strip('"').strip("'")
            if col in row:
                return val in str(row[col])
        return False

    if "startswith(" in expr.lower():
        match = re.match(r"(\w+)\s+startswith\s*\(([^)]+)\)", expr, re.IGNORECASE)
        if match:
            col, val = match.groups()
            val = val.strip('"').strip("'")
            if col in row:
                return str(row[col]).startswith(val)
        return False

    if "endswith(" in expr.lower():
        match = re.match(r"(\w+)\s+endswith\s*\(([^)]+)\)", expr, re.IGNORECASE)
        if match:
            col, val = match.groups()
            val = val.strip('"').strip("'")
            if col in row:
                return str(row[col]).endswith(val)
        return False

    return False


def try_compare(a: str, b: str, op: str) -> bool:
    """Try to compare values, first as numbers, then as strings."""
    try:
        a_num = float(a) if a else 0
        b_num = float(b) if b else 0
        if op == "gt":
            return a_num > b_num
        elif op == "ge":
            return a_num >= b_num
        elif op == "lt":
            return a_num < b_num
        elif op == "le":
            return a_num <= b_num
    except ValueError:
        pass

    if op == "gt":
        return str(a) > str(b)
    elif op == "ge":
        return str(a) >= str(b)
    elif op == "lt":
        return str(a) < str(b)
    elif op == "le":
        return str(a) <= str(b)
    return False


async def cmd_search(args: list[str], ctx: CommandContext) -> ExecResult:
    """Filter rows by regex."""
    pattern = ""
    select_cols: list[str] = []
    invert = False
    ignore_case = False
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-s", "--select") and i + 1 < len(args):
            select_cols = args[i + 1].split(",")
            i += 2
            continue
        elif arg in ("-v", "--invert"):
            invert = True
        elif arg in ("-i", "--ignore-case"):
            ignore_case = True
        elif not arg.startswith("-"):
            if not pattern:
                pattern = arg
            else:
                file_args.append(arg)
        i += 1

    if not pattern:
        return ExecResult(
            stdout="",
            stderr="xan search: no pattern specified\n",
            exit_code=1,
        )

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    search_cols = select_cols if select_cols else headers

    try:
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error:
        return ExecResult(
            stdout="",
            stderr=f"xan search: invalid regex pattern '{pattern}'\n",
            exit_code=1,
        )

    filtered = []
    for row in data:
        matches = any(
            regex.search(str(row.get(col, "")))
            for col in search_cols
            if col in row
        )
        if (matches and not invert) or (not matches and invert):
            filtered.append(row)

    return ExecResult(stdout=format_csv(headers, filtered), stderr="", exit_code=0)


async def cmd_sort(args: list[str], ctx: CommandContext) -> ExecResult:
    """Sort rows."""
    sort_col = ""
    numeric = False
    reverse = False
    file_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-N", "--numeric"):
            numeric = True
        elif arg in ("-r", "--reverse", "-R"):
            reverse = True
        elif arg in ("-s", "--select") and i + 1 < len(args):
            sort_col = args[i + 1]
            i += 2
            continue
        elif not arg.startswith("-"):
            if not sort_col:
                sort_col = arg
            else:
                file_args.append(arg)
        i += 1

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    if not sort_col:
        return ExecResult(
            stdout="",
            stderr="xan sort: no sort column specified\n",
            exit_code=1,
        )

    if sort_col not in headers:
        return ExecResult(
            stdout="",
            stderr=f"xan sort: column '{sort_col}' not found\n",
            exit_code=1,
        )

    def sort_key(row: dict) -> Any:
        val = row.get(sort_col, "")
        if numeric:
            try:
                return float(val) if val else 0
            except ValueError:
                return 0
        return str(val)

    sorted_data = sorted(data, key=sort_key, reverse=reverse)
    return ExecResult(stdout=format_csv(headers, sorted_data), stderr="", exit_code=0)


async def cmd_view(args: list[str], ctx: CommandContext) -> ExecResult:
    """Pretty print as table."""
    file_args = [a for a in args if not a.startswith("-")]

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    if not headers:
        return ExecResult(stdout="", stderr="", exit_code=0)

    # Calculate column widths
    widths = {h: len(h) for h in headers}
    for row in data:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h, ""))))

    # Build table
    lines = []

    # Header
    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    lines.append(header_line)

    # Separator
    sep_line = "-+-".join("-" * widths[h] for h in headers)
    lines.append(sep_line)

    # Data rows
    for row in data:
        row_line = " | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers)
        lines.append(row_line)

    return ExecResult(stdout="\n".join(lines) + "\n", stderr="", exit_code=0)


async def cmd_stats(args: list[str], ctx: CommandContext) -> ExecResult:
    """Show column statistics."""
    file_args = [a for a in args if not a.startswith("-")]

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    if not headers:
        return ExecResult(stdout="", stderr="", exit_code=0)

    lines = []
    for col in headers:
        values = [row.get(col, "") for row in data]
        non_empty = [v for v in values if v]

        # Try to parse as numbers
        nums = []
        for v in non_empty:
            try:
                nums.append(float(v))
            except ValueError:
                pass

        lines.append(f"Column: {col}")
        lines.append(f"  Count: {len(values)}")
        lines.append(f"  Non-empty: {len(non_empty)}")
        lines.append(f"  Unique: {len(set(non_empty))}")

        if nums:
            lines.append(f"  Min: {min(nums)}")
            lines.append(f"  Max: {max(nums)}")
            lines.append(f"  Sum: {sum(nums)}")
            lines.append(f"  Mean: {sum(nums) / len(nums):.2f}")

        lines.append("")

    return ExecResult(stdout="\n".join(lines), stderr="", exit_code=0)


async def cmd_frequency(args: list[str], ctx: CommandContext) -> ExecResult:
    """Count value occurrences."""
    col = ""
    file_args = []

    for arg in args:
        if not arg.startswith("-"):
            if not col:
                col = arg
            else:
                file_args.append(arg)

    headers, data, error = await read_csv_input(file_args, ctx)
    if error:
        return error

    if not col:
        # Default to first column
        col = headers[0] if headers else ""

    if col not in headers:
        return ExecResult(
            stdout="",
            stderr=f"xan frequency: column '{col}' not found\n",
            exit_code=1,
        )

    # Count occurrences
    counts: dict[str, int] = {}
    for row in data:
        val = str(row.get(col, ""))
        counts[val] = counts.get(val, 0) + 1

    # Sort by count descending
    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])

    # Output as CSV
    output = "value,count\n"
    for val, count in sorted_counts:
        output += f"{format_value(val)},{count}\n"

    return ExecResult(stdout=output, stderr="", exit_code=0)


class XanCommand:
    """The xan command - CSV toolkit."""

    name = "xan"

    async def execute(self, args: list[str], ctx: CommandContext) -> ExecResult:
        """Execute the xan command."""
        if not args or "--help" in args or "-h" in args:
            return ExecResult(
                stdout=(
                    "Usage: xan <COMMAND> [OPTIONS] [FILE]\n"
                    "CSV toolkit for data manipulation.\n\n"
                    "Commands:\n"
                    "  headers    Show column names\n"
                    "  count      Count rows\n"
                    "  head       Show first N rows\n"
                    "  tail       Show last N rows\n"
                    "  slice      Extract row range\n"
                    "  select     Select columns\n"
                    "  filter     Filter rows by expression\n"
                    "  search     Filter rows by regex\n"
                    "  sort       Sort rows\n"
                    "  view       Pretty print as table\n"
                    "  stats      Show column statistics\n"
                    "  frequency  Count value occurrences\n\n"
                    "Examples:\n"
                    "  xan headers data.csv\n"
                    "  xan count data.csv\n"
                    "  xan head -n 5 data.csv\n"
                    "  xan select name,email data.csv\n"
                    "  xan filter 'age > 30' data.csv\n"
                    "  xan sort -N price data.csv\n"
                ),
                stderr="",
                exit_code=0,
            )

        subcommand = args[0]
        sub_args = args[1:]

        if subcommand == "headers":
            return await cmd_headers(sub_args, ctx)
        elif subcommand == "count":
            return await cmd_count(sub_args, ctx)
        elif subcommand == "head":
            return await cmd_head(sub_args, ctx)
        elif subcommand == "tail":
            return await cmd_tail(sub_args, ctx)
        elif subcommand == "slice":
            return await cmd_slice(sub_args, ctx)
        elif subcommand == "select":
            return await cmd_select(sub_args, ctx)
        elif subcommand == "filter":
            return await cmd_filter(sub_args, ctx)
        elif subcommand == "search":
            return await cmd_search(sub_args, ctx)
        elif subcommand == "sort":
            return await cmd_sort(sub_args, ctx)
        elif subcommand == "view":
            return await cmd_view(sub_args, ctx)
        elif subcommand == "stats":
            return await cmd_stats(sub_args, ctx)
        elif subcommand in ("frequency", "freq"):
            return await cmd_frequency(sub_args, ctx)
        else:
            return ExecResult(
                stdout="",
                stderr=f"xan: unknown command '{subcommand}'\nRun 'xan --help' for usage.\n",
                exit_code=1,
            )
