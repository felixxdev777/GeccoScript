from src.gecco.compiler import compile_ast
from src.gecco.interpreter import tokenize, Parser
from src.gecco.vm import run_bc
import json, tempfile


def test_compile_and_run(tmp_path, capsys):
    src = 'x = 2\nprint x\n'
    tokens = tokenize(src)
    ast = Parser(tokens).parse()
    bc = compile_ast(ast)
    p = tmp_path / 'tmp.bc.json'
    p.write_text(json.dumps(bc))
    run_bc(str(p))
    captured = capsys.readouterr()
    assert '2' in captured.out