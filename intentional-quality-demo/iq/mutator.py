"""Generate mutants: one small, deliberate change per mutant, made on the AST."""
import ast
import copy
from dataclasses import dataclass

COMPARE_SWAPS = {ast.GtE: ast.Gt, ast.Gt: ast.GtE, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
BINOP_SWAPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Mult}
SYMBOL = {ast.GtE: ">=", ast.Gt: ">", ast.Lt: "<", ast.LtE: "<=", ast.Eq: "==", ast.NotEq: "!=",
          ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//"}


@dataclass
class Mutant:
    id: int
    function: str
    line: int
    operator: str          # e.g. "relational", "arithmetic", "conditional"
    description: str       # e.g. ">=  ->  >"
    original_line: str
    mutated_line: str
    source: str            # full mutated module source
    status: str = "pending"  # pending | killed | survived | equivalent
    killed_by: str = ""


def _sites(tree):
    """Yield (function_name, node, kind) for every mutable site inside top-level functions."""
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE_SWAPS:
                yield fn.name, node, "relational"
            elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_SWAPS:
                yield fn.name, node, "arithmetic"
            elif isinstance(node, ast.IfExp):
                yield fn.name, node, "conditional"


def generate(source: str) -> list[Mutant]:
    tree = ast.parse(source)
    lines = source.splitlines()
    sites = list(_sites(tree))
    mutants = []
    for i, (fname, node, kind) in enumerate(sites):
        t2 = copy.deepcopy(tree)
        target = list(_sites(t2))[i][1]
        if kind == "relational":
            old = type(target.ops[0]); new = COMPARE_SWAPS[old]
            target.ops[0] = new()
            desc = f"{SYMBOL[old]}  ->  {SYMBOL[new]}"
        elif kind == "arithmetic":
            old = type(target.op); new = BINOP_SWAPS[old]
            target.op = new()
            desc = f"{SYMBOL[old]}  ->  {SYMBOL[new]}"
        else:
            target.body, target.orelse = target.orelse, target.body
            desc = "swap if / else"
        new_src = ast.unparse(t2)
        new_lines = new_src.splitlines()
        orig_line = lines[node.lineno - 1].strip()
        mut_line = _matching_line(new_lines, orig_line, node, t2, target)
        mutants.append(Mutant(len(mutants) + 1, fname, node.lineno, kind, desc, orig_line, mut_line, new_src))
    return mutants


def _matching_line(new_lines, orig_line, node, tree, target):
    """Find the mutated statement's text for display."""
    seg = ast.unparse(target)
    for ln in new_lines:
        if seg in ln:
            return ln.strip()
    return seg
