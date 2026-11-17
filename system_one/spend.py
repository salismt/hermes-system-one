"""Spend guard: a SQLite ledger plus caps checked BEFORE a request is sent.

System One APIs bill input tokens only. ``estimate_tokens`` over-estimates on purpose (about 3
characters per token over the JSON body; real text runs about 3.5-4), so a cap trips early, not
late. After the call, the provider's reported ``usage.input_tokens`` is what gets recorded.

A cap <= 0 blocks every call. A cap of ``None`` means "no cap".
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

_LOCK = threading.Lock()



def usd(x: float) -> str:
    """Readable at decision-model prices: $0.50, $0.0000169 (never $0.0000)."""
    if x >= 0.01 or x <= 0:
        return f"${x:.2f}"
    return "$" + f"{float(f'{x:.3g}'):.10f}".rstrip("0")  # 3 significant digits, no exponent

class BudgetExceeded(RuntimeError):
    """Raised before sending. Callers must surface it as an error, never as an answer."""


@dataclass(frozen=True)
class Caps:
    total_usd: float | None = 5.00
    daily_usd: float | None = 0.50
    per_call_usd: float | None = 0.05
    utc_offset_hours: float = 0.0  # which calendar day "daily" means


def estimate_tokens(body: dict) -> int:
    return int(len(json.dumps(body, ensure_ascii=False)) / 3) + 50


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS spend(
                ts TEXT, day TEXT, tag TEXT, provider TEXT, model TEXT, request_id TEXT,
                est_tokens INTEGER, input_tokens INTEGER, usd REAL)""")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    @staticmethod
    def today(caps: Caps) -> str:
        return datetime.now(timezone(timedelta(hours=caps.utc_offset_hours))).strftime("%Y-%m-%d")

    def spent(self, day: str | None = None, tag_prefix: str | None = None) -> float:
        q, a = "SELECT COALESCE(SUM(usd),0) FROM spend WHERE 1=1", []
        if day:
            q += " AND day=?"; a.append(day)
        if tag_prefix:
            esc = tag_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            q += " AND tag LIKE ? ESCAPE '\\'"; a.append(esc + "%")
        with self._conn() as c:
            return float(c.execute(q, a).fetchone()[0])

    def by_provider(self) -> dict[str, float]:
        with self._conn() as c:
            return {p or "?": round(u, 6) for p, u in
                    c.execute("SELECT provider, SUM(usd) FROM spend GROUP BY provider")}

    def check(self, est_usd: float, caps: Caps, *, tag: str = "", run_cap_usd: float | None = None) -> None:
        if caps.per_call_usd is not None and est_usd > caps.per_call_usd:
            raise BudgetExceeded(f"per-call cap {usd(caps.per_call_usd)} (this call est. {usd(est_usd)})")
        total = self.spent()
        if caps.total_usd is not None and total + est_usd > caps.total_usd:
            raise BudgetExceeded(f"total cap {usd(caps.total_usd)} reached (spent {usd(total)})")
        day = self.spent(self.today(caps))
        if caps.daily_usd is not None and day + est_usd > caps.daily_usd:
            raise BudgetExceeded(f"daily cap {usd(caps.daily_usd)} reached (today {usd(day)})")
        if run_cap_usd is not None:
            run = self.spent(tag_prefix=tag)
            if run + est_usd > run_cap_usd:
                raise BudgetExceeded(f"run cap {usd(run_cap_usd)} for {tag!r} reached (spent {usd(run)})")

    def record(self, *, caps: Caps, tag: str, provider: str, model: str, request_id: str,
               est_tokens: int, input_tokens: int, usd: float) -> None:
        now = datetime.now(timezone(timedelta(hours=caps.utc_offset_hours)))
        with _LOCK, self._conn() as c:
            c.execute("INSERT INTO spend VALUES(?,?,?,?,?,?,?,?,?)",
                      (now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d"), tag, provider,
                       model, request_id, est_tokens, input_tokens, usd))
