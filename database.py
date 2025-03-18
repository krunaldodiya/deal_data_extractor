import sqlite3
from datetime import date, time
import threading


class Database:
    def __init__(self, db_name="deals.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.lock = threading.Lock()
        self.connect()  # Connect on initialization

    def ensure_connection(self):
        """Ensure database connection is active"""
        with self.lock:
            if self.conn is None or self.cursor is None:
                self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_tables()  # Create tables on connection
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            raise

    def disconnect(self):
        """Close database connection"""
        with self.lock:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None

    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        with self.lock:
            try:
                self.cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS deal_dates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, start_time, end_time)
                )
                """
                )
                self.conn.commit()
            except Exception as e:
                print(f"Error creating tables: {str(e)}")
                raise

    def insert_deal_date(
        self, deal_date: date, start_time: time, end_time: time
    ) -> bool:
        """Insert a new deal date record

        Args:
            deal_date: The selected date
            start_time: The start time
            end_time: The end time

        Returns:
            bool: True if successful, False otherwise
        """
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "INSERT INTO deal_dates (date, start_time, end_time) VALUES (?, ?, ?)",
                    (
                        deal_date.isoformat(),
                        start_time.isoformat(),
                        end_time.isoformat(),
                    ),
                )
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error inserting deal date: {str(e)}")
                return False

    def get_all_deal_dates(self):
        """Fetch all deal date records

        Returns:
            list: List of tuples containing deal date records
        """
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "SELECT id, date, start_time, end_time, status FROM deal_dates ORDER BY date DESC"
                )
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Error fetching deal dates: {str(e)}")
                return None

    def update_deal_status(self, deal_id: int, status: str) -> bool:
        """Update the status of a deal date record

        Args:
            deal_id: The ID of the deal date record
            status: The new status value

        Returns:
            bool: True if successful, False otherwise
        """
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "UPDATE deal_dates SET status = ? WHERE id = ?", (status, deal_id)
                )
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error updating deal status: {str(e)}")
                return False

    def delete_deal(self, deal_id: int) -> bool:
        """Delete a deal date record from the database

        Args:
            deal_id: The ID of the deal date record to delete

        Returns:
            bool: True if successful, False otherwise
        """
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute("DELETE FROM deal_dates WHERE id = ?", (deal_id,))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting deal: {str(e)}")
                return False
