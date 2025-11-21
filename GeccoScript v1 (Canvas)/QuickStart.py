# clone
git clone <your-repo-url> geccoscript
cd geccoscript
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .[dev]

# run sample interpreted
python -m src.gecco.interpreter samples/factorial.gco

# compile + run on VM
python -m src.gecco.compiler samples/factorial.gco -o samples/factorial.gco.bc
python -m src.gecco.vm samples/factorial.gco.bc

# run tests
pytest -q