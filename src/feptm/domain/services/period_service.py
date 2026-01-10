"""Payment period domain service."""

from feptm.domain.models.period import PaymentPeriod
from feptm.domain.services.protocols import PeriodRepository


class PeriodService:
    """Service for payment period operations.

    Handles period closing and related operations.
    """

    def __init__(self, repository: PeriodRepository) -> None:
        """Initialize PeriodService.

        Args:
            repository: Period repository implementation
        """
        self._repository = repository

    def close_period(self, project_id: str, period: PaymentPeriod) -> None:
        """Close payment period for project.

        FR-004: Period close operation. In future versions, this may
        automate period name propagation and snapshot creation.

        Args:
            project_id: External project ID
            period: Payment period to close

        Raises:
            NotFoundError: If project not found
            ValidationError: If period data is invalid
            GoogleApiError: If period close operation fails
        """
        from feptm.core.exceptions import ValidationError

        # Validate period
        if not period.name or not period.name.strip():
            raise ValidationError("Payment period name MUST NOT be empty")

        if period.end_date < period.start_date:
            raise ValidationError(
                f"Period end date ({period.end_date}) must be >= start date ({period.start_date})"
            )

        self._repository.close_period(project_id, period)
