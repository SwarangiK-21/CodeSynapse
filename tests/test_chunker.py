from codesynapse.services import chunker

PYTHON = '''import os

def top_level(a):
    return a

@decorator
def decorated():
    return 1

class Store:
    def save(self):
        return True

    def load(self):
        return False

class Empty:
    value = 1

async def fetch():
    return 2
'''

TYPESCRIPT = '''export function add(a: number) { return a; }

const multiply = (a: number) => a * 2;

export class Cart {
  total(): number { return 1; }
}

interface Item { id: string }
'''

def symbols(chunks):
    return {c.symbol: c for c in chunks}

def test_python_splits_by_definition():
    found = symbols(chunker.chunk_file("app.py", PYTHON))
    assert set(found) == {"top_level", "decorated", "Store.save", "Store.load", "Empty", "fetch"}
    assert found["Store.save"].kind == "function"
    assert found["Empty"].kind == "class"

def test_line_numbers_match_the_file():
    found = symbols(chunker.chunk_file("app.py", PYTHON))
    assert (found["top_level"].start_line, found["top_level"].end_line) == (3, 4)
    assert found["decorated"].start_line == 6
    assert PYTHON.split("\n")[found["Store.load"].start_line - 1].strip() == "def load(self):"

def test_typescript_and_arrow_functions():
    found = symbols(chunker.chunk_file("cart.ts", TYPESCRIPT))
    assert {"add", "multiply", "Cart.total", "Item"} <= set(found)
    assert found["multiply"].language == "typescript"

def test_tsx_parses():
    found = symbols(chunker.chunk_file("a.tsx", "export const App = () => <div>hi</div>;\n"))
    assert "App" in found

def test_script_without_definitions_still_gets_a_chunk():
    chunks = chunker.chunk_file("run.py", "print('hello')\n")
    assert len(chunks) == 1 and chunks[0].kind == "window"

def test_language_without_grammar_uses_windows():
    chunks = chunker.chunk_file("Main.java", "class Main {}\n")
    assert chunks[0].language == "java" and chunks[0].kind == "window"

def test_long_function_splits_with_correct_lines():
    body = "\n".join(f"    x{i} = {i}" for i in range(300))
    source = f"def huge():\n{body}\n"
    chunks = chunker.chunk_file("big.py", source)
    lines = source.split("\n")
    assert len(chunks) > 1 and all(c.symbol == "huge" for c in chunks)
    for c in chunks:
        assert c.content.split("\n")[0] == lines[c.start_line - 1]
        assert c.end_line - c.start_line < chunker.MAX_CHUNK_LINES

def test_blank_file_has_no_chunks():
    assert chunker.chunk_file("empty.md", "\n\n") == []

def test_broken_code_does_not_crash():
    assert chunker.chunk_file("bad.py", "def (((\n  nonsense") is not None

def test_supported_files():
    assert chunker.is_supported("src/a.py") and chunker.is_supported("A.TSX")
    assert not chunker.is_supported("logo.png") and not chunker.is_supported("Makefile")
