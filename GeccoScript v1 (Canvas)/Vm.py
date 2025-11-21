"""Tiny stack-based VM that reads JSON bytecode as emitted by compiler.py
"""
import sys
import json
from . import stdlib

def run_bc(path):
    with open(path, 'r', encoding='utf-8') as f:
        bc = json.load(f)
    code = bc['code']
    consts = bc.get('consts', [])
    stack = []
    env = {k: v for k, v in stdlib.STD_LIB.items()}

    ip = 0
    while ip < len(code):
        op, arg = code[ip]
        if op == 'LOAD_CONST':
            stack.append(consts[arg])
        elif op == 'LOAD_NAME':
            name = arg
            if name in env:
                stack.append(env[name])
            else:
                raise NameError(name)
        elif op == 'STORE_NAME':
            value = stack.pop()
            env[arg] = value
        elif op == 'BINARY_OP':
            b = stack.pop(); a = stack.pop()
            if arg == '+': stack.append(a + b)
            elif arg == '-': stack.append(a - b)
            elif arg == '*': stack.append(a * b)
            elif arg == '/': stack.append(a / b)
            else: raise RuntimeError('unknown op')
        elif op == 'PRINT':
            v = stack.pop()
            print(v)
        elif op == 'CALL':
            name, argc = arg
            args = [stack.pop() for _ in range(argc)][::-1]
            if name in env and callable(env[name]):
                res = env[name](*args)
                stack.append(res)
            else:
                raise NameError(f'unknown call {name}')
        elif op == 'DEF_RAW':
            # store raw AST for interpreter-style function handling
            node = arg
            name = node[1]
            env[name] = ('function', node[2], node[3])
        else:
            raise RuntimeError(f'unknown instr {op}')
        ip += 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python -m src.gecco.vm file.bc.json')
        sys.exit(1)
    run_bc(sys.argv[1])