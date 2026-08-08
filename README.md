# Backend for Time & Materials Accounting

A backend service for automating time and materials accounting using Google Sheets API as a single source of truth.

## TODO

1. Add tests
2. Linter
3. Logging
4. Add documentation



## Technology Stack
- Python 3.12+
- FastAPI 0.110.0+
- Google Sheets API v4
- OAuth 2.0
- uvicorn 0.29.0+

## Project Structure
- `/src/feptm/` - Main package
  - `/src/feptm/core/` - Core components (configuration, utilities)
  - `/src/feptm/api/` - REST API endpoints
  - `/src/feptm/services/` - Services for working with Google Sheets API
  - `/src/feptm/models/` - Data models
- `/bin/` - Executable scripts
- `/tests/` - Unit tests

## Setup and Installation
1. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -e .
   ```

3. For development, install dev dependencies:
   ```
   pip install -e ".[dev]"
   ```

## Running the Application
```
./bin/run_api.py
```

Or using Python directly:
```
python -m bin.run_api
```

## Run via uv
```
uv run uvicorn feptm.main:app --host 0.0.0.0 --port 8000 --reload
```
