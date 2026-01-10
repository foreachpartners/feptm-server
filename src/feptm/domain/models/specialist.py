"""Domain models for specialists and rates."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List


@dataclass(frozen=True)
class Rate:
    """Hourly rate for a specialist during a specific period.

    FR-002.1: Rate periods support multiple rates per specialist over time.
    Each rate is valid from start_date until the next period starts.

    Attributes:
        internal: Rate paid to specialist
        external: Rate charged to client
        start_date: Date from which this rate applies (FR-002.1)
    """

    internal: Decimal  # Rate paid to specialist
    external: Decimal  # Rate charged to client
    start_date: date  # FR-002.1: Rate period start

    def revenue_per_hour(self) -> Decimal:
        """Calculate revenue per hour.

        Returns:
            Revenue per hour (external - internal)
        """
        return self.external - self.internal

    def __post_init__(self) -> None:
        """Validate rate values."""
        if self.internal < 0:
            raise ValueError(f"Internal rate must be non-negative, got {self.internal}")
        if self.external < 0:
            raise ValueError(f"External rate must be non-negative, got {self.external}")
        if self.external < self.internal:
            raise ValueError(
                f"External rate ({self.external}) must be >= internal rate ({self.internal})"
            )


@dataclass
class Specialist:
    """Team member with timesheet and rate periods.

    FR-002.1: Specialists can have multiple rate periods (rows in Team sheet
    with same Timesheet ID represent rate history).

    Attributes:
        name: Specialist display name
        role: Job function (Developer, QA, Manager, etc.)
        rates: List of rate periods, sorted by start_date ascending
        joined_date: Date when specialist joined the project
    """

    name: str
    role: str
    rates: List[Rate] = field(default_factory=list)
    joined_date: date = field(default_factory=date.today)

    def get_rate_for_date(self, target_date: date) -> Rate | None:
        """Get applicable rate for a specific date.

        FR-002.1: Rate lookup finds applicable period by matching
        target_date against rate start_date.

        Args:
            target_date: Date to find rate for

        Returns:
            Applicable Rate or None if no rate period covers the date
        """
        # Sort rates by start_date descending to find most recent applicable rate
        applicable_rates = [
            rate for rate in sorted(self.rates, key=lambda r: r.start_date, reverse=True)
            if rate.start_date <= target_date
        ]
        return applicable_rates[0] if applicable_rates else None

    def add_rate(self, rate: Rate) -> None:
        """Add a new rate period.

        Args:
            rate: Rate to add

        Raises:
            ValueError: If rate with same start_date already exists
        """
        # Check for duplicate start_date
        if any(r.start_date == rate.start_date for r in self.rates):
            raise ValueError(
                f"Rate with start_date {rate.start_date} already exists for specialist {self.name}"
            )
        self.rates.append(rate)
        # Keep rates sorted by start_date
        self.rates.sort(key=lambda r: r.start_date)

    def __post_init__(self) -> None:
        """Validate specialist data."""
        if not self.name.strip():
            raise ValueError("Specialist name MUST NOT be empty")
        if not self.role.strip():
            raise ValueError("Specialist role MUST NOT be empty")
        # Sort rates by start_date
        self.rates.sort(key=lambda r: r.start_date)
