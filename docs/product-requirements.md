# Product Requirements: Time & Materials Tracking System

## Document Scope

User-facing requirements for T&M project time tracking system. Technical implementation details are out of scope.

## Core Constraint (MUST)

**Google Sheets is the primary user interface.**

- All calculations (hours, costs, revenue) MUST execute via spreadsheet formulas
- Backend server is auxiliary tooling for operations impossible through Sheets UI
- Users interact with spreadsheets directly; backend operates transparently

## User Roles

### Project Manager (PM)

Primary system administrator for a project.

Responsibilities:

- Project structure creation
- Team composition management
- Payment period lifecycle
- Client communication via reports

### Specialist

Team member logging work hours.

Responsibilities:

- Daily/weekly timesheet updates
- Task description entry
- Work hours logging

### Client

External stakeholder with read access.

Responsibilities:

- Review work progress
- Verify invoiced amounts
- Request clarifications via comments

## Access Control Matrix

| Document | PM | Specialist | Client |
|----------|-----|------------|--------|
| Project Info | Edit | No access | No access |
| Team Sheet | Edit | No access | No access |
| Specialist Timesheet | Edit | Edit (own only) | View |
| General Expenses Report | Edit | No access | Comment |
| Payment Distribution | Edit | No access | No access |

## Functional Requirements

### FR-001: Project Creation

**Actor:** PM

**Trigger:** New client engagement starts

**System MUST:**

1. Create Google Drive folder: `{ProjectName}`
2. Create Project Info spreadsheet from template
3. Create General Expenses Report spreadsheet from template
4. Create Payment Distribution spreadsheet from template
5. Link all documents via HYPERLINK formulas in Project Info
6. Return URLs for all created resources

**Postcondition:** Project structure exists with linked documents

### FR-002: Team Member Addition

**Actor:** PM

**Trigger:** PM adds specialist row to Team sheet

**Precondition:** Project exists

**System MUST:**

1. Detect new specialist in Team sheet (row without Timesheet ID)
2. Create personal timesheet from template: `Time Tracking for {Name}. Project {ProjectName}`
3. Place timesheet in project folder
4. Update Team sheet with timesheet ID
5. Create specialist tab in General Expenses Report with IMPORTRANGE formula
6. Create specialist tab in Payment Distribution with IMPORTRANGE formula
7. Add specialist row to "Current Period" tab in both reports
8. Apply calculation formulas to new row

**Formula application:**

- Hours Worked: `=SUMIF(INDIRECT("'"&$A2&"'!$E$2:$E", true), TRIM($C2), INDIRECT("'"&$A2&"'!$D$2:$D", true))`
- Total Cost: `=$D2*$E2`
- Specialist Cost: `=$D2*$G2`
- Revenue: `=$F2-$H2`

**Postcondition:** Specialist has linked timesheet; reports include specialist data

### FR-002.1: Specialist Rate Periods

**Actor:** PM

**Trigger:** PM adds new row with existing Timesheet ID or updates rate conditions

**Precondition:** Specialist exists (identified by Timesheet ID)

**Data model:**

- **Timesheet ID** is the specialist identifier (unique per specialist)
- One specialist MAY have multiple rows in Team sheet with different rate conditions
- Each row represents a rate period: valid from `Start Date` until the next period starts

**Example:**

| Name | Role | Internal Rate | External Rate | Start Date | Timesheet |
|------|------|---------------|---------------|------------|-----------|
| Mark | Developer | 12 | 14 | 2025-01-01 | abc123 |
| Mark | Developer | 15 | 20 | 2025-03-26 | abc123 |

**Calculation rules:**

- Rate lookup MUST find applicable period by matching timesheet entry date against `Start Date`
- Entry dated 2025-03-01 uses rates 12/14 (period starting 2025-01-01)
- Entry dated 2025-04-01 uses rates 15/20 (period starting 2025-03-26)
- Formulas MUST handle multiple rate periods per specialist

**System MUST NOT:**

- Create duplicate timesheet for existing Timesheet ID
- Duplicate specialist tabs in reports for existing specialist

**Postcondition:** Specialist calculations use period-appropriate rates

### FR-003: Time Entry

**Actor:** Specialist

**Trigger:** Work completed

**System:** No backend involvement

**Specialist MUST:**

1. Open personal timesheet
2. Enter row: Date | Project | Task Name | Hours | (Payment Period - leave blank) | (Status - leave blank)

**Validation:**

- Date: Valid date format
- Hours: Positive decimal
- Payment Period: MUST remain blank (PM fills during period close)

### FR-004: Payment Period Close

**Actor:** PM

**Trigger:** Invoice preparation

**PM MUST (via Sheets UI):**

1. Fill "Payment Period" column in each specialist timesheet for relevant rows
2. Duplicate "Current Period" tab in reports, rename to period name (e.g., "January 2026")
3. Fill "Period" column in new tabs

**System SHOULD (future):**

- Automate period name propagation across timesheets
- Create period snapshot tabs automatically

### FR-005: Report Generation

**Actor:** System (automatic)

**Trigger:** Data change in linked timesheets

**System behavior:**

- IMPORTRANGE formulas pull data automatically
- Calculation formulas update automatically
- No backend intervention required

**Report content:**

- General Expenses: Specialist | Role | Hours | Rate | Total Cost
- Payment Distribution: Specialist | Role | Hours | Specialist Rate | Client Rate | Specialist Cost | Client Cost | Revenue

### FR-006: Payment Confirmation

**Actor:** PM

**Trigger:** Client payment received

**PM MUST (via Sheets UI):**

1. Update payment status in period tab
2. Update Payment Status column in specialist timesheets

## Document Structure

### Project Info Spreadsheet

**Sheet: "Project info"**

| Field | Value |
|-------|-------|
| Project ID | {spreadsheet_id} |
| Name | {project_name} |
| Created | {datetime} |
| Modified | {datetime} |
| Project Folder | =HYPERLINK("{folder_url}") |
| Payment Distribution | =HYPERLINK("{calculations_url}") |
| General Expenses | =HYPERLINK("{report_url}") |

**Sheet: "Team"**

| Name | Role | Internal Rate | External Rate | Start Date | Timesheet |
|------|------|---------------|---------------|------------|-----------|

**Column semantics:**

- **Name:** Specialist display name
- **Role:** Job function (Developer, QA, Manager, etc.)
- **Internal Rate:** Hourly rate paid to specialist (currency per project)
- **External Rate:** Hourly rate charged to client (currency per project)
- **Start Date:** Date from which rate conditions apply (YYYY-MM-DD)
- **Timesheet:** Spreadsheet ID (system-generated, serves as specialist identifier)

**Rate periods:** Multiple rows with same Timesheet ID represent rate changes over time. See FR-002.1.

### Specialist Timesheet

**Sheet: "timesheet"**

| Date | Project | Task Name | Work Hours | Payment Period | Payment Status |
|------|---------|-----------|------------|----------------|----------------|

- Rows 2-100: Data entry area
- Green columns: Specialist edits (Date, Project, Task Name, Work Hours)
- Blue columns: PM edits (Payment Period, Payment Status)

### General Expenses Report

**Sheet: "Current Period"**

| Specialist | Specialist Role | Period | Hours Worked | Hourly Rate (USD) | Total Cost (USD) |
|------------|-----------------|--------|--------------|-------------------|------------------|

**Sheet: "{Specialist Name}"**

- Contains: `=IMPORTRANGE("{timesheet_id}", "timesheet!A:D")`

### Payment Distribution

**Sheet: "Current Period"**

| Specialist | Role | Period | Hours | Specialist Rate | Client Rate | Specialist Cost | Client Cost | Revenue |
|------------|------|--------|-------|-----------------|-------------|-----------------|-------------|---------|

**Sheet: "{Specialist Name}"**

- Contains: `=IMPORTRANGE("{timesheet_id}", "timesheet!A:E")`

## Constraints and Assumptions

### C-001: Google Sheets as Single Source of Truth

- NO separate database
- All persistent data resides in Google Sheets
- Backend is stateless

### C-002: Formula-Driven Calculations

- Backend MUST NOT perform financial calculations
- All costs, totals, revenue calculated by spreadsheet formulas
- Backend only inserts formulas, not computed values

### C-003: Template-Based Document Creation

- All documents created by copying pre-configured templates
- Templates contain structure, formatting, base formulas
- Template IDs configured via environment variables

### C-004: Access Segregation

- Specialists see only their own timesheets
- Clients see General Expenses only (not Payment Distribution)
- PM has full access to all documents

### C-005: Manual Period Management

- Payment period names entered manually
- Period close is manual process via Sheets UI
- Backend MAY automate in future versions

### C-006: Fixed Timesheet Capacity

- Timesheets contain 100 rows for entries
- Expansion requires manual intervention

### C-007: No Notifications

- System does not send email/push notifications
- Users responsible for checking documents

### C-008: No Tax/Fee Calculations

- System tracks gross amounts only
- Tax compliance is user responsibility

### C-009: Timesheet ID as Specialist Identifier

- Timesheet ID (spreadsheet ID) is the canonical specialist identifier
- Same Timesheet ID in Team sheet = same specialist
- Multiple rows with same Timesheet ID = rate period history
- Name/Role columns are display-only; Timesheet ID is authoritative

## Out of Scope

- User authentication/authorization (Google handles via sharing)
- Notification system
- Tax calculations
- Invoice document generation
- Multi-currency support (single currency per project)
- Historical data migration
- Audit logging
