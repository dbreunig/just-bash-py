#!/usr/bin/env python3
"""Demonstration of all text processing commands in just-bash-py.

This script showcases every text processing command available:
awk, column, comm, cut, diff, expand, fold, grep, egrep, fgrep,
head, join, nl, od, paste, rev, rg, sed, sort, split, strings,
tac, tail, tee, tr, unexpand, uniq, wc
"""

from just_bash import Bash


def demo(bash: Bash, title: str, command: str) -> None:
    """Run a command and display the results."""
    print(f"\n{'='*60}")
    print(f"## {title}")
    print(f"{'='*60}")
    print(f"$ {command}")
    print("-" * 40)
    result = bash.run(command)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(f"[stderr] {result.stderr}", end="")
    if result.exit_code != 0:
        print(f"[exit code: {result.exit_code}]")


def main():
    print("=" * 60)
    print("  TEXT PROCESSING COMMANDS DEMO")
    print("  just-bash-py")
    print("=" * 60)

    # Create bash instance with sample files
    bash = Bash(files={
        "/data/fruits.txt": "banana\napple\ncherry\napple\ndate\nbanana\nelderberry\n",
        "/data/numbers.txt": "3\n1\n4\n1\n5\n9\n2\n6\n",
        "/data/csv.txt": "name,age,city\nalice,30,new york\nbob,25,los angeles\ncharlie,35,chicago\n",
        "/data/tabs.txt": "col1\tcol2\tcol3\nval1\tval2\tval3\n",
        "/data/file1.txt": "apple\nbanana\ncherry\n",
        "/data/file2.txt": "banana\ncherry\ndate\n",
        "/data/left.txt": "1 alice\n2 bob\n3 charlie\n",
        "/data/right.txt": "1 engineer\n2 designer\n3 manager\n",
        "/data/mixed.txt": "Hello World\n\x00binary\x00data\nMore Text\n",
        "/data/spaces.txt": "    indented line\n        double indent\nnormal line\n",
        "/data/long.txt": "This is a very long line that should be folded when we use the fold command to wrap it at a specific width.\n",
        "/data/poem.txt": "Roses are red\nViolets are blue\nSugar is sweet\nAnd so are you\n",
    })

    # =========================================================================
    # GREP FAMILY
    # =========================================================================
    print("\n" + "=" * 60)
    print("  GREP FAMILY - Pattern Matching")
    print("=" * 60)

    demo(bash, "grep - Basic pattern matching",
         "grep apple /data/fruits.txt")

    demo(bash, "grep -i - Case insensitive",
         "echo -e 'Apple\\nBANANA\\ncherry' | grep -i apple")

    demo(bash, "grep -v - Invert match",
         "grep -v apple /data/fruits.txt")

    demo(bash, "grep -c - Count matches",
         "grep -c apple /data/fruits.txt")

    demo(bash, "grep -n - Show line numbers",
         "grep -n a /data/fruits.txt")

    demo(bash, "grep -E (egrep) - Extended regex",
         "grep -E 'apple|cherry' /data/fruits.txt")

    demo(bash, "egrep - Extended regex (alias)",
         "egrep '^[ab]' /data/fruits.txt")

    demo(bash, "fgrep - Fixed string matching",
         "fgrep 'apple' /data/fruits.txt")

    demo(bash, "rg (ripgrep) - Fast grep alternative",
         "rg apple /data/fruits.txt")

    # =========================================================================
    # SED - Stream Editor
    # =========================================================================
    print("\n" + "=" * 60)
    print("  SED - Stream Editor")
    print("=" * 60)

    demo(bash, "sed - Basic substitution",
         "echo 'hello world' | sed 's/world/universe/'")

    demo(bash, "sed - Global substitution",
         "echo 'apple apple apple' | sed 's/apple/orange/g'")

    demo(bash, "sed - Delete lines matching pattern",
         "sed '/apple/d' /data/fruits.txt")

    demo(bash, "sed - Print specific line",
         "sed -n '3p' /data/fruits.txt")

    demo(bash, "sed - Multiple commands",
         "echo 'hello world' | sed -e 's/hello/hi/' -e 's/world/there/'")

    # =========================================================================
    # AWK - Pattern Scanning
    # =========================================================================
    print("\n" + "=" * 60)
    print("  AWK - Pattern Scanning and Processing")
    print("=" * 60)

    demo(bash, "awk - Print specific field",
         "echo 'alice 30 engineer' | awk '{print $1}'")

    demo(bash, "awk - Print multiple fields",
         "echo 'alice 30 engineer' | awk '{print $1, $3}'")

    demo(bash, "awk - Custom field separator",
         "awk -F, '{print $1, $2}' /data/csv.txt")

    demo(bash, "awk - Pattern matching",
         "awk '/apple/' /data/fruits.txt")

    demo(bash, "awk - Arithmetic",
         "echo '10 20 30' | awk '{print $1 + $2 + $3}'")

    demo(bash, "awk - Built-in variables (NR, NF)",
         "awk '{print \"Line\", NR, \"has\", NF, \"fields\"}' /data/csv.txt")

    demo(bash, "awk - BEGIN and END blocks",
         "awk 'BEGIN {sum=0} {sum+=$1} END {print \"Sum:\", sum}' /data/numbers.txt")

    # =========================================================================
    # CUT - Remove Sections
    # =========================================================================
    print("\n" + "=" * 60)
    print("  CUT - Remove Sections from Lines")
    print("=" * 60)

    demo(bash, "cut -c - Select characters",
         "echo 'hello world' | cut -c1-5")

    demo(bash, "cut -d -f - Select fields with delimiter",
         "cut -d, -f1,3 /data/csv.txt")

    demo(bash, "cut - Select field range",
         "echo 'a:b:c:d:e' | cut -d: -f2-4")

    # =========================================================================
    # TR - Translate Characters
    # =========================================================================
    print("\n" + "=" * 60)
    print("  TR - Translate or Delete Characters")
    print("=" * 60)

    demo(bash, "tr - Basic translation",
         "echo 'hello' | tr 'aeiou' 'AEIOU'")

    demo(bash, "tr - Uppercase to lowercase",
         "echo 'HELLO WORLD' | tr 'A-Z' 'a-z'")

    demo(bash, "tr -d - Delete characters",
         "echo 'hello 123 world' | tr -d '0-9'")

    demo(bash, "tr -s - Squeeze repeats",
         "echo 'hellooooo    world' | tr -s 'o '")

    demo(bash, "tr - Replace newlines with spaces",
         "cat /data/fruits.txt | tr '\\n' ' '")

    # =========================================================================
    # SORT - Sort Lines
    # =========================================================================
    print("\n" + "=" * 60)
    print("  SORT - Sort Lines of Text")
    print("=" * 60)

    demo(bash, "sort - Basic alphabetical sort",
         "sort /data/fruits.txt")

    demo(bash, "sort -n - Numeric sort",
         "sort -n /data/numbers.txt")

    demo(bash, "sort -r - Reverse sort",
         "sort -r /data/fruits.txt")

    demo(bash, "sort -u - Unique sort",
         "sort -u /data/fruits.txt")

    demo(bash, "sort -t -k - Sort by field",
         "sort -t, -k2 -n /data/csv.txt")

    # =========================================================================
    # UNIQ - Report or Omit Repeated Lines
    # =========================================================================
    print("\n" + "=" * 60)
    print("  UNIQ - Report or Omit Repeated Lines")
    print("=" * 60)

    demo(bash, "uniq - Remove adjacent duplicates",
         "sort /data/fruits.txt | uniq")

    demo(bash, "uniq -c - Count occurrences",
         "sort /data/fruits.txt | uniq -c")

    demo(bash, "uniq -d - Only show duplicates",
         "sort /data/fruits.txt | uniq -d")

    demo(bash, "uniq -u - Only show unique lines",
         "sort /data/fruits.txt | uniq -u")

    # =========================================================================
    # HEAD and TAIL
    # =========================================================================
    print("\n" + "=" * 60)
    print("  HEAD and TAIL - Output Parts of Files")
    print("=" * 60)

    demo(bash, "head - First 3 lines",
         "head -n 3 /data/fruits.txt")

    demo(bash, "head -c - First 10 bytes",
         "head -c 10 /data/fruits.txt")

    demo(bash, "tail - Last 3 lines",
         "tail -n 3 /data/fruits.txt")

    demo(bash, "tail -c - Last 10 bytes",
         "tail -c 10 /data/fruits.txt")

    # =========================================================================
    # WC - Word, Line, Character Count
    # =========================================================================
    print("\n" + "=" * 60)
    print("  WC - Word, Line, Character Count")
    print("=" * 60)

    demo(bash, "wc - Full count (lines, words, bytes)",
         "wc /data/fruits.txt")

    demo(bash, "wc -l - Line count only",
         "wc -l /data/fruits.txt")

    demo(bash, "wc -w - Word count only",
         "wc -w /data/fruits.txt")

    demo(bash, "wc -c - Byte count only",
         "wc -c /data/fruits.txt")

    # =========================================================================
    # COMM - Compare Sorted Files
    # =========================================================================
    print("\n" + "=" * 60)
    print("  COMM - Compare Sorted Files Line by Line")
    print("=" * 60)

    demo(bash, "comm - All three columns",
         "comm /data/file1.txt /data/file2.txt")

    demo(bash, "comm -12 - Only lines in both files",
         "comm -12 /data/file1.txt /data/file2.txt")

    demo(bash, "comm -23 - Only lines unique to file1",
         "comm -23 /data/file1.txt /data/file2.txt")

    # =========================================================================
    # DIFF - Compare Files
    # =========================================================================
    print("\n" + "=" * 60)
    print("  DIFF - Compare Files Line by Line")
    print("=" * 60)

    demo(bash, "diff - Show differences",
         "diff /data/file1.txt /data/file2.txt")

    demo(bash, "diff -u - Unified format",
         "diff -u /data/file1.txt /data/file2.txt")

    # =========================================================================
    # JOIN - Join Lines on Common Field
    # =========================================================================
    print("\n" + "=" * 60)
    print("  JOIN - Join Lines of Two Files on Common Field")
    print("=" * 60)

    demo(bash, "join - Join on first field",
         "join /data/left.txt /data/right.txt")

    # =========================================================================
    # PASTE - Merge Lines of Files
    # =========================================================================
    print("\n" + "=" * 60)
    print("  PASTE - Merge Lines of Files")
    print("=" * 60)

    demo(bash, "paste - Merge files side by side",
         "paste /data/file1.txt /data/file2.txt")

    demo(bash, "paste -d - Custom delimiter",
         "paste -d, /data/file1.txt /data/file2.txt")

    demo(bash, "paste -s - Serial (transpose)",
         "paste -s /data/fruits.txt")

    # =========================================================================
    # COLUMN - Format into Columns
    # =========================================================================
    print("\n" + "=" * 60)
    print("  COLUMN - Columnate Lists")
    print("=" * 60)

    demo(bash, "column -t - Create table from delimited data",
         "column -t -s, /data/csv.txt")

    # =========================================================================
    # NL - Number Lines
    # =========================================================================
    print("\n" + "=" * 60)
    print("  NL - Number Lines of Files")
    print("=" * 60)

    demo(bash, "nl - Number all lines",
         "nl /data/fruits.txt")

    demo(bash, "nl -ba - Number including blank lines",
         "echo -e 'line1\\n\\nline3' | nl -ba")

    # =========================================================================
    # FOLD - Wrap Lines
    # =========================================================================
    print("\n" + "=" * 60)
    print("  FOLD - Wrap Lines to Specified Width")
    print("=" * 60)

    demo(bash, "fold -w - Wrap at width",
         "fold -w 40 /data/long.txt")

    demo(bash, "fold -s - Wrap at spaces",
         "fold -w 40 -s /data/long.txt")

    # =========================================================================
    # REV - Reverse Lines
    # =========================================================================
    print("\n" + "=" * 60)
    print("  REV - Reverse Lines Character-wise")
    print("=" * 60)

    demo(bash, "rev - Reverse each line",
         "echo 'hello world' | rev")

    demo(bash, "rev - Reverse file lines",
         "rev /data/file1.txt")

    # =========================================================================
    # TAC - Reverse File
    # =========================================================================
    print("\n" + "=" * 60)
    print("  TAC - Concatenate and Print Files in Reverse")
    print("=" * 60)

    demo(bash, "tac - Reverse line order",
         "tac /data/file1.txt")

    # =========================================================================
    # EXPAND and UNEXPAND
    # =========================================================================
    print("\n" + "=" * 60)
    print("  EXPAND/UNEXPAND - Convert Tabs and Spaces")
    print("=" * 60)

    demo(bash, "expand - Convert tabs to spaces",
         "expand /data/tabs.txt | cat -A")

    demo(bash, "unexpand - Convert spaces to tabs",
         "unexpand -a /data/spaces.txt | cat -A")

    # =========================================================================
    # OD - Octal Dump
    # =========================================================================
    print("\n" + "=" * 60)
    print("  OD - Dump Files in Various Formats")
    print("=" * 60)

    demo(bash, "od -c - Character format",
         "echo 'hello' | od -c")

    demo(bash, "od -x - Hexadecimal format",
         "echo 'hello' | od -x")

    # =========================================================================
    # STRINGS - Print Printable Strings
    # =========================================================================
    print("\n" + "=" * 60)
    print("  STRINGS - Print Printable Character Sequences")
    print("=" * 60)

    demo(bash, "strings - Extract printable strings",
         "strings /data/mixed.txt")

    # =========================================================================
    # SPLIT - Split File into Pieces
    # =========================================================================
    print("\n" + "=" * 60)
    print("  SPLIT - Split a File into Pieces")
    print("=" * 60)

    demo(bash, "split - Split into 2-line chunks",
         "split -l 2 /data/fruits.txt /tmp/part_ && ls /tmp/part_*")

    demo(bash, "split - View split files",
         "cat /tmp/part_aa && echo '---' && cat /tmp/part_ab")

    # =========================================================================
    # TEE - Read from stdin, write to stdout and files
    # =========================================================================
    print("\n" + "=" * 60)
    print("  TEE - Read from stdin, Write to stdout and Files")
    print("=" * 60)

    demo(bash, "tee - Write to file and stdout",
         "echo 'hello world' | tee /tmp/tee_output.txt")

    demo(bash, "tee - Verify file was written",
         "cat /tmp/tee_output.txt")

    demo(bash, "tee -a - Append to file",
         "echo 'second line' | tee -a /tmp/tee_output.txt && cat /tmp/tee_output.txt")

    # =========================================================================
    # COMBINED EXAMPLES
    # =========================================================================
    print("\n" + "=" * 60)
    print("  COMBINED EXAMPLES - Pipelines")
    print("=" * 60)

    demo(bash, "Pipeline: sort | uniq -c | sort -rn (frequency count)",
         "cat /data/fruits.txt | sort | uniq -c | sort -rn")

    demo(bash, "Pipeline: grep | cut | sort (extract and sort)",
         "grep -v '^name' /data/csv.txt | cut -d, -f1 | sort")

    demo(bash, "Pipeline: awk | sort | head (top values)",
         "awk -F, 'NR>1 {print $2, $1}' /data/csv.txt | sort -rn | head -2")

    demo(bash, "Pipeline: Complex text transformation",
         "cat /data/poem.txt | tr 'A-Z' 'a-z' | tr -cs 'a-z' '\\n' | sort | uniq")

    # Summary
    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)
    print("""
Commands demonstrated:
  grep, egrep, fgrep, rg    - Pattern matching
  sed                        - Stream editing
  awk                        - Pattern scanning and processing
  cut                        - Remove sections from lines
  tr                         - Translate characters
  sort                       - Sort lines
  uniq                       - Report/omit repeated lines
  head, tail                 - Output parts of files
  wc                         - Word/line/char counts
  comm                       - Compare sorted files
  diff                       - Compare files
  join                       - Join on common field
  paste                      - Merge lines
  column                     - Format into columns
  nl                         - Number lines
  fold                       - Wrap lines
  rev                        - Reverse lines
  tac                        - Reverse file
  expand, unexpand           - Tab/space conversion
  od                         - Octal dump
  strings                    - Extract printable strings
  split                      - Split files
  tee                        - Tee to file and stdout
""")


if __name__ == "__main__":
    main()
