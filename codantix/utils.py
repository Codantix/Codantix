from typing import Optional
from importlib import util


def _check_pkg(pkg: str, *, pkg_kebab: Optional[str] = None) -> None:
    if not util.find_spec(pkg):
        pkg_kebab = pkg_kebab if pkg_kebab is not None else pkg.replace("_", "-")
        raise ImportError(
            f"Unable to import {pkg}. Please install with `pip install -U {pkg_kebab}`"
        )