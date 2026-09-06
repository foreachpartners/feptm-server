"""Storage for project-scoped spreadsheet operations."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from feptm.core import utils
from feptm.core.exceptions import (
    ProjectFolderNotFoundError,
    ProjectSpreadsheetNotFoundError,
)
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

    def list_projects(self, parent_folder_id: str) -> list[dict[str, str]]:
        return self._sheets.list_drive_folders(parent_folder_id)

    def get_project_card(self, folder_id: str) -> dict:
        try:
            folder = self._sheets.get_file(folder_id)
        except Exception as e:
            raise ProjectFolderNotFoundError(folder_id) from e

        mime = folder.get("mimeType", "")
        if "folder" not in mime:
            raise ProjectFolderNotFoundError(folder_id)

        folder_name: str = folder.get("name", "")
        spreadsheets = self._sheets.list_drive_spreadsheets(folder_id)

        expected_keys = {
            "info": f"{folder_name} - Project info",
            "report": f"{folder_name} - General Expenses",
            "calculations": f"{folder_name} - Payment Distribution",
        }

        found: dict[str, str] = {}
        for key, expected_name in expected_keys.items():
            match = next(
                (s for s in spreadsheets if s["name"] == expected_name),
                None,
            )
            if match is None:
                raise ProjectSpreadsheetNotFoundError(expected_name)
            found[key] = match["id"]

        three_names = set(expected_keys.values())
        timesheets = sorted(
            [s for s in spreadsheets if s["name"] not in three_names],
            key=lambda x: x["name"].lower(),
        )

        return {
            "name": folder_name,
            "drive_folder_id": folder_id,
            "project_id": found["info"],
            "info_spreadsheet_id": found["info"],
            "report_spreadsheet_id": found["report"],
            "calculations_spreadsheet_id": found["calculations"],
            "timesheets": timesheets,
        }

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

    def _read_cell_formula(
        self, spreadsheet_id: str, sheet_name: str, cell: str
    ) -> str | None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")
        try:
            result = (
                self._sheets.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!{cell}",
                    valueRenderOption="FORMULA",
                )
                .execute()
            )
            values = result.get("values", [])
            if not values or not values[0]:
                return None
            return str(values[0][0])
        except Exception:
            return None

    def add_specialist_to_report(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
        import_formula: str,
    ) -> None:
        tab_name = specialist.name
        existing = self._list_sheet_titles(spreadsheet_id)
        if tab_name not in existing:
            self._sheets.batch_update(
                spreadsheet_id=spreadsheet_id,
                requests=[{"addSheet": {"properties": {"title": tab_name}}}],
            )
            self._sheets.invalidate_metadata_cache(spreadsheet_id)
            log.info("Created tab for %s in spreadsheet", specialist.name)
            self._sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )
        else:
            current = self._read_cell_formula(spreadsheet_id, tab_name, "A1")
            if current != import_formula:
                self._sheets.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                    values=[[import_formula]],
                    value_input_option="USER_ENTERED",
                )

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

        if _specialist_in_sheet(values, headers, specialist.name, self._sheets):
            log.info("Specialist %s already exists in Current Period", specialist.name)
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
        values, headers, sheet = sheet_data
        target_row = _find_specialist_row(
            values, headers, specialist.name, self._sheets
        )
        if target_row is None:
            return
        sheet_id = sheet.get("properties", {}).get("sheetId")
        _write_specialist_fields(
            self._sheets, spreadsheet_id, sheet_id, target_row, specialist, headers
        )

    def sync_rates_batch(
        self,
        spreadsheet_id: str,
        specialists: list[Specialist],
    ) -> None:
        sheet_name = SheetName.CURRENT_PERIOD.value
        sheet_data = self._read_current_period(spreadsheet_id, sheet_name)
        if not sheet_data:
            return
        values, headers, sheet = sheet_data
        sheet_id = sheet.get("properties", {}).get("sheetId")

        requests: list[dict[str, Any]] = []
        for specialist in specialists:
            target_row = _find_specialist_row(
                values, headers, specialist.name, self._sheets
            )
            if target_row is None:
                continue

            field_updates = [
                (ColumnName.SPECIALIST.value, specialist.name),
                (ColumnName.SPECIALIST_ROLE.value, specialist.role),
                (ColumnName.HOURLY_RATE_USD.value, specialist.external_rate),
                (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, specialist.internal_rate),
                (ColumnName.CLIENT_HOURLY_RATE_USD.value, specialist.external_rate),
            ]

            row_index = target_row - 1
            for col_name, val in field_updates:
                col_idx = self._sheets.find_column_index(headers, [col_name])
                if col_idx is None or val is None:
                    continue

                if isinstance(val, str):
                    entry: dict[str, Any] = {"stringValue": val}
                else:
                    entry = {"numberValue": float(val)}

                requests.append(
                    {
                        "updateCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1,
                            },
                            "rows": [{"values": [{"userEnteredValue": entry}]}],
                            "fields": "userEnteredValue",
                        }
                    }
                )

        if requests:
            self._sheets.batch_update(spreadsheet_id, requests)

    def batch_add_sheets(
        self,
        spreadsheet_id: str,
        specialists: list[Specialist],
    ) -> None:
        existing = set(self._list_sheet_titles(spreadsheet_id))
        new_names = [sp.name for sp in specialists if sp.name not in existing]
        if not new_names:
            return

        requests = [
            {"addSheet": {"properties": {"title": name}}}
            for name in new_names
        ]
        self._sheets.batch_update(spreadsheet_id, requests)
        self._sheets.invalidate_metadata_cache(spreadsheet_id)
        log.info("Created %d tabs in spreadsheet", len(new_names))

    def batch_write_a1_formulas(
        self,
        spreadsheet_id: str,
        formulas: list[tuple[str, str]],
    ) -> None:
        if not formulas:
            return

        sheets = self._sheets.get_all_sheets(spreadsheet_id)
        sheet_id_map = {
            s.get("properties", {}).get("title"): s.get("properties", {}).get("sheetId")
            for s in sheets
        }

        requests: list[dict[str, Any]] = []
        for tab_name, formula in formulas:
            sheet_id = sheet_id_map.get(tab_name)
            if sheet_id is None:
                continue
            requests.append(
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1,
                        },
                        "rows": [
                            {"values": [{"userEnteredValue": {"formulaValue": formula}}]}
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            )

        if requests:
            self._sheets.batch_update(spreadsheet_id, requests)

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
        sheets = self._sheets.get_all_sheets(spreadsheet_id)
        return [
            s.get("properties", {}).get("title", "")
            for s in sheets
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
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption="UNFORMATTED_VALUE",
            )
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
                self._sheets.invalidate_metadata_cache(spreadsheet_id)
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
                    sheet_id,
                    target_row,
                    headers,
                    formula_provider,
                )
            except Exception as exc:
                log.warning("Failed to add formulas: %s", exc)

        _write_specialist_fields(
            self._sheets, spreadsheet_id, sheet_id, target_row, specialist, headers
        )

    def _copy_row_formatting(
        self, spreadsheet_id: str, sheet_name: str, source_row: int, target_row: int
    ) -> None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheets = self._sheets.get_all_sheets(spreadsheet_id)
        sheet_id = None
        for s in sheets:
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
                        "pasteType": "PASTE_FORMULA",
                        "pasteOrientation": "NORMAL",
                    }
                },
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
                        "pasteType": "PASTE_FORMAT",
                        "pasteOrientation": "NORMAL",
                    }
                },
            ],
        )
        log.info("Copied row %d to row %d", source_row, target_row)

    def close_period_in_timesheet(
        self,
        timesheet_id: str,
        period_name: str,
    ) -> int:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        timesheet_id = (
            utils.extract_id_from_hyperlink_formula(timesheet_id) or timesheet_id
        )

        sheets_list = self._sheets.get_all_sheets(timesheet_id)
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
        period_col = self._sheets.find_column_index(
            headers, [ColumnName.PAYMENT_PERIOD.value]
        )
        if period_col is None:
            period_col = _find_column_contains(headers, ColumnName.PAYMENT_PERIOD.value)
        if period_col is None:
            log.warning(
                "Timesheet %s: missing Payment Period column. headers=%s",
                timesheet_id,
                headers,
            )
            return 0

        updates = 0
        for i in range(1, len(values)):
            row = values[i]
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
                log.warning(
                    "Failed to update Payment Period for row %d: %s", i + 1, exc
                )

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
        values, headers, cp_sheet = cp_data

        cp_sheet_id = cp_sheet.get("properties", {}).get("sheetId")
        if cp_sheet_id is None:
            return False

        # Duplicate Current Period tab at the end of the sheets list
        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[{
                "duplicateSheet": {
                    "sourceSheetId": cp_sheet_id,
                    "insertSheetIndex": len(existing),
                    "newSheetName": period_name,
                }
            }],
        )
        self._sheets.invalidate_metadata_cache(spreadsheet_id)

        # Read all values with UNFORMATTED_VALUE and write back as RAW
        # This replaces formulas with their computed values
        range_name = f"{period_name}!A1:{self._sheets.column_index_to_letter(len(headers) - 1)}{len(values)}"
        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        computed_values = result.get("values", [])
        if computed_values:
            self._sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=range_name,
                values=computed_values,
                value_input_option="RAW",
            )

        # Find Period column and write period_name to data rows (skip total rows)
        period_idx = _find_column_contains(headers, ColumnName.PERIOD.value)
        if period_idx is not None and len(values) > 1:
            period_col_letter = self._sheets.column_index_to_letter(period_idx)
            period_range = f"{period_name}!{period_col_letter}2:{period_col_letter}{len(values)}"
            
            specialist_idx = 0
            period_values = []
            for i in range(1, len(values)):
                row = values[i]
                _pad_row(row, len(headers))
                if row[specialist_idx]:
                    period_values.append([period_name])
                else:
                    period_values.append([""])
            
            self._sheets.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=period_range,
                values=period_values,
                value_input_option="RAW",
            )

        log.info("Archived Current Period as %s in spreadsheet", period_name)
        return True

    def is_period_closed(
        self,
        spreadsheet_id: str,
        period_name: str,
    ) -> bool:
        existing = self._list_sheet_titles(spreadsheet_id)
        return period_name in existing

    def delete_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> bool:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheets = self._sheets.get_all_sheets(spreadsheet_id)
        sheet_id = None
        for sheet in sheets:
            if sheet.get("properties", {}).get("title") == sheet_name:
                sheet_id = sheet.get("properties", {}).get("sheetId")
                break

        if sheet_id is None:
            return False

        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[{"deleteSheet": {"sheetId": sheet_id}}],
        )
        self._sheets.invalidate_metadata_cache(spreadsheet_id)
        log.info("Deleted sheet %s from spreadsheet %s", sheet_name, spreadsheet_id)
        return True

    def remove_stale_specialists(
        self,
        spreadsheet_id: str,
        active_names: set[str],
    ) -> int:
        cp_data = self._read_current_period(
            spreadsheet_id, SheetName.CURRENT_PERIOD.value
        )
        if not cp_data:
            return 0
        values, headers, cp_sheet = cp_data

        sheet_id = cp_sheet.get("properties", {}).get("sheetId")
        if sheet_id is None:
            return 0

        specialist_col = 0
        rows_to_delete: list[int] = []
        for i, row in enumerate(values[1:], start=1):
            _pad_row(row, len(headers))
            name = row[specialist_col] if specialist_col < len(row) else ""
            if not name or name in active_names:
                continue
            if _is_total_row(row, headers, specialist_col, self._sheets):
                continue
            rows_to_delete.append(i)

        if not rows_to_delete:
            return 0

        requests: list[dict] = []
        for row_idx in sorted(rows_to_delete, reverse=True):
            requests.append(
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_idx,
                            "endIndex": row_idx + 1,
                        }
                    }
                }
            )
        self._sheets.batch_update(spreadsheet_id, requests)
        removed = len(rows_to_delete)
        log.info(
            "Removed %d stale specialist rows from Current Period in %s",
            removed,
            spreadsheet_id,
        )
        return removed

    def get_stale_specialists(
        self,
        spreadsheet_id: str,
        active_names: set[str],
    ) -> list[Specialist]:
        cp_data = self._read_current_period(
            spreadsheet_id, SheetName.CURRENT_PERIOD.value
        )
        if not cp_data:
            return []
        values, headers, _ = cp_data

        stale: list[Specialist] = []
        for row in values[1:]:
            _pad_row(row, len(headers))
            name = str(row[0]).strip() if row else ""
            if (
                not name
                or name in active_names
                or _is_total_row(row, headers, 0, self._sheets)
            ):
                continue

            cl_rate = _parse_rate_from_row(
                row, headers, ColumnName.CLIENT_HOURLY_RATE_USD.value
            )
            sp_rate = _parse_rate_from_row(
                row, headers, ColumnName.SPECIALIST_HOURLY_RATE_USD.value
            )

            role_idx = _find_column_contains(headers, ColumnName.SPECIALIST_ROLE.value)
            role = (
                str(row[role_idx])
                if role_idx is not None and role_idx < len(row)
                else ""
            )

            timesheet_url = self._extract_timesheet_id_from_tab(spreadsheet_id, name)
            timesheet_id = (
                utils.extract_id_from_hyperlink_formula(timesheet_url or "")
                or timesheet_url
            )

            stale.append(
                Specialist(
                    name=name,
                    role=role,
                    external_rate=Decimal(str(cl_rate))
                    if cl_rate is not None
                    else Decimal(0),
                    internal_rate=Decimal(str(sp_rate))
                    if sp_rate is not None
                    else Decimal(0),
                    timesheet=timesheet_id,
                )
            )

        return stale

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

    def protect_archived_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        payment_status_col_idx: int,
    ) -> None:
        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheets = self._sheets.get_all_sheets(spreadsheet_id)
        sheet_id = None
        for s in sheets:
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


def _find_column_contains(headers: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for i, header in enumerate(headers):
        if needle_lower in header.lower():
            return i
    return None


def _pad_row(row: list, size: int) -> None:
    while len(row) < size:
        row.append("")


def _parse_rate_from_row(row: list, headers: list[str], col_name: str) -> float | None:
    col_idx = _find_column_contains(headers, col_name)
    if col_idx is None or col_idx >= len(row):
        return None
    raw = str(row[col_idx]).replace("$", "").replace("\xa0", "").replace(" ", "")
    raw = raw.replace(",", ".").replace("€", "")
    try:
        return float(raw)
    except (ValueError, TypeError):
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
    sheet_id: int,
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
    requests: list[dict[str, Any]] = []
    row_index = target_row - 1
    for col_name, formula_name in formula_map:
        col_idx = sheets.find_column_index(headers, [col_name])
        if col_idx is None:
            continue
        formula = formula_provider.get_formula(formula_name)
        requests.append(
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "rows": [
                        {"values": [{"userEnteredValue": {"formulaValue": formula}}]}
                    ],
                    "fields": "userEnteredValue",
                }
            }
        )
    if requests:
        try:
            sheets.batch_update(spreadsheet_id, requests)
        except Exception as exc:
            log.warning("Failed to batch-update formulas: %s", exc)


def _write_specialist_fields(
    sheets: GoogleSheetsService,
    spreadsheet_id: str,
    sheet_id: int,
    target_row: int,
    specialist: Specialist,
    headers: list[str],
) -> None:
    field_updates = [
        (ColumnName.SPECIALIST.value, specialist.name),
        (ColumnName.SPECIALIST_ROLE.value, specialist.role),
        (ColumnName.HOURLY_RATE_USD.value, specialist.external_rate),
        (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, specialist.internal_rate),
        (ColumnName.CLIENT_HOURLY_RATE_USD.value, specialist.external_rate),
    ]
    requests: list[dict[str, Any]] = []
    row_index = target_row - 1
    for col_name, val in field_updates:
        col_idx = sheets.find_column_index(headers, [col_name])
        if col_idx is None:
            continue
        if val is None:
            continue
        if isinstance(val, str):
            entry: dict[str, Any] = {"stringValue": val}
        else:
            entry = {"numberValue": float(val)}  # type: ignore[arg-type]
        cell = {"userEnteredValue": entry}
        requests.append(
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "rows": [{"values": [cell]}],
                    "fields": "userEnteredValue",
                }
            }
        )
    if requests:
        try:
            sheets.batch_update(spreadsheet_id, requests)
        except Exception as exc:
            log.warning("Failed to batch-update specialist fields: %s", exc)
