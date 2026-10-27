"""Run the test suite against the original module or a mutant, in-process and fast."""
import sys
import types
from dataclasses import dataclass, field

MODULE_NAME = "pricing"


def load_module(source: str, name: str = MODULE_NAME) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = f"{name}.py"
    exec(compile(source, f"{name}.py", "exec"), mod.__dict__)
    return mod


@dataclass
class SuiteResult:
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)  # (test_name, error)

    @property
    def green(self):
        return not self.failed


def run_suite(module_source: str, test_sources: list[str]) -> SuiteResult:
    """Execute every test_* function from the given test sources against module_source."""
    mod = load_module(module_source)
    saved = sys.modules.get(MODULE_NAME)
    sys.modules[MODULE_NAME] = mod
    result = SuiteResult()
    try:
        for src in test_sources:
            ns: dict = {}
            exec(compile(src, "test_pricing.py", "exec"), ns)
            for name, fn in ns.items():
                if name.startswith("test_") and callable(fn):
                    try:
                        fn()
                        result.passed.append(name)
                    except Exception as e:  # a failing test kills the mutant
                        result.failed.append((name, f"{type(e).__name__}: {e}"))
    finally:
        if saved is not None:
            sys.modules[MODULE_NAME] = saved
        else:
            sys.modules.pop(MODULE_NAME, None)
    return result


def line_coverage(module_source: str, test_sources: list[str]):
    """Return (covered_lines, executable_lines) for the module under the given tests."""
    code = compile(module_source, "pricing.py", "exec")
    executable = set()

    def collect(co):
        for _, _, ln in co.co_lines():
            if ln is not None:
                executable.add(ln)
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                collect(c)

    for c in code.co_consts:  # function bodies only, not module-level def lines
        if isinstance(c, types.CodeType):
            collect(c)
    # drop def lines and docstring lines (not meaningful for coverage)
    lines = module_source.splitlines()
    executable = {ln for ln in executable
                  if not lines[ln - 1].strip().startswith(("def ", '"""'))}

    covered = set()

    def tracer(frame, event, arg):
        if frame.f_code.co_filename == "pricing.py":
            if event == "line":
                covered.add(frame.f_lineno)
            return tracer
        return None

    sys.settrace(tracer)
    try:
        run_suite(module_source, test_sources)
    finally:
        sys.settrace(None)
    return covered & executable, executable
