import opik


@opik.track(name="generate_required_documents")

def generated_documents(employment_type:str,property_type:str)->list[str]:
    common_docs=[

        "id-proof",
        "address-proof",
        "pan-card",
        "bank-statement",
        "property-title",
        "sale-agreement",

    ]

    if employment_type.lower()=="salaried":
        income_docs=["salary-slip","form-16","employment-proof"]

    else:
        income_docs=["itr-returns","business-proof","profit-loss-statement"]

    if property_type.lower()in ["apartment","flat"]:
        property_docs=["builder_noc","approved_building_plan"]

    else:
        property_docs=["land-record","property-tax-receipt"]     

    return common_docs+income_docs+property_docs



@opik.track(name="find_missing_documents")

#Compares required documents with submitted documents.

def find_missing_documents(required_documents:list[str],submitted_documents:list[str])->list[str]:
    return [doc for doc in required_documents if doc not in submitted_documents]
