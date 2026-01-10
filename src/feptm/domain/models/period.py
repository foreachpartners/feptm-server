"""Domain models for payment periods."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PaymentPeriod:
    """Payment period for invoicing.

    Attributes:
        name: Period name (e.g., "January 2026")
        start_date: Period start date
        end_date: Period end date
    """

    name: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        """Validate period data."""
        if not self.name.strip():
            raise ValueError("Payment period name MUST NOT be empty")
        if self.end_date < self.start_date:
            raise ValueError(
                f"End date ({self.end_date}) must be >= start date ({self.start_date})"
            )

    def contains_date(self, target_date: date) -> bool:
        """Check if period contains a date.

        Args:
            target_date: Date to check

        Returns:
            True if date is within period range
        """
        return self.start_date <= target_date <= self.end_date
