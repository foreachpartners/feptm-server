"""Tests for payment period models."""

import pytest
from pydantic import ValidationError

from feptm.models.payment_period import ClosePeriodRequest, ClosePeriodResponse


class TestClosePeriodRequest:
    def test_valid_request(self):
        req = ClosePeriodRequest(
            project_id="test-project",
            period_name="January 2026",
        )
        assert req.project_id == "test-project"
        assert req.period_name == "January 2026"

    def test_empty_project_id_raises(self):
        with pytest.raises(ValidationError):
            ClosePeriodRequest(
                project_id="",
                period_name="Q1",
            )

    def test_empty_period_name_raises(self):
        with pytest.raises(ValidationError):
            ClosePeriodRequest(
                project_id="test",
                period_name="",
            )


class TestClosePeriodResponse:
    def test_serialization(self):
        resp = ClosePeriodResponse(
            project_id="test",
            period_name="Q1",
            entries_updated=5,
            specialists_processed=3,
            report_archived=True,
            calculations_archived=True,
        )
        data = resp.model_dump(mode="json")
        assert data["project_id"] == "test"
        assert data["period_name"] == "Q1"
        assert data["entries_updated"] == 5
        assert data["specialists_processed"] == 3
        assert data["report_archived"] is True
        assert data["calculations_archived"] is True
        assert "created" in data
