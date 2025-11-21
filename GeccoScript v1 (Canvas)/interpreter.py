"""Simple GeccoScript interpreter (AST evaluator).
Usage: python -m src.gecco.interpreter path/to/file.gco
"""
import sys
import re
from dataclasses import dataclass
from typing import Any
from . import stdlib

# Tokenizer and parser are intentionally simple and readable for learning.
TOKEN_SPEC = [
    ("NUMBER",   r"\d+(?:\.\d+)?"),
    ("STRING",   r'"([^"\\]|\\.)*"'),
    ("NAME",     r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP",       r"==|!=|<=|>=|[+\-*/()<>=]"),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t]+"),
    ("COMMENT",  r"#.*"),
]

TOK_REGEX = "|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC)
token_re = re.compile(TOK_REGEX)

@dataclass
class Token:
    type: str
    value: str

# Tokenize
def tokenize(code: str):
    pos = 0
    tokens = []
    while pos < len(code):
        m = token_re.match(code, pos)
        if not m:
            raise SyntaxError(f"Unexpected character {code[pos]!r} at {pos}")
        typ = m.lastgroup
        val = m.group(typ)
        pos = m.end()
        if typ in ("SKIP", "COMMENT", "NEWLINE"):
            continue
        if typ == "STRING":
            val = bytes(val[1:-1], "utf-8").decode("unicode_escape")
        tokens.append(Token(typ, val))
    tokens.append(Token("EOF", ""))
    return tokens

# Parser & AST
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i]

    def next(self):
        t = self.tokens[self.i]
        self.i += 1
        return t

    def expect(self, typ, val=None):
        t = self.next()
        if t.type != typ or (val is not None and t.value != val):
            raise SyntaxError(f"Expected {typ} {val}, got {t}")
        return t

    def parse(self):
        stmts = []
        while self.peek().type != "EOF":
            stmts.append(self.parse_stmt())
        return ("block", stmts)

    def parse_stmt(self):
        tok = self.peek()
        if tok.type == "NAME" and tok.value == "print":
            self.next()
            expr = self.parse_expr()
            return ("print", expr)
        if tok.type == "NAME" and tok.value == "if":
            self.next()
            cond = self.parse_expr()
            body = []
            while not (self.peek().type == "NAME" and self.peek().value == "end"):
                body.append(self.parse_stmt())
            self.expect("NAME", "end")
            return ("if", cond, ("block", body))
        if tok.type == "NAME" and tok.value == "while":
            self.next()
            cond = self.parse_expr()
            body = []
            while not (self.peek().type == "NAME" and self.peek().value == "end"):
                body.append(self.parse_stmt())
            self.expect("NAME", "end")
            return ("while", cond, ("block", body))
        if tok.type == "NAME" and tok.value == "def":
            # function definition: def name(params) ... end
            self.next()
            name = self.expect("NAME").value
            # params
            self.expect("OP", "(")
            params = []
            if not (self.peek().type == "OP" and self.peek().value == ")"):
                while True:
                    params.append(self.expect("NAME").value)
                    if self.peek().type == "OP" and self.peek().value == ")":
                        break
                    self.expect("OP", ",")
            self.expect("OP", ")")
            body = []
            while not (self.peek().type == "NAME" and self.peek().value == "end"):
                body.append(self.parse_stmt())
            self.expect("NAME", "end")
            return ("def", name, params, ("block", body))
        # assignment
        if tok.type == "NAME":
            if self.tokens[self.i+1].type == "OP" and self.tokens[self.i+1].value == "=":
                name = self.next().value
                self.expect("OP", "=")
                expr = self.parse_expr()
                return ("assign", name, expr)
        expr = self.parse_expr()
        return ("expr", expr)

    def parse_expr(self):
        return self.parse_equality()

    def parse_equality(self):
        node = self.parse_add()
        while self.peek().type == "OP" and self.peek().value in ("==", "!=", "<", ">", "<=", ">="):
            op = self.next().value
            right = self.parse_add()
            node = ("binop", op, node, right)
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.peek().type == "OP" and self.peek().value in ("+", "-"):
            op = self.next().value
            right = self.parse_mul()
            node = ("binop", op, node, right)
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.peek().type == "OP" and self.peek().value in ("*", "/"):
            op = self.next().value
            right = self.parse_unary()
            node = ("binop", op, node, right)
        return node

    def parse_unary(self):
        if self.peek().type == "OP" and self.peek().value == "-":
            self.next()
            node = self.parse_unary()
            return ("unary", "-", node)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()
        if tok.type == "NUMBER":
            self.next()
            return ("number", float(tok.value) if "." in tok.value else int(tok.value))
        if tok.type == "STRING":
            self.next()
            return ("string", tok.value)
        if tok.type == "NAME":
            # function call lookahead
            if self.tokens[self.i+1].type == "OP" and self.tokens[self.i+1].value == "(":
                name = self.next().value
                self.expect("OP", "(")
                args = []
                if not (self.peek().type == "OP" and self.peek().value == ")"):
                    while True:
                        args.append(self.parse_expr())
                        if self.peek().type == "OP" and self.peek().value == ")":
                            break
                        self.expect("OP", ",")
                self.expect("OP", ")")
                return ("call", name, args)
            self.next()
            return ("var", tok.value)
        if tok.type == "OP" and tok.value == "(":
            self.next()
            node = self.parse_expr()
            self.expect("OP", ")")
            return node
        raise SyntaxError(f"Unexpected token {tok}")

# Interpreter runtime
class ReturnExc(Exception):
    def __init__(self, value):
        self.value = value

class Env(dict):
    pass

def eval_expr(node, env):
    t = node[0]
    if t == "number" or t == "string":
        return node[1]
    if t == "var":
        name = node[1]
        if name in env:
            return env[name]
        if name in stdlib.STD_LIB:
            return stdlib.STD_LIB[name]
        raise NameError(f"Undefined variable: {name}")
    if t == "unary":
        op = node[1]
        val = eval_expr(node[2], env)
        if op == "-":
            return -val
    if t == "binop":
        op = node[1]
        a = eval_expr(node[2], env)
        b = eval_expr(node[3], env)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "<":
            return a < b
        if op == ">":
            return a > b
        if op == "<=":
            return a <= b
        if op == ">=":
            return a >= b
    if t == "call":
        name = node[1]
        args = [eval_expr(a, env) for a in node[2]]
        if name in stdlib.STD_LIB:
            return stdlib.STD_LIB[name](*args)
        # user-defined function
        fn = env.get(name)
        if fn and fn[0] == "function":
            params, body = fn[1], fn[2]
            if len(params) != len(args):
                raise TypeError("argument count mismatch")
            local = Env()
            # shallow capture of globals
            local.update(env)
            for n, v in zip(params, args):
                local[n] = v
            try:
                run_node(body, local)
            except ReturnExc as r:
                return r.value
            return None
        raise NameError(f"Unknown function: {name}")
    raise RuntimeError(f"Unknown expr type: {t}")


def run_node(node, env):
    t = node[0]
    if t == "block":
        for s in node[1]:
            run_node(s, env)
    elif t == "print":
        val = eval_expr(node[1], env)
        print(val)
    elif t == "assign":
        name = node[1]
        val = eval_expr(node[2], env)
        env[name] = val
    elif t == "expr":
        eval_expr(node[1], env)
    elif t == "if":
        cond = eval_expr(node[1], env)
        if cond:
            run_node(node[2], env)
    elif t == "while":
        while eval_expr(node[1], env):
            run_node(node[2], env)
    elif t == "def":
        name, params, body = node[1], node[2], node[3]
        env[name] = ("function", params, body)
    else:
        raise RuntimeError(f"Unknown node: {t}")

# CLI
def run_source(source: str, filename: str = "<string>"):
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse()
    env = Env()
    # expose stdlib
    env.update(stdlib.STD_LIB)
    run_node(ast, env)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m src.gecco.interpreter file.gco")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    run_source(src, path)