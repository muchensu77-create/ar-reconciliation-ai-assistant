from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReconciliationConfig:
    """Business-tunable reconciliation settings."""

    amount_tolerance: float = 0.01
    date_window_days: int = 45
    grouped_receipt_max_size: int = 4
    partial_payment_min_ratio: float = 0.35
    high_value_threshold: float = 10000.0
    medium_value_threshold: float = 5000.0
    aging_buckets: tuple[tuple[str, int | None, int | None], ...] = field(
        default=(
            ("not_due", None, 0),
            ("0_30", 1, 30),
            ("31_60", 31, 60),
            ("61_90", 61, 90),
            ("over_90", 91, None),
        )
    )

    @property
    def aging_order(self) -> list[str]:
        return [bucket[0] for bucket in self.aging_buckets]

