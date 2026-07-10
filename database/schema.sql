CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    applicant_name TEXT NOT NULL,
    status TEXT NOT NULL,
    decision TEXT,
    risk_level TEXT,
    application_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assessment_results (
    id SERIAL PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    kyc_result JSONB NOT NULL,
    cibil_result JSONB NOT NULL,
    financial_metrics JSONB NOT NULL,
    document_result JSONB NOT NULL,
    assessment_result JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS status_history (
    id SERIAL PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
