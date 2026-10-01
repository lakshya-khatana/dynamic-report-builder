**Live demo:** https://dynamic-report-builder.onrender.com

# Dynamic Report Builder Engine

A schema-agnostic report builder. Connect a database, reflect its schema, build a query (joins, fields, aggregates, filters, sort) and run it with pagination, or export the result. The backend is FastAPI + SQLAlchemy Core, and the UI is a single HTML file.

## Features

- Data sources: SQLite, PostgreSQL, MySQL, SQL Server and flat files. Credentials are encrypted at rest.
- Schema reflection and join suggestions.
- Report builder: joins, selected fields, aggregates (GROUP BY is added automatically), filters, sorting.
- Preview and run with pagination, plus CSV and Excel export.
- Saved report templates.
- Read-only guard: only SELECT queries run. INSERT, UPDATE, DELETE, DROP and similar statements are blocked.

## Setup

Requires Python 3.13 (the version this was tested with).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create the `.env` file:

1. Copy `.env.example` to `.env`.
2. Generate a key and paste it after `FERNET_KEY=`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Run

```powershell
uvicorn main:app --reload --port 8000
```

- Health check: http://127.0.0.1:8000/health
- API docs (Swagger): http://127.0.0.1:8000/docs

## Use the UI

1. Open `ui/report-builder.html` by double-clicking it (it opens in your normal browser). Keep the backend running.
2. The API base URL at the top should be `http://127.0.0.1:8000`. Click **Test connection**; it should say reachable.
3. **1 Â· Sources**: add a source. For the bundled sample data choose dialect SQLite and use the full path to `storage/sample.db` with forward slashes, for example `C:/path/to/project/storage/sample.db`.
4. **2 Â· Schema**: browse tables and columns.
5. **3 Â· Build Query**: pick the source, a base table, add joins, fields and aggregates, then **Run preview**.
6. **4 Â· Results**: page through the rows and export to CSV or Excel.
7. **5 Â· Templates**: save and reload report definitions.

## Tests

```powershell
python -m pytest -v
```

## Optional: Data tab (demo helper, not part of the report engine)

Tab **6 Â· Data** lets you view and edit rows of a source's tables (backend file `data_admin.py`). It is a convenience for demos and is separate from the report engine, whose read-only guard is unchanged.

Editing is controlled by the `ALLOW_DATA_EDIT` environment variable. Set it in the same terminal before starting the server:

```powershell
$env:ALLOW_DATA_EDIT = "false"   # tab becomes view-only
uvicorn main:app --reload
```

## Project layout

```
main.py            FastAPI entry point
config.py          settings (reads .env)
api/               HTTP routes: sources, schema, reports, templates
connectors/        database and flat-file connectors
reflection/        schema reflection and join recommendation
compiler/          report request to SQL
execution/         query execution, pagination, streaming
exporters/         CSV and Excel export
security/          read-only guard, identifier checks, encryption
templates_store/   saved templates and the app's own tables
errors/            error handling
storage/           sample.db and uploads
tests/             unit tests
ui/                report-builder.html
data_admin.py      optional Data tab backend
```

