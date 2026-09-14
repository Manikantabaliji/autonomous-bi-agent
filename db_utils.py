import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = PROJECT_ROOT / "data" / "northwind.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create a connection to the Northwind SQLite database.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Northwind database not found at: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


# ============================================================
# GET TABLES
# ============================================================

def get_tables():
    """
    Return all user-created tables.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name != 'sqlite_sequence'
            ORDER BY name;
        """)

        return [
            row[0]
            for row in cursor.fetchall()
        ]

    finally:

        conn.close()


# ============================================================
# GET SCHEMA
# ============================================================

def get_schema():
    """
    Extract the complete database schema.
    """

    tables = get_tables()

    conn = get_connection()

    try:

        schema = {}

        cursor = conn.cursor()

        for table in tables:

            cursor.execute(
                f'PRAGMA table_info("{table}")'
            )

            columns = cursor.fetchall()

            schema[table] = []

            for column in columns:

                schema[table].append({
                    "name": column[1],
                    "type": column[2],
                    "not_null": bool(column[3]),
                    "default": column[4],
                    "primary_key": bool(column[5])
                })

        return schema

    finally:

        conn.close()


# ============================================================
# SCHEMA → TEXT
# ============================================================

def get_schema_text():
    """
    Convert database schema into readable text.
    """

    schema = get_schema()

    lines = []

    for table, columns in schema.items():

        lines.append(
            f"TABLE: {table}"
        )

        for column in columns:

            primary_key = (
                " PRIMARY KEY"
                if column["primary_key"]
                else ""
            )

            lines.append(
                f"  - {column['name']} "
                f"({column['type']})"
                f"{primary_key}"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# EXECUTE READ-ONLY SQL
# ============================================================

def execute_query(sql: str) -> pd.DataFrame:
    """
    Execute a read-only SQL query.

    Only SELECT and WITH queries are allowed.
    """

    if not sql or not sql.strip():

        raise ValueError(
            "SQL query cannot be empty."
        )

    sql_clean = sql.strip().lower()

    # --------------------------------------------------------
    # Only SELECT / WITH
    # --------------------------------------------------------

    if not (
        sql_clean.startswith("select")
        or sql_clean.startswith("with")
    ):

        raise ValueError(
            "Only SELECT or WITH queries are allowed."
        )

    # --------------------------------------------------------
    # Block dangerous SQL operations
    # --------------------------------------------------------

    forbidden_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "attach",
        "detach",
        "pragma"
    ]

    for keyword in forbidden_keywords:

        if f" {keyword} " in f" {sql_clean} ":

            raise ValueError(
                f"Forbidden SQL keyword detected: {keyword}"
            )

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    conn = get_connection()

    try:

        dataframe = pd.read_sql_query(
            sql,
            conn
        )

        return dataframe

    finally:

        conn.close()