# Deal Data Extractor

A FastAPI application for managing and processing deal tasks.

## Installation

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

## Running the Application

```bash
python run.py
```

The application will be available at http://localhost:1234

```sh
python export_data.py --table deals --exclude-columns "deal_task_id" --sort-column time --sort-desc --output deals.csv
```
