"""File centralises database connection logic for the project"""


import os 

from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/home_loan",)

def get_connection():

    """Create postgresql connection"""

    return psycopg.connect(DATABASE_URL)


def initialize_database():
    """
    Create required database tables using database/schema.sql.
    """
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

        conn.commit()

