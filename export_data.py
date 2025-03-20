#!/usr/bin/env python
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv
import polars as pl
import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("export_data")

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "deal_data_db")


def get_connection():
    """Create a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise


def get_table_columns(conn, table_name):
    """Get the column names for a table."""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
        return [desc[0] for desc in cursor.description]


def count_rows(conn, table_name, task_id=None, date=None):
    """Count the number of rows in a table, optionally filtered by task_id or date."""
    with conn.cursor() as cursor:
        if table_name == "deals":
            conditions = []
            params = []

            if task_id is not None:
                conditions.append("deal_task_id = %s")
                params.append(task_id)

            if date is not None:
                # For deals table, filter by the time field
                conditions.append("DATE(time) = %s")
                params.append(date)

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name} {where_clause}", params
                )
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

        elif table_name == "deal_tasks" and date is not None:
            cursor.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE date = %s", (date,)
            )
        else:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

        return cursor.fetchone()[0]


def export_data(
    table_name,
    output_file,
    batch_size=100000,
    task_id=None,
    date=None,
    include_headers=True,
    exclude_columns=None,
):
    """
    Export data from PostgreSQL to CSV using Polars.

    Args:
        table_name: Name of the table to export
        output_file: Path to the output CSV file
        batch_size: Number of rows to process at once
        task_id: Optional task_id to filter deals by
        date: Optional date to filter data by (format: YYYY-MM-DD)
        include_headers: Whether to include headers in the CSV file
        exclude_columns: List of column names to exclude from the export
    """
    start_time = time.time()
    conn = get_connection()

    # Initialize exclude_columns if None
    if exclude_columns is None:
        exclude_columns = []

    if exclude_columns:
        logger.info(f"Excluding columns: {exclude_columns}")

    # Build WHERE clause based on filters
    where_conditions = []
    params = []

    if task_id is not None and table_name == "deals":
        where_conditions.append("deal_task_id = %s")
        params.append(task_id)

    if date is not None:
        if table_name == "deals":
            where_conditions.append("DATE(time) = %s")
            params.append(date)
        elif table_name == "deal_tasks":
            where_conditions.append("date = %s")
            params.append(date)

    # Construct the full WHERE clause
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # Count total rows to be exported
    total_rows = count_rows(conn, table_name, task_id, date)
    if date is not None:
        logger.info(f"Exporting {total_rows} rows from {table_name} for date {date}")
    else:
        if task_id is not None and table_name == "deals":
            logger.info(
                f"Exporting {total_rows} rows from {table_name} for task_id {task_id}"
            )
        else:
            logger.info(f"Exporting {total_rows} rows from {table_name}")

    # Get column names
    columns = get_table_columns(conn, table_name)

    # Calculate the number of batches
    num_batches = (total_rows // batch_size) + (1 if total_rows % batch_size > 0 else 0)

    # Process data in batches
    rows_processed = 0

    for batch_num in range(num_batches):
        offset = batch_num * batch_size
        logger.info(
            f"Processing batch {batch_num+1}/{num_batches} (rows {offset+1}-{min(offset+batch_size, total_rows)})"
        )

        # SQL to fetch a batch of data with parameterized query
        sql = f"""
            SELECT * FROM {table_name}
            {where_clause}
            ORDER BY {columns[0]}
            LIMIT {batch_size} OFFSET {offset}
        """

        # Use Polars to read from PostgreSQL and write to CSV
        with conn.cursor(
            name=f"fetch_data_cursor_{batch_num}",
            cursor_factory=psycopg2.extras.DictCursor,
        ) as cursor:
            cursor.execute(sql, params)

            # Fetch rows as dictionaries
            batch_data = cursor.fetchall()
            batch_rows = len(batch_data)
            rows_processed += batch_rows

            if batch_rows == 0:
                logger.info("No more rows to process")
                break

            # Convert to Polars DataFrame
            df = pl.DataFrame([dict(row) for row in batch_data])

            # Drop excluded columns if they exist in the DataFrame
            for col in exclude_columns:
                if col in df.columns:
                    df = df.drop(col)

            # Write to CSV
            if batch_num == 0 and include_headers:
                # First batch with headers - use Python's open function to handle encoding
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    df.write_csv(f, separator=",")
            else:
                # Append without headers
                with open(output_file, "a", newline="", encoding="utf-8") as f:
                    df.write_csv(f, separator=",", include_header=False)

            logger.info(f"Batch {batch_num+1} complete: {batch_rows} rows written")

    elapsed_time = time.time() - start_time
    logger.info(
        f"Export complete: {rows_processed} rows exported in {elapsed_time:.2f} seconds"
    )
    logger.info(f"Data exported to {output_file}")

    conn.close()


def export_task_and_deals(
    task_id, output_dir="exports", date=None, exclude_columns=None
):
    """Export a task and its associated deals to separate CSV files."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize exclude_columns if None
    if exclude_columns is None:
        exclude_columns = []

    # Generate filenames with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_suffix = f"_date_{date.replace('-', '')}" if date else ""
    task_file = os.path.join(output_dir, f"task_{task_id}{date_suffix}_{timestamp}.csv")
    deals_file = os.path.join(
        output_dir, f"deals_task_{task_id}{date_suffix}_{timestamp}.csv"
    )

    # Export task data
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        query = "SELECT * FROM deal_tasks WHERE id = %s"
        params = [task_id]

        if date:
            query += " AND date = %s"
            params.append(date)

        cursor.execute(query, params)
        task_data = cursor.fetchone()

        if not task_data:
            logger.error(
                f"Task with ID {task_id}{' for date ' + date if date else ''} not found"
            )
            conn.close()
            return

        # Convert to Polars DataFrame and write to CSV
        task_df = pl.DataFrame([dict(task_data)])

        # Drop excluded columns if they exist in the DataFrame
        for col in exclude_columns:
            if col in task_df.columns:
                task_df = task_df.drop(col)

        with open(task_file, "w", newline="", encoding="utf-8") as f:
            task_df.write_csv(f, separator=",")
        logger.info(f"Task data exported to {task_file}")

    conn.close()

    # Export associated deals
    export_data(
        "deals",
        deals_file,
        batch_size=100000,
        task_id=task_id,
        date=date,
        exclude_columns=exclude_columns,
    )

    logger.info(
        f"Export complete for task {task_id}{' on date ' + date if date else ''}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export data from PostgreSQL to CSV using Polars"
    )
    parser.add_argument(
        "--table", type=str, help="Table name to export", default="deals"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file name (will be placed in exports directory)",
        default=None,
    )
    parser.add_argument("--batch-size", type=int, help="Batch size", default=100000)
    parser.add_argument(
        "--task-id", type=int, help="Export deals for specific task ID", default=None
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Export data for specific date (format: YYYY-MM-DD)",
        default=None,
    )
    parser.add_argument(
        "--exclude-columns",
        type=str,
        help="Comma-separated list of column names to exclude",
        default="deal_task_id",
    )

    args = parser.parse_args()

    # Parse exclude_columns into a list
    exclude_columns = (
        [col.strip() for col in args.exclude_columns.split(",")]
        if args.exclude_columns
        else []
    )

    # Create exports directory if it doesn't exist
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    # If output file is not specified, create one with timestamp
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_suffix = f"_date_{args.date.replace('-', '')}" if args.date else ""

        if args.task_id is not None:
            filename = f"{args.table}_task_{args.task_id}{date_suffix}_{timestamp}.csv"
        else:
            filename = f"{args.table}{date_suffix}_{timestamp}.csv"
    else:
        # Use the provided filename
        filename = args.output

    # Ensure the output path is inside the exports directory
    output_path = os.path.join(export_dir, filename)

    # If task_id is specified, export both task and deals
    if args.task_id is not None and args.table == "deals":
        export_task_and_deals(
            args.task_id,
            output_dir=export_dir,
            date=args.date,
            exclude_columns=exclude_columns,
        )
    else:
        # Otherwise export the specified table
        export_data(
            args.table,
            output_path,
            args.batch_size,
            args.task_id,
            args.date,
            exclude_columns=exclude_columns,
        )
