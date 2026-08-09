"""Storage for project-scoped spreadsheet operations."""

from datetime import datetime, timedelta, timezone
from typing import Any

from feptm.core import utils
from feptm.core.log import log
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    ColumnName,
    DateFormat,
    FormulaName,
    RangeFormat,
    RowName,
    SheetName,
    UrlPattern,
)


class ProjectStorage:
    """Storage for project creation, metadata, and sheet manipulation."""

    MAX_COLUMN_INDEX = 26

    def __init__(self, sheets_service: GoogleSheetsService) -> None:
        self._sheets = sheets_service

    def create_project(
        self,
        project_name: str,
        template_ids: dict[str, str],
        parent_folder_id: str | None,
    ) -> dict[str, str]:
        if not self._sheets.is_initialized():
            raise Exception("Google services are not initialized.")

        project_folder_id: str | None = None
        try:
            if parent_folder_id:
                try:
                    parent_folder = self._sheets.get_file(parent_folder_id)
                    log.info(
                        "Parent folder found: %s (ID: %s)",
                        parent_folder.get("name"),
                        parent_folder.get("id"),
                    )
                except Exception as exc:
                    raise Exception(
                        f"Parent folder with ID {parent_folder_id} not found or not accessible: {exc}"
                    ) from exc

                folder_info = self._sheets.create_drive_folder(
                    project_name, parent_folder_id
                )
            else:
                folder_info = self._sheets.create_drive_folder(project_name)

            project_folder_id = folder_info["folder_id"]
            log.info(
                "Created project folder: %s (ID: %s)", project_name, project_folder_id
            )

            spreadsheets: dict[str, dict[str, str]] = {}
            for key, template_id in template_ids.items():
                title = _spreadsheet_title(project_name, key)
                spreadsheets[key] = self._create_from_template(
                    template_id, title, project_folder_id
                )

            return {
                "drive_folder_id": project_folder_id,
                "drive_folder_url": folder_info["folder_url"],
                **{
                    f"{k}_spreadsheet_id": v["spreadsheet_id"]
                    for k, v in spreadsheets.items()
                },
                **{
                    f"{k}_spreadsheet_url": v["spreadsheet_url"]
                    for k, v in spreadsheets.items()
                },
            }
        except Exception:
            if project_folder_id is not None:
                try:
                    self._sheets.delete_file(project_folder_id)
                    log.warning("Cleaned up folder %s after error", project_folder_id)
                except Exception as cleanup_error:
                    log.error("Failed to clean up: %s", cleanup_error)
            raise

    def update_project_info_sheet(self, spreadsheet_id: str, project: Project) -> None:
        project_data: list[list[Any]] = [
            ["Project Information", ""],
            [RowName.FIELD.value, RowName.VALUE.value],
            [
                RowName.PROJECT_ID.value,
                project.project_info_spreadsheet_id or "Not assigned yet",
            ],
            [RowName.NAME.value, project.name],
            [
                RowName.CREATED.value,
                datetime.strftime(project.created, DateFormat.DISPLAY_DATETIME.value),
            ],
            [
                RowName.MODIFIED.value,
                datetime.strftime(project.modified, DateFormat.DISPLAY_DATETIME.value),
            ],
        ]

        folder_url = (
            UrlPattern.DRIVE_FOLDER.format(folder_id=project.drive_folder_id)
            if project.drive_folder_id
            else ""
        )
        project_data.append([RowName.PROJECT_FOLDER.value, _hyperlink(folder_url)])

        if project.calculations_spreadsheet_id:
            calc_url = UrlPattern.SPREADSHEET.format(
                spreadsheet_id=project.calculations_spreadsheet_id
            )
            project_data.append(
                [RowName.PAYMENT_DISTRIBUTION.value, _hyperlink(calc_url)]
            )

        if project.report_spreadsheet_id:
            report_url = UrlPattern.SPREADSHEET.format(
                spreadsheet_id=project.report_spreadsheet_id
            )
            project_data.append(
                [RowName.GENERAL_EXPENSES.value, _hyperlink(report_url)]
            )

        self._sheets.update_sheet_data(
            spreadsheet_id=spreadsheet_id,
            sheet_name=SheetName.PROJECT_INFO.value,
            data=project_data,
        )

    def get_project_metadata(self, project_id: str) -> Project:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheet = self._sheets.get_sheet_by_name(
            spreadsheet_id=project_id, sheet_name=SheetName.PROJECT_INFO.value
        )
        if not sheet:
            raise Exception("Project info sheet not found")

        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=project_id, range=RangeFormat.PROJECT_INFO.value)
            .execute()
        )
        values: list[list] = result.get("values", [])
        if not values:
            raise Exception("No data found in project info sheet")

        project_name = ""
        drive_folder_id: str | None = None
        report_spreadsheet_id: str | None = None
        calculations_spreadsheet_id: str | None = None

        for row in values:
            if len(row) < 2:
                continue
            field = row[0].strip()
            value = row[1].strip()

            if field == RowName.NAME.value:
                project_name = value
            elif field == RowName.PROJECT_FOLDER.value:
                drive_folder_id = utils.extract_id_from_hyperlink_formula(value)
            elif field == RowName.GENERAL_EXPENSES.value:
                report_spreadsheet_id = utils.extract_id_from_hyperlink_formula(value)
            elif field == RowName.PAYMENT_DISTRIBUTION.value:
                calculations_spreadsheet_id = utils.extract_id_from_hyperlink_formula(
                    value
                )

        if not project_name:
            raise Exception("Project name not found in project info sheet")

        if not drive_folder_id:
            try:
                file_info = self._sheets.get_file(project_id)
                parents = file_info.get("parents", [])
                if parents:
                    drive_folder_id = parents[0]
            except Exception as exc:
                log.warning("Failed to get drive folder ID from file metadata: %s", exc)

        return Project(
            name=project_name,
            drive_folder_id=drive_folder_id,
            project_info_spreadsheet_id=project_id,
            report_spreadsheet_id=report_spreadsheet_id,
            calculations_spreadsheet_id=calculations_spreadsheet_id,
        )

    def add_specialist_to_report(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
        import_formula: str,
    ) -> None:
        tab_name = specialist.display_name or specialist.name
        existing = self._list_sheet_titles(spreadsheet_id)
        if tab_name not in existing:
            self._sheets.batch_update(
                spreadsheet_id=spreadsheet_id,
                requests=[{"addSheet": {"properties": {"title": tab_name}}}],
            )
            self._sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )
            log.info("Created tab for %s in spreadsheet", specialist.name)

    def update_current_period(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
        formula_provider: Any,
    ) -> None:
        sheet_name = SheetName.CURRENT_PERIOD.value
        sheet_data = self._read_current_period(spreadsheet_id, sheet_name)
        if not sheet_data:
            return

        values, headers, sheet = sheet_data

        if _specialist_in_sheet(values, headers, specialist.display_name or specialist.name, self._sheets):
            log.info("Specialist %s already exists in Current Period", specialist.display_name or specialist.name)
            return

        insert_row, should_insert = _find_insert_position(values, headers, self._sheets)

        self._insert_and_update_row(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            sheet=sheet,
            insert_row=insert_row,
            should_insert=should_insert,
            specialist=specialist,
            headers=headers,
            values=values,
            formula_provider=formula_provider,
        )
        log.info("Added %s to %s tab", specialist.name, sheet_name)

    def sync_rates_to_current_period(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
    ) -> None:
        sheet_name = SheetName.CURRENT_PERIOD.value
        sheet_data = self._read_current_period(spreadsheet_id, sheet_name)
        if not sheet_data:
            return
        values, headers, _ = sheet_data
        target_row = _find_specialist_row(
            values, headers, specialist.display_name or specialist.name, self._sheets
        )
        if target_row is None:
            return
        _write_specialist_fields(
            self._sheets, spreadsheet_id, sheet_name, target_row, specialist, headers
        )

    def _create_from_template(
        self, template_id: str, new_title: str, folder_id: str
    ) -> dict[str, str]:
        if not template_id:
            raise Exception("Template ID is not configured")
        result = self._sheets.ensure_spreadsheet_from_template(
            template_id=template_id, new_title=new_title, folder_id=folder_id
        )
        log.info(
            "Created spreadsheet: %s (ID: %s)", new_title, result.get("spreadsheet_id")
        )
        return result

    def _list_sheet_titles(self, spreadsheet_id: str) -> list[str]:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")
        spreadsheet = (
            self._sheets.sheets_service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )
        return [
            s.get("properties", {}).get("title", "")
            for s in spreadsheet.get("sheets", [])
        ]

    def _read_current_period(
        self, spreadsheet_id: str, sheet_name: str
    ) -> tuple[list[list], list[str], dict] | None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheet = self._sheets.get_sheet_by_name(spreadsheet_id, sheet_name)
        if not sheet:
            return None

        range_name = RangeFormat.CURRENT_PERIOD.value.format(sheet_name=sheet_name)
        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values: list[list] = result.get("values", [])
        if not values:
            return None
        return values, values[0], sheet

    def _insert_and_update_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        sheet: dict,
        insert_row: int,
        should_insert: bool,
        specialist: Specialist,
        headers: list[str],
        values: list[list],
        formula_provider: Any,
    ) -> None:
        sheet_id = sheet.get("properties", {}).get("sheetId")
        target_row = insert_row + 1

        if should_insert:
            try:
                self._sheets.batch_update(
                    spreadsheet_id=spreadsheet_id,
                    requests=[
                        {
                            "insertDimension": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "ROWS",
                                    "startIndex": insert_row,
                                    "endIndex": insert_row + 1,
                                },
                                "inheritFromBefore": True,
                            }
                        }
                    ],
                )
            except Exception as exc:
                log.warning("Failed to insert row, continuing: %s", exc)

        template_row = _find_template_row(values, headers, self._sheets)
        if template_row is not None:
            try:
                self._copy_row_formatting(
                    spreadsheet_id, sheet_name, template_row, target_row
                )
            except Exception as exc:
                log.warning("Failed to copy template: %s", exc)
        else:
            try:
                _add_formulas_for_row(
                    self._sheets,
                    spreadsheet_id,
                    sheet_name,
                    target_row,
                    headers,
                    formula_provider,
                )
            except Exception as exc:
                log.warning("Failed to add formulas: %s", exc)

        _write_specialist_fields(
            self._sheets, spreadsheet_id, sheet_name, target_row, specialist, headers
        )

    def _copy_row_formatting(
        self, spreadsheet_id: str, sheet_name: str, source_row: int, target_row: int
    ) -> None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        spreadsheet = (
            self._sheets.sheets_service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )
        sheet_id = None
        for s in spreadsheet.get("sheets", []):
            if s.get("properties", {}).get("title") == sheet_name:
                sheet_id = s.get("properties", {}).get("sheetId")
                break
        if not sheet_id:
            raise Exception(f"Sheet ID not found for '{sheet_name}'")

        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[
                {
                    "copyPaste": {
                        "source": {
                            "sheetId": sheet_id,
                            "startRowIndex": source_row - 1,
                            "endRowIndex": source_row,
                            "startColumnIndex": 0,
                            "endColumnIndex": self.MAX_COLUMN_INDEX,
                        },
                        "destination": {
                            "sheetId": sheet_id,
                            "startRowIndex": target_row - 1,
                            "endRowIndex": target_row,
                            "startColumnIndex": 0,
                            "endColumnIndex": self.MAX_COLUMN_INDEX,
                        },
                        "pasteType": "PASTE_NORMAL",
                        "pasteOrientation": "NORMAL",
                    }
                }
            ],
        )
        log.info("Copied row %d to row %d", source_row, target_row)

    def close_period_in_timesheet(
        self,
        timesheet_id: str,
        period_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        spreadsheet = (
            self._sheets.sheets_service.spreadsheets()
            .get(spreadsheetId=timesheet_id)
            .execute()
        )
        sheets_list = spreadsheet.get("sheets", [])
        if not sheets_list:
            return 0
        sheet_name = sheets_list[0].get("properties", {}).get("title", "")
        if not sheet_name:
            return 0

        range_name = RangeFormat.TIMESHEET_DATA.value.format(sheet_name=sheet_name)
        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=timesheet_id,
                range=range_name,
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values: list[list] = result.get("values", [])
        if not values or len(values) < 2:
            return 0

        headers = values[0]
        date_col = self._sheets.find_column_index(headers, [ColumnName.DATE.value])
        period_col = self._sheets.find_column_index(
            headers, [ColumnName.PAYMENT_PERIOD.value]
        )
        if period_col is None:
            period_col = _find_column_contains(
                headers, ColumnName.PAYMENT_PERIOD.value
            )
        if date_col is None or period_col is None:
            log.warning(
                "Timesheet %s: missing columns. headers=%s, Date found=%s, Payment Period found=%s",
                timesheet_id, headers,
                date_col is not None, period_col is not None,
            )
            return 0

        updates = 0
        for i in range(1, len(values)):
            row = values[i]
            if len(row) <= date_col:
                continue
            date_val = row[date_col]
            parsed = _serial_to_date(date_val)
            if parsed is None:
                continue
            if parsed < start_date or parsed > end_date:
                continue
            period_cell = row[period_col] if len(row) > period_col else ""
            if period_cell and str(period_cell).strip():
                continue
            col_letter = self._sheets.column_index_to_letter(period_col)
            try:
                self._sheets.update_range(
                    spreadsheet_id=timesheet_id,
                    range_name=f"{sheet_name}!{col_letter}{i + 1}",
                    values=[[period_name]],
                    value_input_option="RAW",
                )
                updates += 1
            except Exception as exc:
                log.warning("Failed to update Payment Period for row %d: %s", i + 1, exc)

        log.info(
            "Updated %d entries in timesheet %s for period %s",
            updates,
            timesheet_id,
            period_name,
        )
        return updates

    def archive_current_period(
        self,
        spreadsheet_id: str,
        period_name: str,
        specialists: list[Specialist],
        start_date: datetime,
        end_date: datetime,
    ) -> bool:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        existing = self._list_sheet_titles(spreadsheet_id)
        if period_name in existing:
            log.info("Archived tab %s already exists, skipping", period_name)
            return False

        cp_data = self._read_current_period(
            spreadsheet_id, SheetName.CURRENT_PERIOD.value
        )
        if not cp_data:
            return False
        values, headers, _ = cp_data

        sp_map = {
            sp.display_name or sp.name: sp
            for sp in specialists
            if sp.timesheet
        }

        archive = [list(headers)]
        num_cols = len(headers)
        seen_bases: set[str] = set()

        import re

        for row in values[1:]:
            _pad_row(row, num_cols)
            sp_name = row[0] if row else ""

            sp = sp_map.get(sp_name)
            if sp is None:
                base = re.sub(r"\s+\(\d+\)$", "", sp_name)
                if base != sp_name:
                    sp = sp_map.get(base)

            if sp is None:
                archive.append(list(row))
                continue

            canonical = sp.display_name or sp.name or sp_name
            base_name = re.sub(r"\s+\(\d+\)$", "", canonical)
            if base_name in seen_bases:
                continue

            if canonical != sp_name:
                sp_name = canonical
                _pad_row(row, 1)
                row[0] = canonical

            timesheet_id = sp.timesheet or ""
            if not timesheet_id:
                archive.append(list(row))
                continue

            hours = self._sum_timesheet_hours(timesheet_id, start_date, end_date)
            if hours <= 0:
                archive.append(list(row))
                continue

            seen_bases.add(base_name)

            cl_rate = float(sp.external_rate)
            sp_rate = float(sp.internal_rate)
            cl_cost = round(hours * cl_rate, 2)
            sp_cost = round(hours * sp_rate, 2)
            revenue = round(cl_cost - sp_cost, 2)

            new_row = list(row)
            for col_name, val in [
                (ColumnName.HOURS_WORKED.value, str(hours)),
                (ColumnName.CLIENT_HOURLY_RATE_USD.value, str(cl_rate)),
                (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, str(sp_rate)),
                (ColumnName.CLIENT_WORK_COST_USD.value, str(cl_cost)),
                (ColumnName.SPECIALIST_WORK_COST_USD.value, str(sp_cost)),
                (ColumnName.REVENUE_USD.value, str(revenue)),
            ]:
                col_idx = _find_column_contains(headers, col_name)
                if col_idx is not None:
                    _pad_row(new_row, col_idx + 1)
                    new_row[col_idx] = val
            archive.append(new_row)

        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[{"addSheet": {"properties": {"title": period_name}}}],
        )
        new_range = RangeFormat.CURRENT_PERIOD.value.format(
            sheet_name=period_name
        )
        self._sheets.update_range(
            spreadsheet_id=spreadsheet_id,
            range_name=new_range,
            values=archive,
            value_input_option="RAW",
        )
        log.info("Archived Current Period as %s in spreadsheet", period_name)
        return True

    def _extract_timesheet_id_from_tab(
        self,
        spreadsheet_id: str,
        tab_name: str,
    ) -> str | None:
        if not self._sheets.sheets_service:
            return None
        try:
            result = (
                self._sheets.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=f"{tab_name}!A1",
                    valueRenderOption="FORMULA",
                )
                .execute()
            )
            vals = result.get("values", [])
            if not vals or not vals[0]:
                return None
            formula = str(vals[0][0])
            import re
            m = re.search(r'IMPORTRANGE\s*\(\s*"([^"]+)"', formula)
            return m.group(1) if m else None
        except Exception as exc:
            log.warning("Failed to extract timesheet ID from tab %s: %s", tab_name, exc)
            return None

    def _sum_timesheet_hours(
        self,
        timesheet_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        if not self._sheets.sheets_service:
            return 0.0
        spreadsheet = (
            self._sheets.sheets_service.spreadsheets()
            .get(spreadsheetId=timesheet_id)
            .execute()
        )
        sheets_list = spreadsheet.get("sheets", [])
        if not sheets_list:
            return 0.0
        sheet_name = sheets_list[0].get("properties", {}).get("title", "")
        if not sheet_name:
            return 0.0

        range_name = RangeFormat.TIMESHEET_DATA.value.format(
            sheet_name=sheet_name
        )
        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=timesheet_id,
                range=range_name,
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values: list[list] = result.get("values", [])
        if not values or len(values) < 2:
            return 0.0

        headers = values[0]
        date_col = self._sheets.find_column_index(headers, [ColumnName.DATE.value])
        hours_col = self._sheets.find_column_index(headers, [ColumnName.WORK_HOURS.value])

        if date_col is None or hours_col is None:
            return 0.0

        total = 0.0
        for i in range(1, len(values)):
            row = values[i]
            if len(row) <= max(date_col, hours_col):
                continue
            parsed = _serial_to_date(row[date_col])
            if parsed is None:
                continue
            if parsed < start_date or parsed > end_date:
                continue
            try:
                total += float(row[hours_col] or 0)
            except (ValueError, TypeError):
                continue
        return total

    def protect_archived_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        payment_status_col_idx: int,
    ) -> None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        spreadsheet = (
            self._sheets.sheets_service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )
        sheet_id = None
        for s in spreadsheet.get("sheets", []):
            if s.get("properties", {}).get("title") == sheet_name:
                sheet_id = s.get("properties", {}).get("sheetId")
                break
        if sheet_id is None:
            raise Exception(f"Sheet ID not found for '{sheet_name}'")

        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[
                {
                    "addProtectedRange": {
                        "protectedRange": {
                            "range": {
                                "sheetId": sheet_id,
                            },
                            "unprotectedRanges": [
                                {
                                    "sheetId": sheet_id,
                                    "startColumnIndex": payment_status_col_idx,
                                    "endColumnIndex": payment_status_col_idx + 1,
                                }
                            ],
                            "description": "Archived period — protected",
                            "warningOnly": False,
                        }
                    }
                }
            ],
        )
        log.info("Protected archived sheet %s", sheet_name)


def _spreadsheet_title(project_name: str, key: str) -> str:
    titles = {
        "info": f"{project_name} - Project info",
        "report": f"{project_name} - General Expenses",
        "calculations": f"{project_name} - Payment Distribution",
    }
    return titles.get(key, f"{project_name} - {key}")


_GSHEETS_EPOCH = datetime(1899, 12, 30)

_RUSSIAN_MONTHS = {
    "янв": 1, "январь": 1, "января": 1,
    "фев": 2, "февр": 2, "февраль": 2, "февраля": 2,
    "мар": 3, "март": 3, "марта": 3,
    "апр": 4, "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июн": 6, "июнь": 6, "июня": 6,
    "июл": 7, "июль": 7, "июля": 7,
    "авг": 8, "август": 8, "августа": 8,
    "сен": 9, "сент": 9, "сентябрь": 9, "сентября": 9,
    "окт": 10, "октябрь": 10, "октября": 10,
    "ноя": 11, "нояб": 11, "ноябрь": 11, "ноября": 11,
    "дек": 12, "декабрь": 12, "декабря": 12,
}


def _find_column_contains(headers: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for i, header in enumerate(headers):
        if needle_lower in header.lower():
            return i
    return None


def _pad_row(row: list, size: int) -> None:
    while len(row) < size:
        row.append("")


def _parse_rate_from_row(
    row: list, headers: list[str], col_name: str
) -> float | None:
    col_idx = _find_column_contains(headers, col_name)
    if col_idx is None or col_idx >= len(row):
        return None
    raw = str(row[col_idx]).replace("$", "").replace("\xa0", "").replace(" ", "")
    raw = raw.replace(",", ".").replace("€", "")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _serial_to_date(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return (_GSHEETS_EPOCH + timedelta(days=int(value))).replace(
            tzinfo=timezone.utc
        )
    if isinstance(value, str) and value.strip():
        val = value.strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y"):
            try:
                return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        parsed = _parse_russian_date(val)
        if parsed is not None:
            return parsed.replace(tzinfo=timezone.utc)
    return None


def _parse_russian_date(val: str) -> datetime | None:
    import re

    cleaned = re.sub(r"[,\s]+", " ", val).strip()
    parts = cleaned.split()
    if len(parts) < 3:
        return None

    for i, part in enumerate(parts):
        month_name = part.rstrip(".").lower()
        if month_name in _RUSSIAN_MONTHS:
            month = _RUSSIAN_MONTHS[month_name]
            day_part = parts[0] if i > 0 else parts[1]
            year_part = parts[-1]
            try:
                day = int(day_part)
                year = int(year_part)
                return datetime(year, month, day)
            except (ValueError, IndexError):
                return None
    return None


def _hyperlink(url: str) -> str:
    return f'=HYPERLINK("{url}"; "{url}")' if url else ""


def _specialist_in_sheet(
    values: list[list], headers: list[str], name: str, sheets: GoogleSheetsService
) -> bool:
    idx = sheets.find_column_index(headers, [ColumnName.SPECIALIST.value])
    if idx is None:
        return False
    for row in values[1:]:
        if len(row) > idx and row[idx] == name:
            return True
    return False


def _find_specialist_row(
    values: list[list], headers: list[str], name: str, sheets: GoogleSheetsService
) -> int | None:
    idx = sheets.find_column_index(headers, [ColumnName.SPECIALIST.value])
    if idx is None:
        return None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > idx and row[idx] == name:
            return i
    return None


def _find_insert_position(
    values: list[list], headers: list[str], sheets: GoogleSheetsService
) -> tuple[int, bool]:
    idx = sheets.find_column_index(headers, [ColumnName.SPECIALIST.value])
    if idx is None:
        return 1, False

    specialist_rows: list[int] = []
    total_row_idx: int | None = None

    for i, row in enumerate(values[1:], start=1):
        if len(row) <= idx:
            continue
        cell = row[idx]
        if cell and cell != "0" and not _is_total_row(row, headers, idx, sheets):
            specialist_rows.append(i)
        elif _is_total_row(row, headers, idx, sheets):
            total_row_idx = i
            break

    if not specialist_rows:
        return 1, False

    last = max(specialist_rows)
    insert_pos = last + 1
    if total_row_idx is not None and insert_pos >= total_row_idx:
        insert_pos = total_row_idx
    return insert_pos, True


def _is_total_row(
    row: list, headers: list[str], specialist_idx: int, sheets: GoogleSheetsService
) -> bool:
    if not row[specialist_idx] or row[specialist_idx] == "0":
        cost_cols = [
            ColumnName.TOTAL_COST_USD.value,
            ColumnName.SPECIALIST_WORK_COST_USD.value,
            ColumnName.CLIENT_WORK_COST_USD.value,
            ColumnName.REVENUE_USD.value,
        ]
        for col_name in cost_cols:
            col_idx = sheets.find_column_index(headers, [col_name])
            if col_idx is not None and len(row) > col_idx:
                cell = str(row[col_idx]) if row[col_idx] else ""
                if cell.startswith("="):
                    return True
        if not row[0] and any(str(c).strip() for c in row[1:]):
            return True
    return False


def _find_template_row(
    values: list[list], headers: list[str], sheets: GoogleSheetsService
) -> int | None:
    idx = sheets.find_column_index(headers, [ColumnName.SPECIALIST.value])
    if idx is None:
        return None
    for i in range(len(values) - 1, 0, -1):
        row = values[i]
        if (
            len(row) > idx
            and row[idx]
            and row[idx] != "0"
            and not _is_total_row(row, headers, idx, sheets)
        ):
            return i + 1
    return None


def _column_letter(index: int) -> str:
    result = ""
    while index >= 0:
        result = chr(index % 26 + ord("A")) + result
        index = index // 26 - 1
    return result


def _add_formulas_for_row(
    sheets: GoogleSheetsService,
    spreadsheet_id: str,
    sheet_name: str,
    target_row: int,
    headers: list[str],
    formula_provider: Any,
) -> None:
    formula_map = [
        (ColumnName.HOURS_WORKED.value, FormulaName.CALCULATE_WORKING_HOURS.value),
        (ColumnName.TOTAL_COST_USD.value, FormulaName.GROSS_TOTAL_COST.value),
        (ColumnName.SPECIALIST_WORK_COST_USD.value, FormulaName.NET_TOTAL_COST.value),
        (ColumnName.CLIENT_WORK_COST_USD.value, FormulaName.GROSS_TOTAL_COST.value),
        (ColumnName.REVENUE_USD.value, FormulaName.REVENUE.value),
    ]
    for col_name, formula_name in formula_map:
        col_idx = sheets.find_column_index(headers, [col_name])
        if col_idx is None:
            continue
        try:
            formula = formula_provider.get_formula(formula_name)
            sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_name}!{_column_letter(col_idx)}{target_row}",
                values=[[formula]],
                value_input_option="USER_ENTERED",
            )
        except Exception as exc:
            log.warning("Failed to set %s formula: %s", col_name, exc)


def _write_specialist_fields(
    sheets: GoogleSheetsService,
    spreadsheet_id: str,
    sheet_name: str,
    target_row: int,
    specialist: Specialist,
    headers: list[str],
) -> None:
    field_updates = [
        (ColumnName.SPECIALIST.value, specialist.display_name or specialist.name),
        (ColumnName.SPECIALIST_ROLE.value, specialist.role),
        (ColumnName.HOURLY_RATE_USD.value, str(specialist.external_rate)),
        (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, str(specialist.internal_rate)),
        (ColumnName.CLIENT_HOURLY_RATE_USD.value, str(specialist.external_rate)),
    ]
    for col_name, val in field_updates:
        col_idx = sheets.find_column_index(headers, [col_name])
        if col_idx is None:
            continue
        try:
            sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_name}!{_column_letter(col_idx)}{target_row}",
                values=[[val]],
                value_input_option="USER_ENTERED",
            )
        except Exception as exc:
            log.warning("Failed to update %s: %s", col_name, exc)
