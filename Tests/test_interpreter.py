from src.gecco.interpreter import run_source

def test_factorial_prints(capsys):
    src = '''
    def fact(n)
      if n <= 1
        return 1
      end
      return n * fact(n - 1)
    end
    print fact(5)
    '''
    run_source(src)
    captured = capsys.readouterr()
    assert '120' in captured.out