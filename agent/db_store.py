"""
PostgreSQL persistence layer for home loan applications.

This stores tool updates against application_id/thread_id so every tool call
can be audited and resumed from DB if needed.
"""

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/home_loan",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
    """
    Creates required tables if they do not exist.
    Safe to call on every app/tool execution.
    """

    create_loan_applications_table = """
    CREATE TABLE IF NOT EXISTS loan_applications (
        application_id TEXT PRIMARY KEY,
        application_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
        is_ready_for_assessment BOOLEAN NOT NULL DEFAULT FALSE,
        status TEXT NOT NULL DEFAULT 'in_progress',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_loan_assessments_table = """
    CREATE TABLE IF NOT EXISTS loan_assessments (
        id SERIAL PRIMARY KEY,
        application_id TEXT NOT NULL REFERENCES loan_applications(application_id),
        assessment_result JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_loan_tool_events_table = """
    CREATE TABLE IF NOT EXISTS loan_tool_events (
        id SERIAL PRIMARY KEY,
        application_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        tool_args JSONB NOT NULL DEFAULT '{}'::jsonb,
        tool_result JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_loan_applications_table)
            cursor.execute(create_loan_assessments_table)
            cursor.execute(create_loan_tool_events_table)
        connection.commit()


def upsert_application_state(
    application_id: str,
    application_data: dict[str, Any],
    missing_fields: list[str],
    is_ready_for_assessment: bool,
    status: str = "in_progress",
) -> None:
    """
    Insert/update application state against application_id.
    """

    init_db()

    query = """
    INSERT INTO loan_applications (
        application_id,
        application_data,
        missing_fields,
        is_ready_for_assessment,
        status,
        updated_at
    )
    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (application_id)
    DO UPDATE SET
        application_data = EXCLUDED.application_data,
        missing_fields = EXCLUDED.missing_fields,
        is_ready_for_assessment = EXCLUDED.is_ready_for_assessment,
        status = EXCLUDED.status,
        updated_at = CURRENT_TIMESTAMP;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    application_id,
                    json.dumps(application_data),
                    json.dumps(missing_fields),
                    is_ready_for_assessment,
                    status,
                ),
            )
        connection.commit()


def save_assessment_result(
    application_id: str,
    assessment_result: dict[str, Any],
) -> None:
    """
    Save final assessment result against application_id.
    Does not overwrite application_data in loan_applications.
    """

    init_db()

    ensure_parent_query = """
    INSERT INTO loan_applications (
        application_id,
        status,
        updated_at
    )
    VALUES (%s, 'assessed', CURRENT_TIMESTAMP)
    ON CONFLICT (application_id)
    DO UPDATE SET
        status = 'assessed',
        updated_at = CURRENT_TIMESTAMP;
    """

    insert_assessment_query = """
    INSERT INTO loan_assessments (
        application_id,
        assessment_result
    )
    VALUES (%s, %s);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(ensure_parent_query, (application_id,))
            cursor.execute(
                insert_assessment_query,
                (
                    application_id,
                    json.dumps(assessment_result),
                ),
            )
        connection.commit()


def mark_application_closed(application_id: str) -> None:
    """
    Mark application/conversation as closed against application_id.
    """

    init_db()

    query = """
    INSERT INTO loan_applications (
        application_id,
        status,
        updated_at
    )
    VALUES (%s, 'closed', CURRENT_TIMESTAMP)
    ON CONFLICT (application_id)
    DO UPDATE SET
        status = 'closed',
        updated_at = CURRENT_TIMESTAMP;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (application_id,))
        connection.commit()


def save_tool_event(
    application_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> None:
    """
    Save every tool call for audit/debugging.
    """

    init_db()

    query = """
    INSERT INTO loan_tool_events (
        application_id,
        tool_name,
        tool_args,
        tool_result
    )
    VALUES (%s, %s, %s, %s);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    application_id,
                    tool_name,
                    json.dumps(tool_args),
                    json.dumps(tool_result),
                ),
            )
        connection.commit()


def get_application_from_db(application_id: str) -> dict[str, Any] | None:
    """
    Optional helper to inspect saved application state from DB.
    """

    init_db()

    query = """
    SELECT
        application_id,
        application_data,
        missing_fields,
        is_ready_for_assessment,
        status,
        created_at,
        updated_at
    FROM loan_applications
    WHERE application_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, (application_id,))
            row = cursor.fetchone()

    if not row:
        return None

    return dict(row)