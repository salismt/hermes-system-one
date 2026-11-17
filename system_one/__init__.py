"""Provider-neutral client for System One decision models (TypeSafe Jev, Liquid d1.2, ...)."""
__version__ = "0.1.0"

from .client import SystemOne, Settings, SystemOneError, build_body, simplify  # noqa: E402
from .providers import BUILTIN, resolve  # noqa: E402
from .spend import BudgetExceeded, Caps, Ledger  # noqa: E402

__all__ = ["SystemOne", "Settings", "Caps", "Ledger", "BudgetExceeded", "SystemOneError",
           "BUILTIN", "resolve", "build_body", "simplify", "__version__"]
