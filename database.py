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
                CREATE TABLE IF NOT EXISTS deal_tasks (
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

                self.cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS mt5_deals (
                    deal_id INTEGER PRIMARY KEY,
                    action INTEGER,
                    comment TEXT,
                    commission REAL,
                    contract_size REAL,
                    dealer INTEGER,
                    digits INTEGER,
                    digits_currency INTEGER,
                    entry INTEGER,
                    expert_id INTEGER,
                    external_id TEXT,
                    fee REAL,
                    flags INTEGER,
                    gateway TEXT,
                    login INTEGER,
                    market_ask REAL,
                    market_bid REAL,
                    market_last REAL,
                    modification_flags INTEGER,
                    obsolete_value INTEGER,
                    order_id INTEGER,
                    position_id INTEGER,
                    price REAL,
                    price_gateway REAL,
                    price_position REAL,
                    price_sl REAL,
                    price_tp REAL,
                    profit REAL,
                    profit_raw REAL,
                    rate_margin REAL,
                    rate_profit REAL,
                    reason INTEGER,
                    storage REAL,
                    symbol TEXT,
                    tick_size REAL,
                    tick_value REAL,
                    time TIMESTAMP,
                    time_msc INTEGER,
                    value REAL,
                    volume REAL,
                    volume_closed REAL,
                    volume_closed_ext REAL,
                    volume_ext REAL,
                    deal_date_id INTEGER,
                    FOREIGN KEY (deal_date_id) REFERENCES deal_tasks (id)
                )
                """
                )

                self.cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mt5_deals_login_time ON mt5_deals (login, time)"
                )

                self.conn.commit()
            except Exception as e:
                print(f"Error creating tables: {str(e)}")
                raise

    def insert_deal_task(
        self, deal_date: date, start_time: time, end_time: time
    ) -> bool:
        """Insert a new deal task record"""
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "INSERT INTO deal_tasks (date, start_time, end_time) VALUES (?, ?, ?)",
                    (
                        deal_date.isoformat(),
                        start_time.isoformat(),
                        end_time.isoformat(),
                    ),
                )
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error inserting deal task: {str(e)}")
                return False

    def get_all_deal_tasks(self):
        """Fetch all deal task records"""
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "SELECT id, date, start_time, end_time, status FROM deal_tasks ORDER BY date DESC"
                )
                return self.cursor.fetchall()
            except Exception as e:
                print(f"Error fetching deal tasks: {str(e)}")
                return None

    def update_deal_status(self, deal_id: int, status: str) -> bool:
        """Update the status of a deal task record"""
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "UPDATE deal_tasks SET status = ? WHERE id = ?", (status, deal_id)
                )
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error updating deal status: {str(e)}")
                return False

    def delete_deal(self, deal_id: int) -> bool:
        """Delete a deal task record from the database"""
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    "DELETE FROM mt5_deals WHERE deal_date_id = ?", (deal_id,)
                )
                self.cursor.execute("DELETE FROM deal_tasks WHERE id = ?", (deal_id,))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting deal: {str(e)}")
                return False

    def insert_mt5_deals(self, deals_data: list, deal_date_id: int):
        """Insert MT5 deals directly using SQLite"""
        self.ensure_connection()
        with self.lock:
            try:
                # Prepare the SQL statement
                sql = """
                INSERT INTO mt5_deals (
                    deal_id, action, comment, commission, contract_size, dealer,
                    digits, digits_currency, entry, expert_id, external_id, fee,
                    flags, gateway, login, market_ask, market_bid, market_last,
                    modification_flags, obsolete_value, order_id, position_id,
                    price, price_gateway, price_position, price_sl, price_tp,
                    profit, profit_raw, rate_margin, rate_profit, reason,
                    storage, symbol, tick_size, tick_value, time, time_msc,
                    value, volume, volume_closed, volume_closed_ext, volume_ext,
                    deal_date_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?)
                """

                # Execute in chunks
                chunk_size = 1000
                for i in range(0, len(deals_data), chunk_size):
                    chunk = deals_data[i : i + chunk_size]
                    self.cursor.executemany(sql, chunk)
                    self.conn.commit()

                return True
            except Exception as e:
                print(f"Error inserting MT5 deals: {str(e)}")
                return False

    def get_mt5_deals_summary(self, deal_date_id: int):
        """Get summary statistics for MT5 deals"""
        self.ensure_connection()
        with self.lock:
            try:
                self.cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_deals,
                        SUM(volume) as total_volume,
                        SUM(profit) as total_profit,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT login) as unique_logins
                    FROM mt5_deals 
                    WHERE deal_date_id = ?
                """,
                    (deal_date_id,),
                )
                return self.cursor.fetchone()
            except Exception as e:
                print(f"Error getting MT5 deals summary: {str(e)}")
                return None
