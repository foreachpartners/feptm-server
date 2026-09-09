"""Storage for specialist-scoped spreadsheet operations."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from feptm.core import utils
from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    ColumnName,
    RangeFormat,
    SheetName,
)


class SpecialistStorage:
    """Storage for specialist listing, timesheet creation, and sheet updates."""

    def __init__(self, sheets_service: GoogleSheetsService) -> None:
        self._sheets = sheets_service

    def list_from_sheet(
        self, spreadsheet_id: str, sheet_name: str = SheetName.TEAM.value
    ) -> tuple[list[Specialist], int]:
        values, headers = self._read_sheet(spreadsheet_id, sheet_name)
        if not values or len(values) < 2:
            return [], 0

        self._validate_headers(headers)
        return self._parse_rows(values, headers)

    def create_timesheet(
        self, specialist: Specialist, context: TimesheetContext, template_id: str
    ) -> dict[str, str]:
        if not template_id:
            raise Exception("Timesheet template ID not configured")

        title = utils.generate_timesheet_title(specialist.name, context.project_name)

        existing_id = self._sheets.find_file_in_folder(context.folder_id, title)
        if existing_id:
            specialist.timesheet = existing_id
            log.info("Reusing existing timesheet for %s", specialist.name)
            return {
                "spreadsheet_id": existing_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{existing_id}",
            }

        result = self._sheets.ensure_spreadsheet_from_template(
            template_id=template_id, new_title=title, folder_id=context.folder_id
        )
        specialist.timesheet = result["spreadsheet_id"]
        log.info("Created timesheet for %s", specialist.name)
        return result

    def find_existing_timesheets(
        self, folder_id: str, specialist_names: list[str], project_name: str
    ) -> dict[str, str]:
        all_files = self._sheets.list_drive_spreadsheets(folder_id)
        file_map = {f["name"]: f["id"] for f in all_files}

        result: dict[str, str] = {}
        for name in specialist_names:
            title = utils.generate_timesheet_title(name, project_name)
            if title in file_map:
                result[name] = file_map[title]
        return result

    def update_timesheet_ids(
        self, spreadsheet_id: str, sheet_name: str, specialists: list[Specialist]
    ) -> bool:
        updates, headers = self._prepare_updates(spreadsheet_id, sheet_name, specialists)
        if not updates:
            return True

        self._apply_updates(spreadsheet_id, sheet_name, updates, headers)
        return True

    def _read_sheet(
        self, spreadsheet_id: str, sheet_name: str
    ) -> tuple[list[list], list[str]]:
        sheet = self._sheets.get_sheet_by_name(spreadsheet_id, sheet_name)
        if not sheet:
            return [], []

        values, headers = self._sheets.get_sheet_data_with_headers(
            spreadsheet_id, sheet_name, RangeFormat.SPECIALIST_DATA.value
        )
        return values, headers

    def _validate_headers(self, headers: list[str]) -> None:
        name_idx = self._sheets.find_column_index(headers, [ColumnName.NAME.value])
        role_idx = self._sheets.find_column_index(headers, [ColumnName.ROLE.value])
        missing = []
        if name_idx is None:
            missing.append(ColumnName.NAME.value)
        if role_idx is None:
            missing.append(ColumnName.ROLE.value)
        if missing:
            raise Exception(
                f"Required columns missing in specialists sheet: {', '.join(missing)}"
            )

    def _parse_rows(
        self, values: list[list], headers: list[str]
    ) -> tuple[list[Specialist], int]:
        headers_map = self._build_map(headers)
        specialists: list[Specialist] = []
        existing_count = 0

        for i, row in enumerate(values[1:]):
            name_idx = headers_map["name"]
            role_idx = headers_map["role"]
            if name_idx is None or role_idx is None:
                raise Exception(
                    "Required columns 'name' or 'role' not found after validation"
                )
            if not row or len(row) <= max(name_idx, role_idx):
                continue

            sp = self._parse_row(row, headers_map, row_number=i + 2)
            if sp:
                specialists.append(sp)
                if sp.timesheet:
                    existing_count += 1

        return specialists, existing_count

    def _build_map(self, headers: list[str]) -> dict[str, int | None]:
        return {
            "name": self._sheets.find_column_index(headers, [ColumnName.NAME.value]),
            "role": self._sheets.find_column_index(headers, [ColumnName.ROLE.value]),
            "project": self._sheets.find_column_index(
                headers, [ColumnName.PROJECT.value]
            ),
            "internal_rate": self._sheets.find_column_index(
                headers, [ColumnName.INTERNAL_RATE.value]
            ),
            "external_rate": self._sheets.find_column_index(
                headers, [ColumnName.EXTERNAL_RATE.value]
            ),
            "date": self._sheets.find_column_index(headers, [ColumnName.DATE.value]),
            "timesheet": self._sheets.find_column_index(
                headers, [ColumnName.TIMESHEET.value]
            ),
        }

    def _parse_row(self, row: list, hmap: dict[str, int | None], row_number: int | None = None) -> Specialist | None:
        name = (
            str(row[hmap["name"]]).strip()
            if hmap["name"] is not None and hmap["name"] < len(row)
            else ""
        )
        role = (
            str(row[hmap["role"]]).strip()
            if hmap["role"] is not None and hmap["role"] < len(row)
            else ""
        )
        if not name or not role:
            return None

        project = _opt(row, hmap.get("project"))
        date_val = None
        date_raw = _opt(row, hmap.get("date"))
        if date_raw:
            try:
                date_val = _serial_from_number(float(date_raw))
            except (ValueError, TypeError):
                pass
            if date_val is None:
                log.error("Invalid date value for %s: %s", name, date_raw)
        internal_rate = _parse_decimal(
            row, hmap.get("internal_rate"), name, "internal rate"
        )
        external_rate = _parse_decimal(
            row, hmap.get("external_rate"), name, "external rate"
        )
        timesheet_raw = _opt(row, hmap.get("timesheet"))
        timesheet = utils.extract_id_from_hyperlink_formula(timesheet_raw or "") or timesheet_raw

        return Specialist(
            name=name,
            role=role,
            project=project,
            internal_rate=internal_rate,
            external_rate=external_rate,
            date=date_val,
            timesheet=timesheet,
            row_index=row_number,
        )

    def _prepare_updates(
        self, spreadsheet_id: str, sheet_name: str, specialists: list[Specialist]
    ) -> tuple[list[tuple[int, str]], list[str]]:
        values, headers = self._sheets.get_sheet_data_with_headers(
            spreadsheet_id, sheet_name, RangeFormat.SPECIALIST_DATA.value
        )
        if not values:
            return [], []

        timesheet_col = self._sheets.find_column_index(
            headers, [ColumnName.TIMESHEET.value]
        )
        if timesheet_col is None:
            return [], []

        updates: list[tuple[int, str]] = []
        for sp in specialists:
            if not sp.timesheet:
                continue
            if sp.row_index is not None:
                updates.append((sp.row_index, sp.timesheet))
        return updates, headers

    def _apply_updates(
        self, spreadsheet_id: str, sheet_name: str, updates: list[tuple[int, str]], headers: list[str]
    ) -> None:
        sheet = self._sheets.get_sheet_by_name(spreadsheet_id, sheet_name)
        if not sheet:
            raise Exception(f"Sheet '{sheet_name}' not found")

        sheet_id = sheet.get("properties", {}).get("sheetId")

        timesheet_col = self._sheets.find_column_index(
            headers, [ColumnName.TIMESHEET.value]
        )
        if timesheet_col is None:
            raise Exception("Timesheet column not found")

        requests: list[dict[str, Any]] = []
        for row_idx, ts_id in updates:
            if "spreadsheets/d/" not in ts_id:
                ts_id = f"https://docs.google.com/spreadsheets/d/{ts_id}"
            requests.append(
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx - 1,
                            "endRowIndex": row_idx,
                            "startColumnIndex": timesheet_col,
                            "endColumnIndex": timesheet_col + 1,
                        },
                        "rows": [
                            {
                                "values": [
                                    {"userEnteredValue": {"stringValue": ts_id}}
                                ]
                            }
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            )
        if requests:
            self._sheets.batch_update(spreadsheet_id, requests)


def _opt(row: list, idx: int | None) -> str | None:
    if idx is not None and idx < len(row):
        return utils.clean_string_value(row[idx])
    return None


_GSHEETS_EPOCH = datetime(1899, 12, 30)


def _serial_from_number(value: int | float) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return (_GSHEETS_EPOCH + timedelta(days=int(value))).replace(
            tzinfo=None
        )
    return None


def _parse_decimal(row: list, idx: int | None, name: str, field: str) -> Decimal | None:
    if idx is None or idx >= len(row):
        return None
    rate_str = str(row[idx]).strip()
    if not rate_str:
        return None
    try:
        cleaned = rate_str.replace(",", ".")
        return Decimal(cleaned)
    except Exception:
        log.warning("Invalid %s value for %s: '%s'", field, name, rate_str)
        return None
