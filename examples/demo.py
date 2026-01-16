#!/usr/bin/env python3
"""
Demonstration of just-bash-py capabilities.

This script showcases various bash features implemented in just-bash-py,
a pure Python bash interpreter with an in-memory filesystem.

Run with: python examples/demo.py
"""

import asyncio
from just_bash import Bash


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def demo(command: str, result) -> None:
    """Pretty print a command and its result."""
    print(f"\n  $ {command}")
    print(f"  {'-'*50}")
    if result.stdout:
        for line in result.stdout.rstrip('\n').split('\n'):
            print(f"  {line}")
    if result.stderr:
        for line in result.stderr.rstrip('\n').split('\n'):
            print(f"  [stderr] {line}")
    if not result.stdout and not result.stderr:
        print(f"  (no output)")


async def main():
    """Run all demonstrations."""
    bash = Bash()

    print("\n" + "="*70)
    print("  JUST-BASH-PY DEMONSTRATION")
    print("  A Pure Python Bash Interpreter")
    print("="*70)

    # =========================================================================
    # 1. BASIC COMMANDS
    # =========================================================================
    section("1. BASIC COMMANDS")

    cmd = 'echo "Hello, World!"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'printf "Name: %s, Age: %d\\n" "Alice" 30'
    demo(cmd, await bash.exec(cmd))

    cmd = 'name="just-bash"; echo "Welcome to $name"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 2. VARIABLES AND EXPANSION
    # =========================================================================
    section("2. VARIABLES AND EXPANSION")

    cmd = 'greeting="Hello"; echo "${greeting}, User!"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'text="hello world"; echo "Length: ${#text}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'path="/home/user/file.txt"; echo "Basename: ${path##*/}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'str="hello"; echo "Uppercase: ${str^^}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'default="${UNDEFINED:-default_value}"; echo "$default"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 3. ARITHMETIC
    # =========================================================================
    section("3. ARITHMETIC")

    cmd = 'echo "2 + 3 = $((2 + 3))"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'x=5; echo "x=$x, x*2=$((x * 2))"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'n=10; echo "n++ = $((n++)), now n=$n"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'a=5; b=3; echo "max = $((a > b ? a : b))"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo "Binary 101 = $((2#101)), Hex ff = $((16#ff))"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 4. ARRAYS
    # =========================================================================
    section("4. ARRAYS")

    cmd = 'arr=(apple banana cherry); echo "First: ${arr[0]}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'arr=(a b c d e); echo "All: ${arr[@]}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'arr=(one two three); echo "Count: ${#arr[@]}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'arr=(x y z); for i in "${arr[@]}"; do echo "- $i"; done'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 5. CONTROL FLOW
    # =========================================================================
    section("5. CONTROL FLOW")

    cmd = 'for i in 1 2 3; do echo "Number: $i"; done'
    demo(cmd, await bash.exec(cmd))

    cmd = 'for fruit in apple banana cherry; do echo "Fruit: $fruit"; done'
    demo(cmd, await bash.exec(cmd))

    cmd = 'x=3; if [[ $x -gt 2 ]]; then echo "x is greater than 2"; fi'
    demo(cmd, await bash.exec(cmd))

    cmd = '''
case "hello" in
  hi) echo "Matched hi" ;;
  hello) echo "Matched hello" ;;
  *) echo "No match" ;;
esac
'''.strip()
    demo(cmd, await bash.exec(cmd))

    cmd = 'i=1; while [[ $i -le 3 ]]; do echo "i=$i"; ((i++)); done'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 6. CONDITIONALS
    # =========================================================================
    section("6. CONDITIONALS")

    cmd = '[[ "hello" == "hello" ]] && echo "Strings match"'
    demo(cmd, await bash.exec(cmd))

    cmd = '[[ "hello world" =~ ^hello ]] && echo "Regex matches"'
    demo(cmd, await bash.exec(cmd))

    cmd = '[[ -n "nonempty" ]] && echo "String is non-empty"'
    demo(cmd, await bash.exec(cmd))

    cmd = '[[ 5 -gt 3 && 2 -lt 4 ]] && echo "Both conditions true"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 7. PIPES AND COMMAND SUBSTITUTION
    # =========================================================================
    section("7. PIPES AND COMMAND SUBSTITUTION")

    cmd = 'echo "hello world" | tr "a-z" "A-Z"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo -e "banana\\napple\\ncherry" | sort'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo "one two three" | awk \'{print $2}\''
    demo(cmd, await bash.exec(cmd))

    cmd = 'today=$(date +%Y-%m-%d); echo "Today is $today"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'files=$(echo "a.txt b.txt c.txt"); echo "Files: $files"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 8. TEXT PROCESSING
    # =========================================================================
    section("8. TEXT PROCESSING")

    cmd = 'echo "hello world hello" | grep -o "hello" | wc -l'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo "hello world" | sed "s/world/universe/"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo "  hello  " | sed "s/^ *//;s/ *$//"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo "name:alice:30" | cut -d: -f2'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo -e "b\\na\\nc\\na\\nb" | sort | uniq -c'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 9. IN-MEMORY FILESYSTEM
    # =========================================================================
    section("9. IN-MEMORY FILESYSTEM")

    cmd = 'echo "Hello from file" > /tmp/test.txt; cat /tmp/test.txt'
    demo(cmd, await bash.exec(cmd))

    cmd = 'mkdir -p /tmp/mydir; echo "file content" > /tmp/mydir/file.txt; ls /tmp/mydir'
    demo(cmd, await bash.exec(cmd))

    cmd = 'echo -e "line1\\nline2\\nline3" > /tmp/lines.txt; wc -l /tmp/lines.txt'
    demo(cmd, await bash.exec(cmd))

    cmd = 'cat /tmp/lines.txt | head -2'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 10. FUNCTIONS
    # =========================================================================
    section("10. FUNCTIONS")

    cmd = 'greet() { echo "Hello, $1!"; }; greet "World"'
    demo(cmd, await bash.exec(cmd))

    cmd = '''
factorial() {
  if [[ $1 -le 1 ]]; then echo 1
  else echo $(( $1 * $(factorial $(($1 - 1))) ))
  fi
}
echo "Factorial of 5 = $(factorial 5)"
'''.strip()
    # Use simpler recursive example
    cmd = 'say_hi() { echo "Hi from function!"; }; say_hi; say_hi'
    demo(cmd, await bash.exec(cmd))

    cmd = '''
is_even() {
  if (( $1 % 2 == 0 )); then
    return 0
  else
    return 1
  fi
}
is_even 4 && echo "4 is even"
is_even 5 || echo "5 is odd"
'''.strip()
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 11. JSON PROCESSING (jq)
    # =========================================================================
    section("11. JSON PROCESSING (jq)")

    cmd = '''echo '{"name":"Alice","age":30}' | jq '.name' '''
    demo(cmd, await bash.exec(cmd))

    cmd = '''echo '[1,2,3,4,5]' | jq 'map(. * 2)' '''
    demo(cmd, await bash.exec(cmd))

    cmd = '''echo '{"users":[{"name":"Alice"},{"name":"Bob"}]}' | jq '.users[].name' '''
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # 12. ADVANCED FEATURES
    # =========================================================================
    section("12. ADVANCED FEATURES")

    cmd = 'x="test"; echo "${x@Q}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'arr=(1 2 3); echo "Keys: ${!arr[@]}"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'base=16; echo "hex ff = $(($base#ff))"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'readonly CONST=42; echo "CONST=$CONST"'
    demo(cmd, await bash.exec(cmd))

    cmd = 'shopt -s extglob; echo "extglob enabled"'
    demo(cmd, await bash.exec(cmd))

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("  DEMONSTRATION COMPLETE")
    print("="*70)
    print("""
  just-bash-py provides a pure Python bash interpreter with:

  - Full variable expansion and parameter operations
  - Arrays (indexed and associative)
  - Arithmetic with all operators
  - Control flow (if/for/while/case)
  - Pipes and command substitution
  - 70+ commands (grep, sed, awk, jq, curl, etc.)
  - In-memory virtual filesystem
  - No external dependencies or WASM

  For more information, see the README.md
""")


if __name__ == "__main__":
    asyncio.run(main())
