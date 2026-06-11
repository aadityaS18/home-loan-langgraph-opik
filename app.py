"""
Streamlit UI for the Home Loan AI Origination Prototype.

Run:
    streamlit run app.py

This UI has:
1. Applicant-side application form
2. Optional demo presets
3. Admin/Ops dashboard
4. PostgreSQL save/retrieve/update support
"""

from pprint import pformat

import streamlit as st

from agent.controlled_assessment import run_controlled_home_loan_assessment
from database.db import initialize_database
from database.repository import (
    create_application_record,
    get_application_record,
    list_applications,
    update_application_status,
    get_status_history
)


st.set_page_config(
    page_title="Home Loan AI ",
    page_icon="🏠",
    layout="wide",
)


# Create DB tables if they do not already exist.
initialize_database()


BASE_DOCUMENTS = [
    "id_proof",
    "address_proof",
    "pan_card",
    "bank_statement",
    "property_title_deed",
    "sale_agreement",
]

SALARIED_DOCUMENTS = [
    "salary_slips",
    "form_16",
    "employment_proof",
]

SELF_EMPLOYED_DOCUMENTS = [
    "itr_returns",
    "business_proof",
    "profit_loss_statement",
]

APARTMENT_DOCUMENTS = [
    "builder_noc",
    "approved_building_plan",
]

PLOT_HOUSE_DOCUMENTS = [
    "land_record",
    "property_tax_receipt",
]


def get_defaults(application_mode: str) -> dict:
    """Return default field values based on selected application mode."""

    if application_mode == "Demo: Pre-approved applicant":
        return {
            "name": "Aryan",
            "age": 35,
            "employment_type": "salaried",
            "monthly_income": 150000.0,
            "work_experience_years": 8.0,
            "credit_score": 780,
            "existing_emi": 5000.0,
            "loan_amount": 3000000.0,
            "interest_rate": 8.5,
            "tenure_years": 20,
            "loan_purpose": "purchase",
            "property_value": 6000000.0,
            "property_type": "apartment",
            "property_location": "Bangalore",
            "property_age": 4,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
        }

    if application_mode == "Demo: Rejected affordability case":
        return {
            "name": "Rahul",
            "age": 32,
            "employment_type": "salaried",
            "monthly_income": 70000.0,
            "work_experience_years": 5.0,
            "credit_score": 730,
            "existing_emi": 10000.0,
            "loan_amount": 6000000.0,
            "interest_rate": 8.5,
            "tenure_years": 20,
            "loan_purpose": "purchase",
            "property_value": 7500000.0,
            "property_type": "apartment",
            "property_location": "Noida",
            "property_age": 3,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
        }

    # Custom application starts blank/default.
    return {
        "name": "",
        "age": 30,
        "employment_type": "salaried",
        "monthly_income": 0.0,
        "work_experience_years": 0.0,
        "credit_score": 700,
        "existing_emi": 0.0,
        "loan_amount": 0.0,
        "interest_rate": 8.5,
        "tenure_years": 20,
        "loan_purpose": "purchase",
        "property_value": 0.0,
        "property_type": "apartment",
        "property_location": "",
        "property_age": 0,
        "construction_status": "ready_to_move",
        "legal_clearance_status": "clear",
        "valuation_status": "clear",
        "pan_available": True,
        "id_proof_available": True,
        "address_proof_available": True,
    }


def format_currency(value) -> str:
    """Format numeric value as rupee-style text."""
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def get_select_index(options: list[str], value: str) -> int:
    """Safely get selectbox index."""
    if value in options:
        return options.index(value)
    return 0


def validate_application(application: dict) -> list[str]:
    """Validate required application inputs before running assessment."""

    errors = []

    if not application["name"].strip():
        errors.append("Applicant name is required.")

    if application["monthly_income"] <= 0:
        errors.append("Monthly income must be greater than 0.")

    if application["loan_amount"] <= 0:
        errors.append("Requested loan amount must be greater than 0.")

    if application["property_value"] <= 0:
        errors.append("Property value must be greater than 0.")

    if application["property_value"] < application["loan_amount"]:
        errors.append(
            "Property value is lower than requested loan amount. "
            "This may create very high LTV risk. Please confirm the values."
        )

    if not application["property_location"].strip():
        errors.append("Property location is required.")

    if application["credit_score"] < 300 or application["credit_score"] > 900:
        errors.append("Credit score must be between 300 and 900.")

    if application["age"] < 18:
        errors.append("Applicant age must be at least 18.")

    return errors


def display_result(result: dict, application_id: str | None = None):
    """Display assessment result in a clean UI format."""

    assessment = result["assessment"]
    financial = result["financial_metrics"]
    documents = result["documents"]
    kyc = result["kyc"]
    cibil = result["cibil"]

    if application_id:
        st.success(f"Application saved successfully. Application ID: `{application_id}`")

    decision = assessment["decision"]
    risk_level = assessment["risk_level"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Decision", decision)

    with col2:
        st.metric("Risk Level", risk_level)

    with col3:
        st.metric("KYC Status", kyc["kyc_status"])

    with col4:
        st.metric("CIBIL Status", cibil["cibil_status"])

    st.divider()

    st.subheader("Financial Metrics")

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        st.metric("Proposed EMI", format_currency(financial["proposed_emi"]))

    with f2:
        st.metric("LTV Ratio", f'{financial["ltv_ratio"]}%')

    with f3:
        st.metric("DTI Ratio", f'{financial["dti_ratio"]}%')

    with f4:
        st.metric("FOIR Ratio", f'{financial["foir_ratio"]}%')

    f5, f6, f7 = st.columns(3)

    with f5:
        st.metric(
            "Max Affordable New EMI",
            format_currency(financial["max_affordable_new_emi"]),
        )

    with f6:
        st.metric(
            "Estimated Max Eligible Loan",
            format_currency(financial["max_eligible_loan"]),
        )

    with f7:
        st.metric(
            "Requested Amount Above Estimate",
            format_currency(financial["loan_amount_gap"]),
        )

    st.divider()

    st.subheader("Document Status")

    d1, d2 = st.columns(2)

    with d1:
        st.write("**Status:**", documents["document_status"])

    with d2:
        st.write("**Missing Documents:**")
        if documents["missing_documents"]:
            st.warning(", ".join(documents["missing_documents"]))
        else:
            st.success("None")

    with st.expander("View required and submitted documents"):
        st.write("**Required Documents**")
        st.write(documents["required_documents"])

        st.write("**Submitted Documents**")
        st.write(documents["submitted_documents"])

    st.divider()

    st.subheader("Assessment Details")

    c1, c2 = st.columns(2)

    with c1:
        st.write("**Decision Reasons**")
        for reason in assessment["decision_reasons"]:
            st.write(f"- {reason}")

        st.write("**Risk Flags**")
        if assessment["risk_flags"]:
            for flag in assessment["risk_flags"]:
                st.write(f"- {flag}")
        else:
            st.success("No major risk flags.")

    with c2:
        st.write("**Positive Factors**")
        for factor in assessment["positive_factors"]:
            st.write(f"- {factor}")

        st.write("**Recommended Actions**")
        for action in assessment["recommended_actions"]:
            st.write(f"- {action}")

def applicant_status_check_ui():

    st.subheader("Check Existing Application Status")
    st.caption("Enter your application ID to view the latest application status and next steps.")
    
    application_id=st.text_input(

        "Application ID",
        placeholder="Example: app-48371fbce6",

        key="applicant_status_application_id",
        value="app-48371fbce6"
    )



    def applicant_status_check_ui():
        """To check existing application status by application Id"""

        st.subheader("Check Exisitng Application Status")
        st.caption("Enter the application id RECIEVED AFTER SUBMISSION TO VIEW THE LATEST STATUS")
        
        application_id=st.text_input(
            "Application ID",
            placeholder="Example: app-48371fbce6",
            key="applicant_status_application_id",
        )

        if st.button("Check Status"):
            if not  application_id.strip():
                st.error("Please enter an application id.")
                return 
            
            record =get_application_record(application_id.strip())

            if record is None:
                st.error("No application found for this ID.")
                return 
            

            app_data=record["application"]
            assessment=record["assessment"]

            assessment_result=assessment["assessment_result"]
            document_result=assessment["document_result"]
            financial_metrics=assessment["financial_metrics"]

            st.success("Application found")

            c1,c2,c3,c4=st.columns(4)

            with c1:
                st.metric("Application ID",app_data["id"])


            with c2:
                st.metric("Current Status",app_data["status"])


            with c3:
                st.metric("Decision",app_data["decision"])


            with c4:
                st.metric("Risk Level",app_data["risk_level"])

            st.divider()

            st.write("**Applicant Name:**",app_data["applicant_name"])

            st.subheader("Key Finanacial Summary ")

            f1,f2,f3=st.columns(3)

            with f1:
                st.metric("Proposed EMI",format_currency(financial_metrics["proposed_emi"]))

            with f2:
                st.metric("LTV Ratio",f'{financial_metrics["ltv_ratio"]}%')

            with f3:
                st.metric("FOIR ratio",f'{financial_metrics["foir_ratio"]}%')

            st.subheader("Document Status")

            st.write("**Status**",document_result["document_status"])

            if document_result["missing_documents"]:
                st.warning("Missing Documents: " + ", ".join(document_result["missing_documents"]))

            else:
                st.success("No missing documents.")

            st.subheader("Recommended Actions")

            recommended_actions=assessment_result.get("recommended_actions",[])

            if recommended_actions:
                for action in recommended_actions:
                    st.write(f"- {action}")

                else:
                    st.info("No recommended actions available.")    

                st.subheader("Decision Reasons")

                decision_reasons=assessment_result.get(decision_reasons,[])

                if decision_reasons:
                    for reason in decision_reasons:
                        st.write(f"- {reason}")

                else:
                    st.info("No decision reasons available.")        

def applicant_ui():
    """Applicant-side application form."""

    st.header("Applicant Home Loan Application")
    st.caption(
        "Prototype initial assessment. This is not a final bank sanction or approval."
    )

    with st.expander("Already applied? Check your application status"):
        applicant_status_check_ui()

    st.divider()

    application_mode = st.selectbox(
        "Application Mode",
        [
            "Custom Application",
            "Demo: Pre-approved applicant",
            "Demo: Rejected affordability case",
        ],
    )

    defaults = get_defaults(application_mode)

    with st.form("home_loan_application_form"):
        st.subheader("1. Customer Profile")

        c1, c2, c3 = st.columns(3)

        employment_options = ["salaried", "self-employed"]

        with c1:
            name = st.text_input("Applicant Name", value=defaults["name"])
            age = st.number_input(
                "Age",
                min_value=18,
                max_value=75,
                value=defaults["age"],
            )
            employment_type = st.selectbox(
                "Employment Type",
                employment_options,
                index=get_select_index(employment_options, defaults["employment_type"]),
            )

        with c2:
            monthly_income = st.number_input(
                "Monthly Income",
                min_value=0.0,
                value=defaults["monthly_income"],
                step=5000.0,
            )
            work_experience_years = st.number_input(
                "Work Experience in Years",
                min_value=0.0,
                value=defaults["work_experience_years"],
                step=1.0,
            )

        with c3:
            credit_score = st.number_input(
                "Credit Score",
                min_value=300,
                max_value=900,
                value=defaults["credit_score"],
            )
            existing_emi = st.number_input(
                "Existing EMI",
                min_value=0.0,
                value=defaults["existing_emi"],
                step=1000.0,
            )

        st.subheader("2. Loan Requirement")

        l1, l2, l3, l4 = st.columns(4)

        loan_purpose_options = ["purchase", "construction", "refinance"]

        with l1:
            loan_amount = st.number_input(
                "Requested Loan Amount",
                min_value=0.0,
                value=defaults["loan_amount"],
                step=100000.0,
            )

        with l2:
            interest_rate = st.number_input(
                "Interest Rate (%)",
                min_value=0.0,
                value=defaults["interest_rate"],
                step=0.1,
            )

        with l3:
            tenure_years = st.number_input(
                "Tenure in Years",
                min_value=1,
                max_value=40,
                value=defaults["tenure_years"],
            )

        with l4:
            loan_purpose = st.selectbox(
                "Loan Purpose",
                loan_purpose_options,
                index=get_select_index(loan_purpose_options, defaults["loan_purpose"]),
            )

        st.subheader("3. Property Details")

        p1, p2, p3 = st.columns(3)

        property_type_options = ["apartment", "flat", "house", "plot"]
        construction_options = ["ready_to_move", "under_construction"]
        clearance_options = ["clear", "pending", "issue"]

        with p1:
            property_value = st.number_input(
                "Property Value",
                min_value=0.0,
                value=defaults["property_value"],
                step=100000.0,
            )
            property_type = st.selectbox(
                "Property Type",
                property_type_options,
                index=get_select_index(property_type_options, defaults["property_type"]),
            )

        with p2:
            property_location = st.text_input(
                "Property Location",
                value=defaults["property_location"],
            )
            property_age = st.number_input(
                "Property Age in Years",
                min_value=0,
                max_value=100,
                value=defaults["property_age"],
            )

        with p3:
            construction_status = st.selectbox(
                "Construction Status",
                construction_options,
                index=get_select_index(
                    construction_options,
                    defaults["construction_status"],
                ),
            )
            legal_clearance_status = st.selectbox(
                "Legal Clearance Status",
                clearance_options,
                index=get_select_index(
                    clearance_options,
                    defaults["legal_clearance_status"],
                ),
            )
            valuation_status = st.selectbox(
                "Valuation Status",
                clearance_options,
                index=get_select_index(clearance_options, defaults["valuation_status"]),
            )

        st.subheader("4. Mock KYC Details")

        k1, k2, k3 = st.columns(3)

        with k1:
            pan_available = st.checkbox(
                "PAN card available",
                value=defaults["pan_available"],
            )

        with k2:
            id_proof_available = st.checkbox(
                "ID proof available",
                value=defaults["id_proof_available"],
            )

        with k3:
            address_proof_available = st.checkbox(
                "Address proof available",
                value=defaults["address_proof_available"],
            )

        st.subheader("5. Submitted Documents")

        available_document_options = BASE_DOCUMENTS.copy()

        if employment_type == "salaried":
            available_document_options += SALARIED_DOCUMENTS
        else:
            available_document_options += SELF_EMPLOYED_DOCUMENTS

        if property_type in ["apartment", "flat"]:
            available_document_options += APARTMENT_DOCUMENTS
        else:
            available_document_options += PLOT_HOUSE_DOCUMENTS

        # For custom applications, default to only KYC docs selected.
        if application_mode == "Custom Application":
            default_documents = [
                doc
                for doc in ["id_proof", "address_proof", "pan_card"]
                if doc in available_document_options
            ]
        else:
            default_documents = available_document_options

        submitted_documents = st.multiselect(
            "Select documents submitted by applicant",
            options=available_document_options,
            default=default_documents,
        )

        submitted = st.form_submit_button("Run Initial Assessment")

    if submitted:
        application = {
            "name": name.strip(),
            "age": int(age),
            "employment_type": employment_type,
            "monthly_income": float(monthly_income),
            "work_experience_years": float(work_experience_years),
            "credit_score": int(credit_score),
            "existing_emi": float(existing_emi),
            "loan_amount": float(loan_amount),
            "interest_rate": float(interest_rate),
            "tenure_years": int(tenure_years),
            "loan_purpose": loan_purpose,
            "property_value": float(property_value),
            "property_type": property_type,
            "property_location": property_location.strip(),
            "property_age": int(property_age),
            "construction_status": construction_status,
            "legal_clearance_status": legal_clearance_status,
            "valuation_status": valuation_status,
            "pan_available": bool(pan_available),
            "id_proof_available": bool(id_proof_available),
            "address_proof_available": bool(address_proof_available),
            "submitted_documents": submitted_documents,
        }

        errors = validate_application(application)

        # Warning only: property value lower than loan amount is risky but still useful to assess.
        blocking_errors = [
            error
            for error in errors
            if not error.startswith("Property value is lower")
        ]

        for error in errors:
            if error.startswith("Property value is lower"):
                st.warning(error)
            else:
                st.error(error)

        if blocking_errors:
            st.stop()

        with st.spinner("Running controlled tool-based assessment..."):
            result = run_controlled_home_loan_assessment(application)
            application_id = create_application_record(result)

        st.divider()
        st.header("Assessment Result")
        display_result(result, application_id=application_id)


def admin_ui():
    """Admin/Ops dashboard."""

    st.header("Admin / Operations Dashboard")
    st.caption("Review saved loan applications and update processing status.")

    applications = list_applications()

    if not applications:
        st.info("No applications found yet.")
        return

    st.subheader("Saved Applications")

    st.dataframe(
        applications,
        use_container_width=True,
        hide_index=True,
    )

    application_options = [
        f'{app["id"]} | {app["applicant_name"]} | {app["status"]}'
        for app in applications
    ]

    selected = st.selectbox("Select Application", application_options)

    selected_application_id = selected.split(" | ")[0]

    record = get_application_record(selected_application_id)

    if record is None:
        st.error("Application not found.")
        return

    st.divider()
    st.subheader("Application Summary")

    app_data = record["application"]
    assessment = record["assessment"]

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric("Application ID", app_data["id"])

    with s2:
        st.metric("Applicant", app_data["applicant_name"])

    with s3:
        st.metric("Current Status", app_data["status"])

    with s4:
        st.metric("Decision", app_data["decision"])

    st.subheader("Assessment Record")

    reconstructed_result = {
        "application": app_data["application_data"],
        "kyc": assessment["kyc_result"],
        "cibil": assessment["cibil_result"],
        "financial_metrics": assessment["financial_metrics"],
        "documents": assessment["document_result"],
        "assessment": assessment["assessment_result"],
    }

    display_result(reconstructed_result)

    st.divider()
    st.subheader("Status History")

    history=get_status_history(selected_application_id)
    if history:
        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("No status history found for this application")    

    st.divider()
    st.subheader("Update Application Status")

    status_options = [
        "submitted",
        "kyc_pending",
        "cibil_pending",
        "documents_pending",
        "manual_review",
        "pre_approved",
        "rejected",
        "approved_for_processing",
        "sanctioned",
        "disbursed",
    ]

    current_status = app_data["status"]
    status_index = get_select_index(status_options, current_status)

    new_status = st.selectbox(
        "New Status",
        status_options,
        index=status_index,
    )

    note = st.text_area("Admin/Ops Note")

    if st.button("Update Status"):
        updated = update_application_status(
            application_id=selected_application_id,
            new_status=new_status,
            note=note,
        )

        if updated:
            st.success("Application status updated successfully.")
            st.rerun()
        else:
            st.error("Failed to update application status.")

    with st.expander("Raw saved database record"):
        st.code(pformat(record), language="python")


def main():
    st.title("🏠 Home Loan AI Origination Prototype")

    st.write(
        "This prototype uses mock KYC, mock CIBIL, deterministic financial metrics, and document verification to assess home loan applications."
    )

    st.info("This is a prototype initial assessment system. It is not a final bank approval, sanction, or disbursement system.")

    tab1, tab2 = st.tabs(["Applicant Application", "Admin/Ops Dashboard"])

    with tab1:
        applicant_ui()


    with tab2:
        admin_ui()    


if __name__ =="__main__":
    main()
