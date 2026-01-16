"""Parser module for just-bash."""

from .lexer import (
    Lexer,
    Token,
    TokenType,
    tokenize,
    HeredocInfo,
    is_valid_name,
    is_valid_assignment_lhs,
    RESERVED_WORDS,
)
from .parser import (
    Parser,
    ParseException,
    parse,
    MAX_INPUT_SIZE,
    MAX_TOKENS,
    MAX_PARSE_ITERATIONS,
)

__all__ = [
    # Lexer
    "Lexer",
    "Token",
    "TokenType",
    "tokenize",
    "HeredocInfo",
    "is_valid_name",
    "is_valid_assignment_lhs",
    "RESERVED_WORDS",
    # Parser
    "Parser",
    "ParseException",
    "parse",
    "MAX_INPUT_SIZE",
    "MAX_TOKENS",
    "MAX_PARSE_ITERATIONS",
]
