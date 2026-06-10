"""
Database repository functions for saving and reading home-loan applications.

This file stores structured application and assessment results in PostgreSQL.
"""

import uuid
from typing import Any

from psycopg.types.json import Jsonb

from database.db import get_connection


def create_application_record(result: dict[str, Any]) -> str:
    """
    Save a controlled assessment result into PostgreSQL.

    Returns:
        application_id
    """

    application_id = f"app-{uuid.uuid4().hex[:10]}"

    application = result["application"]
    assessment = result["assessment"]

    applicant_name = application["name"]
    decision = assessment["decision"]
    risk_level = assessment["risk_level"]

    # Map assessment decision to a simple application status.
    if decision == "pre_approved":
        status = "pre_approved"
    elif decision == "needs_documents":
        status = "documents_pending"
    elif decision == "manual_review":
        status = "manual_review"
    else:
        status = "rejected"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO applications (
                    id,
                    applicant_name,
                    status,
                    decision,
                    risk_level,
                    application_data
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    application_id,
                    applicant_name,
                    status,
                    decision,
                    risk_level,
                    Jsonb(application),
                ),
            )

            cur.execute(
                """
                INSERT INTO assessment_results (
                    application_id,
                    kyc_result,
                    cibil_result,
                    financial_metrics,
                    document_result,
                    assessment_result
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    application_id,
                    Jsonb(result["kyc"]),
                    Jsonb(result["cibil"]),
                    Jsonb(result["financial_metrics"]),
                    Jsonb(result["documents"]),
                    Jsonb(result["assessment"]),
                ),
            )

            cur.execute(
                """
                INSERT INTO status_history (
                    application_id,
                    old_status,
                    new_status,
                    note
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    application_id,
                    None,
                    status,
                    "Application created from controlled assessment.",
                ),
            )

        conn.commit()

    return application_id


def get_application_record(application_id: str) -> dict[str, Any] | None:
    """
    Retrieve a saved application and its latest assessment result.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    applicant_name,
                    status,
                    decision,
                    risk_level,
                    application_data,
                    created_at,
                    updated_at
                FROM applications
                WHERE id = %s
                """,
                (application_id,),
            )

            app_row = cur.fetchone()

            if app_row is None:
                return None

            cur.execute(
                """
                SELECT
                    kyc_result,
                    cibil_result,
                    financial_metrics,
                    document_result,
                    assessment_result,
                    created_at
                FROM assessment_results
                WHERE application_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (application_id,),
            )

            assessment_row = cur.fetchone()

    return {
        "application": {
            "id": app_row[0],
            "applicant_name": app_row[1],
            "status": app_row[2],
            "decision": app_row[3],
            "risk_level": app_row[4],
            "application_data": app_row[5],
            "created_at": app_row[6],
            "updated_at": app_row[7],
        },
        "assessment": {
            "kyc_result": assessment_row[0] if assessment_row else None,
            "cibil_result": assessment_row[1] if assessment_row else None,
            "financial_metrics": assessment_row[2] if assessment_row else None,
            "document_result": assessment_row[3] if assessment_row else None,
            "assessment_result": assessment_row[4] if assessment_row else None,
            "created_at": assessment_row[5] if assessment_row else None,
        },
    }


def list_applications() -> list[dict[str, Any]]:
    """
    Return all saved applications, newest first.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    applicant_name,
                    status,
                    decision,
                    risk_level,
                    created_at
                FROM applications
                ORDER BY created_at DESC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "applicant_name": row[1],
            "status": row[2],
            "decision": row[3],
            "risk_level": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def update_application_status(
    application_id: str,
    new_status: str,
    note: str | None = None,
) -> bool:
    """
    Update application status and save status-history entry.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM applications
                WHERE id = %s
                """,
                (application_id,),
            )

            row = cur.fetchone()

            if row is None:
                return False

            old_status = row[0]

            cur.execute(
                """
                UPDATE applications
                SET status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_status, application_id),
            )

            cur.execute(
                """
                INSERT INTO status_history (
                    application_id,
                    old_status,
                    new_status,
                    note
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    application_id,
                    old_status,
                    new_status,
                    note,
                ),
            )

        conn.commit()

    

    return True


def get_status_history(application_id:str)->list[dict[str,Any]]:
    """Will return the history for saved application"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
SELECT
old_status,
new_status,
note,
created_at
FROM status_history
WHERE application_id=%s
ORDER BY created_at ASC
""",
(application_id,),
            )

            rows = cur.fetchall()

    return [
        {
            "old_status": row[0],
            "new_status": row[1],
            "note": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]