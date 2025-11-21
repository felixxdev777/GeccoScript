"""Compile GeccoScript AST to a tiny bytecode format (JSON-friendly).
This is intentionally minimal: used for demonstration and unit tests.
"""
import sys
import json
from .interpreter import tokenize, Parser

# bytecode instruction set (tuples)
# Each instruction is (OP, arg?)

def compile_ast(ast):
    # For demo: compile only expressions, assigns, prints, defs, calls (no closures)
    code = []
    consts = []
    names = []

    def add_const(v):
        if v in consts:
            return consts.index(v)
        consts.append(v)
        return len(consts)-1

    def emit(op, arg=None):
        code.append((op, arg))

    def comp_node(node):
        t = node[0]
        if t == 'block':
            for s in node[1]:
                comp_node(s)
        elif t == 'number' or t == 'string':
            idx = add_const(node[1])
            emit('LOAD_CONST', idx)
        elif t == 'var':
            emit('LOAD_NAME', node[1])
        elif t == 'assign':
            comp_node(node[2])
            emit('STORE_NAME', node[1])
        elif t == 'print':
            comp_node(node[1])
            emit('PRINT', None)
        elif t == 'binop':
            comp_node(node[2]); comp_node(node[3])
            emit('BINARY_OP', node[1])
        elif t == 'call':
            # push args
            for a in node[2]: comp_node(a)
            emit('CALL', (node[1], len(node[2])))
        elif t == 'def':
            # Not compiling function bodies in this minimal compiler; emit as runtime def marker
            # For tests we keep behavior simple: store AST under name
            emit('DEF_RAW', node)
        else:
            # fallback: ignore
            pass

    comp_node(ast)
    return {
        'code': code,
        'consts': consts,
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python -m src.gecco.compiler file.gco [-o out.bc.json]')
        sys.exit(1)
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    tokens = tokenize(src)
    ast = Parser(tokens).parse()
    bc = compile_ast(ast)
    out = path + '.bc.json'
    if '-o' in sys.argv:
        i = sys.argv.index('-o')
        out = sys.argv[i+1]
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(bc, f, indent=2)
    print('Wrote', out)