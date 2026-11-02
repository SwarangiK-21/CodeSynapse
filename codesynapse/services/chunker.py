from dataclasses import dataclass
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Parser

MAX_CHUNK_LINES = 120
WINDOW_OVERLAP = 10

LANGUAGES = {
    ".py": ("python", Language(tree_sitter_python.language())),
    ".js": ("javascript", Language(tree_sitter_javascript.language())),
    ".jsx": ("javascript", Language(tree_sitter_javascript.language())),
    ".ts": ("typescript", Language(tree_sitter_typescript.language_typescript())),
    ".tsx": ("typescript", Language(tree_sitter_typescript.language_tsx())),
}

# No grammar for these yet, so they are split into line windows
OTHER_LANGUAGES = {
    ".java": "java", ".go": "go", ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp", ".cs": "csharp",
    ".rb": "ruby", ".php": "php", ".kt": "kotlin", ".swift": "swift", ".sql": "sql", ".md": "markdown",
    ".yml": "yaml", ".yaml": "yaml", ".toml": "toml", ".tf": "terraform", ".sh": "shell",
}

# Config files show skills too, such as CI, containers and infrastructure
NAMED_FILES = {"dockerfile": "docker", "makefile": "make"}

FUNCTION_NODES = {"function_definition", "function_declaration", "generator_function_declaration",
                  "method_definition"}
CLASS_NODES = {"class_definition", "class_declaration", "abstract_class_declaration", "interface_declaration"}
VALUE_NODES = {"lexical_declaration", "variable_declaration"}
ARROW_NODES = {"arrow_function", "function_expression", "function"}

@dataclass
class Chunk:
    path: str
    language: str
    kind: str
    symbol: str
    start_line: int
    end_line: int
    content: str

def is_supported(path):
    return extension(path) in LANGUAGES or extension(path) in OTHER_LANGUAGES or file_name(path) in NAMED_FILES

def file_name(path):
    return path.rsplit("/", 1)[-1].lower()

def extension(path):
    name = path.rsplit("/", 1)[-1]
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""

def windows(path, language, lines, offset=0, kind="window", symbol=""):
    """Splits lines into overlapping windows. Line numbers stay relative to the file."""
    chunks = []
    start = 0
    while start < len(lines):
        part = lines[start:start + MAX_CHUNK_LINES]
        if "\n".join(part).strip():
            chunks.append(Chunk(path, language, kind, symbol, offset + start + 1, offset + start + len(part),
                                "\n".join(part)))
        if start + MAX_CHUNK_LINES >= len(lines):
            break
        start += MAX_CHUNK_LINES - WINDOW_OVERLAP
    return chunks

def node_name(node):
    name = node.child_by_field_name("name")
    return name.text.decode("utf-8", "replace") if name else ""

def arrow_name(node):
    """Returns the name in `const f = () => {}`, which is how a lot of JS is written."""
    for child in node.named_children:
        if child.type == "variable_declarator":
            value = child.child_by_field_name("value")
            if value is not None and value.type in ARROW_NODES:
                return node_name(child)
    return ""

def unwrap(node):
    """Looks through decorators and `export` to the definition inside."""
    if node.type in ("decorated_definition", "export_statement"):
        for child in node.named_children:
            if child.type in FUNCTION_NODES | CLASS_NODES | VALUE_NODES:
                return child
    return node

def add(chunks, path, language, lines, outer, kind, symbol):
    start, end = outer.start_point[0], outer.end_point[0]
    chunks.extend(windows(path, language, lines[start:end + 1], start, kind, symbol))

def class_body(node):
    return next((c for c in node.named_children if c.type in ("block", "class_body", "interface_body")), None)

def walk(node, path, language, lines, chunks, prefix=""):
    for outer in node.named_children:
        inner = unwrap(outer)
        if inner.type in FUNCTION_NODES:
            add(chunks, path, language, lines, outer, "function", prefix + node_name(inner))
        elif inner.type in CLASS_NODES:
            body = class_body(inner)
            before = len(chunks)
            if body is not None:
                walk(body, path, language, lines, chunks, f"{prefix}{node_name(inner)}.")
            # A class without methods is still worth finding as a whole
            if len(chunks) == before:
                add(chunks, path, language, lines, outer, "class", prefix + node_name(inner))
        elif inner.type in VALUE_NODES and arrow_name(inner):
            add(chunks, path, language, lines, outer, "function", prefix + arrow_name(inner))

def module_chunks(path, language, lines, chunks):
    """Keeps code outside any definition: imports, app setup and configuration."""
    covered = {i for c in chunks for i in range(c.start_line - 1, c.end_line)}
    found = []
    start = None
    for i in range(len(lines) + 1):
        if i < len(lines) and i not in covered:
            start = i if start is None else start
        elif start is not None:
            found.extend(windows(path, language, lines[start:i], start, "module"))
            start = None
    return found

def chunk_file(path, text):
    """Splits a file by function and class where a grammar exists, otherwise into line windows."""
    lines = text.split("\n")
    ext = extension(path)
    if ext not in LANGUAGES:
        return windows(path, OTHER_LANGUAGES.get(ext) or NAMED_FILES.get(file_name(path), "text"), lines)

    language, grammar = LANGUAGES[ext]
    root = Parser(grammar).parse(text.encode("utf-8")).root_node
    chunks = []
    walk(root, path, language, lines, chunks)
    # Scripts with no definitions, or code the grammar couldn't read
    return chunks + module_chunks(path, language, lines, chunks) if chunks else windows(path, language, lines)
