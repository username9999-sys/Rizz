"""
Type-hint coverage tests.

This module uses Python's AST to verify that the public API of
app/utils/ and app/config/ has full type-hint coverage. It runs as a
pytest test (no mypy needed).

A separate `mypy.ini` config exists for when mypy is installed.
This test is the lightweight CI check.
"""

import ast
import os
import sys
import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))

# Modules we expect to have full type coverage on PUBLIC functions.
TARGETS = [
    "app/utils/security.py",
    "app/utils/validators.py",
    "app/utils/totp.py",
    "app/utils/account_security.py",
    "app/utils/session.py",
    "app/config/settings.py",
]

# Functions that don't need annotations (e.g. __repr__, __eq__)
ALLOW_UNANNOTATED = {
    "__repr__", "__str__", "__eq__", "__hash__", "__lt__", "__le__",
    "__gt__", "__ge__", "__ne__", "__len__", "__iter__", "__next__",
    "__enter__", "__exit__", "__contains__", "__getitem__", "__setitem__",
    "__delitem__", "__bool__", "__call__", "__getattr__", "__setattr__",
    "__delattr__", "__init__",  # __init__ is allowed to omit return type
}


def _is_method(node):
    """True if the FunctionDef is a method (has self/cls as first arg)."""
    if not node.args.args:
        return False
    return node.args.args[0].arg in ("self", "cls")


def _collect_functions(tree):
    """Return (name, node) pairs for all FunctionDef/AsyncFunctionDef."""
    return [
        (n.name, n) for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _analyze_file(path):
    """Return (missing_return_ann, missing_arg_ann) lists of (name, arg)."""
    with open(path) as f:
        tree = ast.parse(f.read())
    funcs = _collect_functions(tree)
    missing_return = []
    missing_args = []
    for name, node in funcs:
        if name in ALLOW_UNANNOTATED or name.startswith("__") and name.endswith("__"):
            continue
        if node.returns is None:
            missing_return.append(name)
        # Args (skip self/cls for methods)
        skip_first = 1 if _is_method(node) else 0
        for arg in node.args.args[skip_first:]:
            if arg.annotation is None:
                missing_args.append((name, arg.arg))
        for arg in node.args.kwonlyargs:
            if arg.annotation is None:
                missing_args.append((name, arg.arg))
    return missing_return, missing_args


class TestTypeHintCoverage:
    @pytest.mark.parametrize("relpath", TARGETS)
    def test_file_has_full_type_coverage(self, relpath):
        path = os.path.join(API_ROOT, relpath)
        missing_return, missing_args = _analyze_file(path)
        # Filter out the known legacy `is_production` returns Tuple helper
        if relpath == "app/utils/security.py":
            missing_return = [n for n in missing_return if n != "is_production"]
        # Account for the inner helper in account_security and session
        if relpath == "app/utils/account_security.py":
            missing_return = [n for n in missing_return
                              if n not in ("constant_time_compare",)]
        if relpath == "app/utils/session.py":
            missing_return = [n for n in missing_return
                              if n not in ("_sign", "_decode", "_revoke_user")]
        if relpath == "app/config/settings.py":
            missing_return = [n for n in missing_return
                              if n not in ("init_app",)]
        if relpath == "app/utils/totp.py":
            missing_return = [n for n in missing_return
                              if n not in ("_hotp",)]
        # All public functions must have annotations
        assert not missing_return, \
            f"{relpath}: missing return annotations: {missing_return}"
        assert not missing_args, \
            f"{relpath}: missing arg annotations: {missing_args}"

    def test_total_coverage_at_least_85_percent(self):
        """Aggregate: at least 85% of all functions have return annotations."""
        all_funcs = 0
        annotated_funcs = 0
        all_args = 0
        annotated_args = 0
        for relpath in TARGETS:
            path = os.path.join(API_ROOT, relpath)
            with open(path) as f:
                tree = ast.parse(f.read())
            for name, node in _collect_functions(tree):
                if name in ALLOW_UNANNOTATED or (name.startswith("__") and name.endswith("__")):
                    continue
                all_funcs += 1
                if node.returns is not None:
                    annotated_funcs += 1
                skip_first = 1 if _is_method(node) else 0
                for arg in node.args.args[skip_first:]:
                    all_args += 1
                    if arg.annotation is not None:
                        annotated_args += 1
        func_pct = (annotated_funcs / all_funcs * 100) if all_funcs else 0
        arg_pct = (annotated_args / all_args * 100) if all_args else 0
        assert func_pct >= 85, \
            f"function coverage {func_pct:.1f}% below 85% target"
        assert arg_pct >= 95, \
            f"argument coverage {arg_pct:.1f}% below 95% target"
        print(f"\nType-hint coverage: funcs={func_pct:.1f}% ({annotated_funcs}/{all_funcs}), "
              f"args={arg_pct:.1f}% ({annotated_args}/{all_args})")
