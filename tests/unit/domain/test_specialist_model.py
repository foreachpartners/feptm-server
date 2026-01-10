"""Unit tests for Specialist domain model."""

from datetime import date
from decimal import Decimal

import pytest

from feptm.domain.models.specialist import Rate, Specialist


class TestRate:
    """Tests for Rate dataclass."""

    def test_rate_creation(self) -> None:
        """Test creating a valid rate."""
        rate = Rate(
            internal=Decimal("12.00"),
            external=Decimal("14.00"),
            start_date=date(2025, 1, 1),
        )
        assert rate.internal == Decimal("12.00")
        assert rate.external == Decimal("14.00")
        assert rate.start_date == date(2025, 1, 1)
        assert rate.revenue_per_hour() == Decimal("2.00")

    def test_rate_validation_negative_internal(self) -> None:
        """Test rate validation rejects negative internal rate."""
        with pytest.raises(ValueError, match="Internal rate must be non-negative"):
            Rate(
                internal=Decimal("-1"),
                external=Decimal("10"),
                start_date=date(2025, 1, 1),
            )

    def test_rate_validation_external_less_than_internal(self) -> None:
        """Test rate validation rejects external rate less than internal."""
        with pytest.raises(
            ValueError, match="External rate.*must be >= internal rate"
        ):
            Rate(
                internal=Decimal("15"),
                external=Decimal("10"),
                start_date=date(2025, 1, 1),
            )


class TestSpecialist:
    """Tests for Specialist domain model."""

    def test_specialist_creation(self) -> None:
        """Test creating a specialist with rates."""
        rate1 = Rate(
            internal=Decimal("12"), external=Decimal("14"), start_date=date(2025, 1, 1)
        )
        rate2 = Rate(
            internal=Decimal("15"),
            external=Decimal("20"),
            start_date=date(2025, 3, 26),
        )

        specialist = Specialist(
            name="Mark",
            role="Developer",
            rates=[rate2, rate1],  # Out of order, should be sorted
        )

        assert specialist.name == "Mark"
        assert specialist.role == "Developer"
        assert len(specialist.rates) == 2
        # Rates should be sorted by start_date
        assert specialist.rates[0].start_date == date(2025, 1, 1)
        assert specialist.rates[1].start_date == date(2025, 3, 26)

    def test_get_rate_for_date(self) -> None:
        """Test getting rate for specific date (FR-002.1)."""
        rate1 = Rate(
            internal=Decimal("12"), external=Decimal("14"), start_date=date(2025, 1, 1)
        )
        rate2 = Rate(
            internal=Decimal("15"),
            external=Decimal("20"),
            start_date=date(2025, 3, 26),
        )

        specialist = Specialist(
            name="Mark", role="Developer", rates=[rate1, rate2]
        )

        # Date in first period
        rate = specialist.get_rate_for_date(date(2025, 3, 1))
        assert rate is not None
        assert rate.internal == Decimal("12")
        assert rate.external == Decimal("14")

        # Date in second period
        rate = specialist.get_rate_for_date(date(2025, 4, 1))
        assert rate is not None
        assert rate.internal == Decimal("15")
        assert rate.external == Decimal("20")

        # Date before any period
        rate = specialist.get_rate_for_date(date(2024, 12, 1))
        assert rate is None

    def test_add_rate(self) -> None:
        """Test adding a new rate period."""
        rate1 = Rate(
            internal=Decimal("12"), external=Decimal("14"), start_date=date(2025, 1, 1)
        )
        specialist = Specialist(name="Mark", role="Developer", rates=[rate1])

        rate2 = Rate(
            internal=Decimal("15"),
            external=Decimal("20"),
            start_date=date(2025, 3, 26),
        )
        specialist.add_rate(rate2)

        assert len(specialist.rates) == 2
        assert specialist.rates[0].start_date == date(2025, 1, 1)
        assert specialist.rates[1].start_date == date(2025, 3, 26)

    def test_add_rate_duplicate_date(self) -> None:
        """Test adding rate with duplicate start_date fails."""
        rate1 = Rate(
            internal=Decimal("12"), external=Decimal("14"), start_date=date(2025, 1, 1)
        )
        specialist = Specialist(name="Mark", role="Developer", rates=[rate1])

        rate2 = Rate(
            internal=Decimal("15"),
            external=Decimal("20"),
            start_date=date(2025, 1, 1),  # Duplicate date
        )

        with pytest.raises(ValueError, match="Rate with start_date.*already exists"):
            specialist.add_rate(rate2)

    def test_specialist_validation_empty_name(self) -> None:
        """Test specialist validation rejects empty name."""
        with pytest.raises(ValueError, match="Specialist name MUST NOT be empty"):
            Specialist(name="", role="Developer")
