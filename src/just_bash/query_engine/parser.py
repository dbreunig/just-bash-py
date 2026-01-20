"""Parser for jq expressions.

Converts a token sequence into an AST using recursive descent parsing.
"""

from .tokenizer import tokenize
from .types import (
    ArrayNode,
    AstNode,
    BinaryOpNode,
    CallNode,
    CommaNode,
    CondNode,
    ElifBranch,
    FieldNode,
    ForeachNode,
    IdentityNode,
    IndexNode,
    IterateNode,
    LiteralNode,
    ObjectEntry,
    ObjectNode,
    OptionalNode,
    ParenNode,
    PipeNode,
    RecurseNode,
    ReduceNode,
    SliceNode,
    StringInterpNode,
    Token,
    TokenType,
    TryNode,
    UnaryOpNode,
    UpdateOpNode,
    VarBindNode,
    VarRefNode,
)


class Parser:
    """Recursive descent parser for jq expressions."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset: int = 0) -> Token:
        """Look at token at current position + offset."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(TokenType.EOF, None, -1)

    def advance(self) -> Token:
        """Advance and return current token."""
        tok = (
            self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TokenType.EOF, None, -1)
        )
        self.pos += 1
        return tok

    def check(self, type_: TokenType) -> bool:
        """Check if current token is of given type."""
        return self.peek().type == type_

    def match(self, *types: TokenType) -> Token | None:
        """If current token matches any type, advance and return it."""
        for t in types:
            if self.check(t):
                return self.advance()
        return None

    def expect(self, type_: TokenType, msg: str) -> Token:
        """Expect current token to be of given type, or raise error."""
        if not self.check(type_):
            raise ValueError(f"{msg} at position {self.peek().pos}, got {self.peek().type.name}")
        return self.advance()

    def parse(self) -> AstNode:
        """Parse the entire expression."""
        expr = self.parse_expr()
        if not self.check(TokenType.EOF):
            raise ValueError(
                f"Unexpected token {self.peek().type.name} at position {self.peek().pos}"
            )
        return expr

    def parse_expr(self) -> AstNode:
        """Parse an expression (top level)."""
        return self.parse_pipe()

    def parse_pipe(self) -> AstNode:
        """Parse pipe expressions (left-associative |)."""
        left = self.parse_comma()
        while self.match(TokenType.PIPE):
            right = self.parse_comma()
            left = PipeNode(left, right)
        return left

    def parse_comma(self) -> AstNode:
        """Parse comma expressions (left-associative ,)."""
        left = self.parse_var_bind()
        while self.match(TokenType.COMMA):
            right = self.parse_var_bind()
            left = CommaNode(left, right)
        return left

    def parse_var_bind(self) -> AstNode:
        """Parse variable binding (expr as $var | body)."""
        expr = self.parse_update()
        if self.match(TokenType.AS):
            var_token = self.expect(TokenType.IDENT, "Expected variable name after 'as'")
            var_name = var_token.value
            if not isinstance(var_name, str) or not var_name.startswith("$"):
                raise ValueError(f"Variable name must start with $ at position {var_token.pos}")
            self.expect(TokenType.PIPE, "Expected '|' after variable binding")
            body = self.parse_expr()
            return VarBindNode(var_name, expr, body)
        return expr

    def parse_update(self) -> AstNode:
        """Parse update operators (=, |=, +=, -=, *=, /=, %=, //=)."""
        left = self.parse_alt()
        op_map = {
            TokenType.ASSIGN: "=",
            TokenType.UPDATE_ADD: "+=",
            TokenType.UPDATE_SUB: "-=",
            TokenType.UPDATE_MUL: "*=",
            TokenType.UPDATE_DIV: "/=",
            TokenType.UPDATE_MOD: "%=",
            TokenType.UPDATE_ALT: "//=",
            TokenType.UPDATE_PIPE: "|=",
        }
        tok = self.match(
            TokenType.ASSIGN,
            TokenType.UPDATE_ADD,
            TokenType.UPDATE_SUB,
            TokenType.UPDATE_MUL,
            TokenType.UPDATE_DIV,
            TokenType.UPDATE_MOD,
            TokenType.UPDATE_ALT,
            TokenType.UPDATE_PIPE,
        )
        if tok:
            value = self.parse_var_bind()
            return UpdateOpNode(op_map[tok.type], left, value)
        return left

    def parse_alt(self) -> AstNode:
        """Parse alternative operator (//)."""
        left = self.parse_or()
        while self.match(TokenType.ALT):
            right = self.parse_or()
            left = BinaryOpNode("//", left, right)
        return left

    def parse_or(self) -> AstNode:
        """Parse or operator."""
        left = self.parse_and()
        while self.match(TokenType.OR):
            right = self.parse_and()
            left = BinaryOpNode("or", left, right)
        return left

    def parse_and(self) -> AstNode:
        """Parse and operator."""
        left = self.parse_comparison()
        while self.match(TokenType.AND):
            right = self.parse_comparison()
            left = BinaryOpNode("and", left, right)
        return left

    def parse_comparison(self) -> AstNode:
        """Parse comparison operators (==, !=, <, <=, >, >=)."""
        left = self.parse_add_sub()
        op_map = {
            TokenType.EQ: "==",
            TokenType.NE: "!=",
            TokenType.LT: "<",
            TokenType.LE: "<=",
            TokenType.GT: ">",
            TokenType.GE: ">=",
        }
        tok = self.match(
            TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE
        )
        if tok:
            right = self.parse_add_sub()
            left = BinaryOpNode(op_map[tok.type], left, right)
        return left

    def parse_add_sub(self) -> AstNode:
        """Parse addition and subtraction (left-associative)."""
        left = self.parse_mul_div()
        while True:
            if self.match(TokenType.PLUS):
                right = self.parse_mul_div()
                left = BinaryOpNode("+", left, right)
            elif self.match(TokenType.MINUS):
                right = self.parse_mul_div()
                left = BinaryOpNode("-", left, right)
            else:
                break
        return left

    def parse_mul_div(self) -> AstNode:
        """Parse multiplication, division, and modulo (left-associative)."""
        left = self.parse_unary()
        while True:
            if self.match(TokenType.STAR):
                right = self.parse_unary()
                left = BinaryOpNode("*", left, right)
            elif self.match(TokenType.SLASH):
                right = self.parse_unary()
                left = BinaryOpNode("/", left, right)
            elif self.match(TokenType.PERCENT):
                right = self.parse_unary()
                left = BinaryOpNode("%", left, right)
            else:
                break
        return left

    def parse_unary(self) -> AstNode:
        """Parse unary operators (-)."""
        if self.match(TokenType.MINUS):
            operand = self.parse_unary()
            return UnaryOpNode("-", operand)
        return self.parse_postfix()

    def parse_postfix(self) -> AstNode:
        """Parse postfix operators (?, .[...], .field)."""
        expr = self.parse_primary()

        while True:
            if self.match(TokenType.QUESTION):
                expr = OptionalNode(expr)
            elif self.check(TokenType.DOT) and self.peek(1).type == TokenType.IDENT:
                self.advance()  # consume DOT
                name_tok = self.expect(TokenType.IDENT, "Expected field name")
                expr = FieldNode(name_tok.value, expr)
            elif self.check(TokenType.LBRACKET):
                self.advance()
                if self.match(TokenType.RBRACKET):
                    expr = IterateNode(expr)
                elif self.check(TokenType.COLON):
                    self.advance()
                    end = None if self.check(TokenType.RBRACKET) else self.parse_expr()
                    self.expect(TokenType.RBRACKET, "Expected ']'")
                    expr = SliceNode(None, end, expr)
                else:
                    index_expr = self.parse_expr()
                    if self.match(TokenType.COLON):
                        end = None if self.check(TokenType.RBRACKET) else self.parse_expr()
                        self.expect(TokenType.RBRACKET, "Expected ']'")
                        expr = SliceNode(index_expr, end, expr)
                    else:
                        self.expect(TokenType.RBRACKET, "Expected ']'")
                        expr = IndexNode(index_expr, expr)
            else:
                break

        return expr

    def parse_primary(self) -> AstNode:
        """Parse primary expressions."""
        # Recursive descent (..)
        if self.match(TokenType.DOTDOT):
            return RecurseNode()

        # Identity or field access starting with dot
        if self.match(TokenType.DOT):
            # Check for .[] or .[n] or .[n:m]
            if self.check(TokenType.LBRACKET):
                self.advance()
                if self.match(TokenType.RBRACKET):
                    return IterateNode()
                if self.check(TokenType.COLON):
                    self.advance()
                    end = None if self.check(TokenType.RBRACKET) else self.parse_expr()
                    self.expect(TokenType.RBRACKET, "Expected ']'")
                    return SliceNode(None, end)
                index_expr = self.parse_expr()
                if self.match(TokenType.COLON):
                    end = None if self.check(TokenType.RBRACKET) else self.parse_expr()
                    self.expect(TokenType.RBRACKET, "Expected ']'")
                    return SliceNode(index_expr, end)
                self.expect(TokenType.RBRACKET, "Expected ']'")
                return IndexNode(index_expr)
            # .field
            if self.check(TokenType.IDENT):
                name = self.advance().value
                return FieldNode(name)
            # Just identity
            return IdentityNode()

        # Literals
        if self.match(TokenType.TRUE):
            return LiteralNode(True)
        if self.match(TokenType.FALSE):
            return LiteralNode(False)
        if self.match(TokenType.NULL):
            return LiteralNode(None)
        if self.check(TokenType.NUMBER):
            tok = self.advance()
            return LiteralNode(tok.value)
        if self.check(TokenType.STRING):
            tok = self.advance()
            s = tok.value
            # Check for string interpolation
            if isinstance(s, str) and "\\(" in s:
                return self.parse_string_interpolation(s)
            return LiteralNode(s)

        # Array construction
        if self.match(TokenType.LBRACKET):
            if self.match(TokenType.RBRACKET):
                return ArrayNode()
            elements = self.parse_expr()
            self.expect(TokenType.RBRACKET, "Expected ']'")
            return ArrayNode(elements)

        # Object construction
        if self.match(TokenType.LBRACE):
            return self.parse_object_construction()

        # Parentheses
        if self.match(TokenType.LPAREN):
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN, "Expected ')'")
            return ParenNode(expr)

        # if-then-else
        if self.match(TokenType.IF):
            return self.parse_if()

        # try-catch
        if self.match(TokenType.TRY):
            body = self.parse_postfix()
            catch_expr = None
            if self.match(TokenType.CATCH):
                catch_expr = self.parse_postfix()
            return TryNode(body, catch_expr)

        # reduce EXPR as $VAR (INIT; UPDATE)
        if self.match(TokenType.REDUCE):
            expr = self.parse_postfix()
            self.expect(TokenType.AS, "Expected 'as' after reduce expression")
            var_token = self.expect(TokenType.IDENT, "Expected variable name")
            var_name = var_token.value
            if not isinstance(var_name, str) or not var_name.startswith("$"):
                raise ValueError(f"Variable name must start with $ at position {var_token.pos}")
            self.expect(TokenType.LPAREN, "Expected '(' after variable")
            init = self.parse_expr()
            self.expect(TokenType.SEMICOLON, "Expected ';' after init expression")
            update = self.parse_expr()
            self.expect(TokenType.RPAREN, "Expected ')' after update expression")
            return ReduceNode(expr, var_name, init, update)

        # foreach EXPR as $VAR (INIT; UPDATE) or (INIT; UPDATE; EXTRACT)
        if self.match(TokenType.FOREACH):
            expr = self.parse_postfix()
            self.expect(TokenType.AS, "Expected 'as' after foreach expression")
            var_token = self.expect(TokenType.IDENT, "Expected variable name")
            var_name = var_token.value
            if not isinstance(var_name, str) or not var_name.startswith("$"):
                raise ValueError(f"Variable name must start with $ at position {var_token.pos}")
            self.expect(TokenType.LPAREN, "Expected '(' after variable")
            init = self.parse_expr()
            self.expect(TokenType.SEMICOLON, "Expected ';' after init expression")
            update = self.parse_expr()
            extract = None
            if self.match(TokenType.SEMICOLON):
                extract = self.parse_expr()
            self.expect(TokenType.RPAREN, "Expected ')' after expressions")
            return ForeachNode(expr, var_name, init, update, extract)

        # not as a standalone filter (when used as a function, not unary operator)
        if self.match(TokenType.NOT):
            return CallNode("not")

        # Variable reference or function call
        if self.check(TokenType.IDENT):
            tok = self.advance()
            name = tok.value

            # Variable reference
            if isinstance(name, str) and name.startswith("$"):
                return VarRefNode(name)

            # Function call with args
            if self.match(TokenType.LPAREN):
                args: list[AstNode] = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self.match(TokenType.SEMICOLON):
                        args.append(self.parse_expr())
                self.expect(TokenType.RPAREN, "Expected ')'")
                return CallNode(name, args)

            # Builtin without parens
            return CallNode(name)

        raise ValueError(f"Unexpected token {self.peek().type.name} at position {self.peek().pos}")

    def parse_object_construction(self) -> ObjectNode:
        """Parse object construction {...}."""
        entries: list[ObjectEntry] = []

        if not self.check(TokenType.RBRACE):
            while True:
                key: AstNode | str
                value: AstNode

                # Check for ({(.key): .value}) dynamic key
                if self.match(TokenType.LPAREN):
                    key = self.parse_expr()
                    self.expect(TokenType.RPAREN, "Expected ')'")
                    self.expect(TokenType.COLON, "Expected ':'")
                    value = self.parse_object_value()
                elif self.check(TokenType.IDENT):
                    ident_tok = self.advance()
                    ident = ident_tok.value
                    if self.match(TokenType.COLON):
                        # {key: value}
                        key = ident
                        value = self.parse_object_value()
                    else:
                        # {key} shorthand for {key: .key}
                        key = ident
                        value = FieldNode(ident)
                elif self.check(TokenType.STRING):
                    key_tok = self.advance()
                    key = key_tok.value
                    self.expect(TokenType.COLON, "Expected ':'")
                    value = self.parse_object_value()
                else:
                    raise ValueError(f"Expected object key at position {self.peek().pos}")

                entries.append(ObjectEntry(key, value))

                if not self.match(TokenType.COMMA):
                    break

        self.expect(TokenType.RBRACE, "Expected '}'")
        return ObjectNode(entries)

    def parse_object_value(self) -> AstNode:
        """Parse object value - allows pipes but stops at comma or rbrace."""
        left = self.parse_var_bind()
        while self.match(TokenType.PIPE):
            right = self.parse_var_bind()
            left = PipeNode(left, right)
        return left

    def parse_if(self) -> CondNode:
        """Parse if-then-elif-else-end."""
        cond = self.parse_expr()
        self.expect(TokenType.THEN, "Expected 'then'")
        then = self.parse_expr()

        elifs: list[ElifBranch] = []
        while self.match(TokenType.ELIF):
            elif_cond = self.parse_expr()
            self.expect(TokenType.THEN, "Expected 'then' after elif")
            elif_then = self.parse_expr()
            elifs.append(ElifBranch(elif_cond, elif_then))

        else_expr = None
        if self.match(TokenType.ELSE):
            else_expr = self.parse_expr()

        self.expect(TokenType.END, "Expected 'end'")
        return CondNode(cond, then, elifs, else_expr)

    def parse_string_interpolation(self, s: str) -> StringInterpNode:
        """Parse a string with interpolation."""
        parts: list[str | AstNode] = []
        current = ""
        i = 0

        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "(":
                if current:
                    parts.append(current)
                    current = ""
                i += 2
                # Find matching paren
                depth = 1
                expr_str = ""
                while i < len(s) and depth > 0:
                    if s[i] == "(":
                        depth += 1
                    elif s[i] == ")":
                        depth -= 1
                    if depth > 0:
                        expr_str += s[i]
                    i += 1
                tokens = tokenize(expr_str)
                parser = Parser(tokens)
                parts.append(parser.parse())
            else:
                current += s[i]
                i += 1

        if current:
            parts.append(current)

        return StringInterpNode(parts)


def parse(input_str: str) -> AstNode:
    """Parse a jq expression string into an AST.

    Args:
        input_str: The jq expression to parse

    Returns:
        The root AST node

    Raises:
        ValueError: If the expression is invalid
    """
    tokens = tokenize(input_str)
    parser = Parser(tokens)
    return parser.parse()
