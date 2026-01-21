# Command Coverage Audit: just-bash TypeScript vs Python Port

## Overview

Systematic comparison of the original TypeScript `just-bash` implementation against the Python port to identify missing functionality that silently fails.

---

## Complex/Special Commands

### xargs
- Missing flags:
  - `-P NUM` - parallel processing (silently ignored)
  - `-d` delimiter escape sequences not parsed
  - `-v` (--verbose) formatting less complete

### sqlite3
- Status: EXISTS in Python (sqlite3_cmd.py)
- Notes: Needs detailed comparison for missing features

---

## Summary by Severity

### LOW PRIORITY (nice to have)
1. **printf** - Variable assignment (`-v var`)
2. **strings** - Encoding selection (`-e`)