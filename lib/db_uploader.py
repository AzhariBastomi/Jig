"""
db_uploader.py — Upload hasil test ke database.

Supported backends:
  - PostgreSQL  : via psycopg2        (pip install psycopg2-binary)
  - MySQL       : via mysql-connector (pip install mysql-connector-python)
  - InfluxDB v2 : via influxdb-client (pip install influxdb-client)

Semua uploader mewarisi UploaderBase dan mengekspos:
  upload(result: TestResultRecord) -> bool
  upload_batch(results: list[TestResultRecord]) -> bool

Contoh:
    from db_uploader import PostgresUploader, PostgresConfig, TestResultRecord
    from datetime import datetime

    cfg = PostgresConfig(host="localhost", database="jig_db")
    up  = PostgresUploader(cfg)
    rec = TestResultRecord(
        station="ST-01", device_id="SN-123", test_name="LED Test",
        command="TEST_LED", result="OK", duration_ms=1500,
    )
    up.upload(rec)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Data record
# ---------------------------------------------------------------------------

@dataclass
class TestResultRecord:
    station:     str
    device_id:   str
    test_name:   str
    command:     str
    result:      str                          # "OK" | "NG"
    duration_ms: int         = 0
    notes:       str         = ""
    timestamp:   datetime    = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def ok(self) -> bool:
        return self.result.upper() == "OK"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class UploaderBase:
    def upload(self, record: TestResultRecord) -> bool:
        raise NotImplementedError

    def upload_batch(self, records: list) -> bool:
        return all(self.upload(r) for r in records)

    def _safe(self, fn, record) -> bool:
        try:
            fn(record)
            return True
        except Exception as e:
            print(f"[db_uploader] Error: {e}")
            return False


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

@dataclass
class PostgresConfig:
    host:     str = "localhost"
    port:     int = 5432
    database: str = "jig_db"
    user:     str = "postgres"
    password: str = ""
    table:    str = "test_results"


class PostgresUploader(UploaderBase):
    """
    Tabel yang dibutuhkan (jalankan sekali):

        CREATE TABLE IF NOT EXISTS test_results (
            id          SERIAL PRIMARY KEY,
            timestamp   TIMESTAMPTZ NOT NULL,
            station     TEXT,
            device_id   TEXT,
            test_name   TEXT,
            command     TEXT,
            result      TEXT,
            duration_ms INTEGER,
            notes       TEXT
        );
    """

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS {table} (
            id          SERIAL PRIMARY KEY,
            timestamp   TIMESTAMPTZ NOT NULL,
            station     TEXT,
            device_id   TEXT,
            test_name   TEXT,
            command     TEXT,
            result      TEXT,
            duration_ms INTEGER,
            notes       TEXT
        );
    """

    INSERT_SQL = """
        INSERT INTO {table}
            (timestamp, station, device_id, test_name, command, result, duration_ms, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """

    def __init__(self, config: PostgresConfig, auto_create_table: bool = True):
        self.cfg = config
        self._auto_create = auto_create_table

    def _connect(self):
        import psycopg2
        return psycopg2.connect(
            host=self.cfg.host, port=self.cfg.port,
            dbname=self.cfg.database, user=self.cfg.user,
            password=self.cfg.password,
        )

    def ensure_table(self):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(self.CREATE_TABLE_SQL.format(table=self.cfg.table))
            conn.commit()

    def upload(self, record: TestResultRecord) -> bool:
        def _do(r):
            with self._connect() as conn:
                if self._auto_create:
                    with conn.cursor() as cur:
                        cur.execute(self.CREATE_TABLE_SQL.format(table=self.cfg.table))
                with conn.cursor() as cur:
                    cur.execute(
                        self.INSERT_SQL.format(table=self.cfg.table),
                        (r.timestamp, r.station, r.device_id, r.test_name,
                         r.command, r.result, r.duration_ms, r.notes),
                    )
                conn.commit()
        return self._safe(_do, record)


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------

@dataclass
class MySQLConfig:
    host:     str = "localhost"
    port:     int = 3306
    database: str = "jig_db"
    user:     str = "root"
    password: str = ""
    table:    str = "test_results"


class MySQLUploader(UploaderBase):
    """
    Tabel yang dibutuhkan:

        CREATE TABLE IF NOT EXISTS test_results (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            timestamp   DATETIME NOT NULL,
            station     VARCHAR(100),
            device_id   VARCHAR(100),
            test_name   VARCHAR(200),
            command     VARCHAR(100),
            result      VARCHAR(10),
            duration_ms INT,
            notes       TEXT
        );
    """

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS {table} (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            timestamp   DATETIME NOT NULL,
            station     VARCHAR(100),
            device_id   VARCHAR(100),
            test_name   VARCHAR(200),
            command     VARCHAR(100),
            result      VARCHAR(10),
            duration_ms INT,
            notes       TEXT
        )
    """

    INSERT_SQL = """
        INSERT INTO {table}
            (timestamp, station, device_id, test_name, command, result, duration_ms, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    def __init__(self, config: MySQLConfig, auto_create_table: bool = True):
        self.cfg = config
        self._auto_create = auto_create_table

    def _connect(self):
        import mysql.connector
        return mysql.connector.connect(
            host=self.cfg.host, port=self.cfg.port,
            database=self.cfg.database, user=self.cfg.user,
            password=self.cfg.password,
        )

    def upload(self, record: TestResultRecord) -> bool:
        def _do(r):
            conn = self._connect()
            cur  = conn.cursor()
            if self._auto_create:
                cur.execute(self.CREATE_TABLE_SQL.format(table=self.cfg.table))
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                self.INSERT_SQL.format(table=self.cfg.table),
                (ts, r.station, r.device_id, r.test_name,
                 r.command, r.result, r.duration_ms, r.notes),
            )
            conn.commit()
            cur.close()
            conn.close()
        return self._safe(_do, record)


# ---------------------------------------------------------------------------
# InfluxDB v2
# ---------------------------------------------------------------------------

@dataclass
class InfluxConfig:
    url:         str = "http://localhost:8086"
    token:       str = ""
    org:         str = "my-org"
    bucket:      str = "jig_results"
    measurement: str = "test_result"


class InfluxUploader(UploaderBase):
    """
    Tidak perlu buat tabel — InfluxDB pakai time-series bucket.
    Tag  : station, device_id, test_name, command, result
    Field: duration_ms, ok (0/1), notes
    """

    def __init__(self, config: InfluxConfig):
        self.cfg = config

    def upload(self, record: TestResultRecord) -> bool:
        def _do(r):
            from influxdb_client import InfluxDBClient, Point, WritePrecision
            from influxdb_client.client.write_api import SYNCHRONOUS

            client = InfluxDBClient(
                url=self.cfg.url, token=self.cfg.token, org=self.cfg.org)
            write_api = client.write_api(write_options=SYNCHRONOUS)

            point = (
                Point(self.cfg.measurement)
                .tag("station",   r.station)
                .tag("device_id", r.device_id)
                .tag("test_name", r.test_name)
                .tag("command",   r.command)
                .tag("result",    r.result)
                .field("duration_ms", r.duration_ms)
                .field("ok",          1 if r.ok else 0)
                .field("notes",       r.notes)
                .time(r.timestamp, WritePrecision.NS)
            )

            write_api.write(bucket=self.cfg.bucket, org=self.cfg.org, record=point)
            client.close()
        return self._safe(_do, record)


# ---------------------------------------------------------------------------
# Multi-uploader (kirim ke beberapa backend sekaligus)
# ---------------------------------------------------------------------------

class MultiUploader(UploaderBase):
    """Kirim satu record ke beberapa backend sekaligus."""

    def __init__(self, *uploaders: UploaderBase):
        self._uploaders = list(uploaders)

    def upload(self, record: TestResultRecord) -> bool:
        results = [u.upload(record) for u in self._uploaders]
        return all(results)
