"""Provider-neutral client for System One decision models (TypeSafe Jev, Liquid d1.2, ...)."""
__version__ = "0.3.0"

from .client import SystemOne, Settings, SystemOneError, build_body, simplify  # noqa: E402
from .providers import BUILTIN, Capabilities, UnsupportedRequest, resolve  # noqa: E402
from .questions import box, choice, noul, question, score  # noqa: E402
from .spend import BudgetExceeded, Caps, Ledger  # noqa: E402

__all__ = ["SystemOne", "Settings", "Caps", "Ledger", "BudgetExceeded", "SystemOneError", "UnsupportedRequest",
           "Capabilities", "BUILTIN", "resolve", "build_body", "simplify",
           "noul", "choice", "score", "box", "question", "__version__"]
