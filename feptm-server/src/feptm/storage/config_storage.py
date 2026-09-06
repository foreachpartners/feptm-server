"""Storage for formula retrieval from config spreadsheet."""

import re

from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import SheetName


class ConfigStorage:
    """Storage for formula retrieval from the configuration Google Sheet."""

    def __init__(
        self, sheets_service: GoogleSheetsService, config_sheet_id: str
    ) -> None:
        self._sheets = sheets_service
        self._config_sheet_id = config_sheet_id
        self._cache: dict[str, str] = {}
        self._all_formulas_loaded: bool = False

    def get_formula(self, formula_name: str) -> str:
        if formula_name in self._cache:
            return self._cache[formula_name]

        if not self._all_formulas_loaded:
            self._load_all_formulas()
            self._all_formulas_loaded = True

        if formula_name in self._cache:
            return self._cache[formula_name]

        raise Exception(
            f"Formula '{formula_name}' not found in configuration spreadsheet"
        )

    def _load_all_formulas(self) -> None:
        if not self._sheets.is_initialized():
            raise Exception("Google Sheets service not initialized")

        sheet = self._sheets.get_sheet_by_name(
            spreadsheet_id=self._config_sheet_id,
            sheet_name=SheetName.FORMULAS.value,
        )
        if not sheet:
            raise Exception("Formulas sheet not found in the configuration spreadsheet")

        if not self._sheets.sheets_service:
            raise Exception("Google Sheets service not initialized")

        result = (
            self._sheets.sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self._config_sheet_id,
                range=f"{SheetName.FORMULAS.value}!A:C",
            )
            .execute()
        )

        values = result.get("values", [])
        if not values or len(values) <= 1:
            raise Exception("No formulas found in the configuration spreadsheet")

        for row in values[1:]:
            if len(row) >= 2:
                name: str = row[0].strip()
                formula: str = row[1].strip()
                if name and formula:
                    self._cache[name] = formula

    def get_import_timesheet_formula(self, specialist_timesheet_id: str) -> str:
        formula = self.get_formula("Import specialist timesheet")
        if "spreadsheets/d/" in specialist_timesheet_id:
            url = specialist_timesheet_id
        else:
            url = f"https://docs.google.com/spreadsheets/d/{specialist_timesheet_id}"
        return re.sub(
            r"(SpecialistSpreadsheetID|\{timesheet_id\})",
            url,
            formula,
        )
