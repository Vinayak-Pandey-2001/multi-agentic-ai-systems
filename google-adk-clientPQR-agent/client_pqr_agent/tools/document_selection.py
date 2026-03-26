from typing import List
DOCUMENT_CATALOG = [
    {
        "id": "company_brochure_profile",
        "name": "Company Brochure / Profile",
        "definition": "Overview of the vendor’s business, capabilities, infrastructure, experience, certifications, and key clientele.",
        "validates": ["company_profile", "organizational_capability"]
    },
    {
        "id": "product_catalogue",
        "name": "Product Catalogue",
        "definition": "Detailed listing of products manufactured or supplied, including specifications, models, standards, and technical features.",
        "validates": ["technical_capability", "product_scope"]
    },
    {
        "id": "itr_or_ca_certificate",
        "name": "ITR / CA Certificate",
        "definition": "Income Tax Returns or Chartered Accountant–certified financial statements evidencing turnover and financial performance.",
        "validates": ["turnover", "financial_capacity"]
    },
    {
        "id": "license_copy",
        "name": "License Copy",
        "definition": "Copies of statutory or regulatory licenses required for carrying out the business or executing the specified scope of work.",
        "validates": ["statutory_compliance", "regulatory_eligibility"]
    },
    {
        "id": "manufacturing_capacity_details",
        "name": "Manufacturing Capacity Details",
        "definition": "Information on production capacity, manufacturing facilities, machinery, plant layout, and throughput capabilities.",
        "validates": ["manufacturing_capability", "technical_capacity"]
    },
    {
        "id": "machinery_list",
        "name": "Machinery List",
        "definition": "List of major machinery, equipment, and tools available with the vendor for execution of the scope of work.",
        "validates": ["technical_capacity", "infrastructure"]
    },
    {
        "id": "welder_list",
        "name": "Welder List",
        "definition": "Details of qualified welders including certifications, experience, and qualification levels.",
        "validates": ["manpower_capability", "technical_capacity"]
    },
    {
        "id": "product_image",
        "name": "Product Image",
        "definition": "Image of a finished product that the vendor manufactures or supplies, used for visual verification.",
        "validates": ["product_capability"]
    },
    {
        "id": "work_in_progress_photograph",
        "name": "Work In Progress Photograph",
        "definition": "Photographic evidence of ongoing projects or manufacturing activities.",
        "validates": ["execution_capability", "current_workload"]
    },
    {
        "id": "po_document",
        "name": "PO Document",
        "definition": "Purchase Order copies from clients demonstrating awarded scope, value, and execution history.",
        "validates": ["experience", "commercial_history"]
    },
    {
        "id": "technical_quotation",
        "name": "Technical Quotation",
        "definition": "Vendor’s technical offer detailing compliance to specifications, scope, and standards.",
        "validates": ["technical_compliance"]
    },
    {
        "id": "commercial_techno_commercial_quotation",
        "name": "Commercial / Techno-Commercial Quotation",
        "definition": "Pricing proposal including cost breakup, taxes, duties, and commercial terms.",
        "validates": ["commercial_compliance"]
    },
    {
        "id": "pan",
        "name": "PAN",
        "definition": "Permanent Account Number issued by the Income Tax Department for vendor identification.",
        "validates": ["statutory_compliance", "tax_identity"]
    },
    {
        "id": "incorporation_certificate",
        "name": "Incorporation Certification",
        "definition": "Legal proof of company registration establishing the vendor as a legally incorporated entity.",
        "validates": ["legal_identity"]
    },
    {
        "id": "financial_statements",
        "name": "Financial Statements",
        "definition": "Audited balance sheet, profit & loss statement, and cash flow statement for specified financial years.",
        "validates": ["financial_capacity", "net_worth"]
    },
    {
        "id": "gst_registration",
        "name": "GST Registration",
        "definition": "Goods and Services Tax registration proof confirming statutory tax compliance.",
        "validates": ["statutory_compliance", "tax_compliance"]
    },
    {
        "id": "net_profit_statements",
        "name": "Net Profit Statements",
        "definition": "Statement highlighting profitability trends over specified financial periods.",
        "validates": ["financial_health"]
    },
    {
        "id": "man_power_split",
        "name": "Man Power Split",
        "definition": "Breakup of workforce by roles such as engineers, supervisors, technicians, and workers.",
        "validates": ["manpower_capability"]
    },
    {
        "id": "msme_certificate",
        "name": "MSME Certificate",
        "definition": "Government-issued certificate confirming MSME status of the vendor.",
        "validates": ["msme_eligibility", "statutory_compliance"]
    },
    {
        "id": "ppp_list",
        "name": "PPP List",
        "definition": "List of plant, property, and equipment owned or leased by the vendor.",
        "validates": ["infrastructure", "asset_ownership"]
    },
    {
        "id": "project_image",
        "name": "Project Image",
        "definition": "Photographs of completed or ongoing projects used as visual evidence of experience.",
        "validates": ["experience"]
    },
    {
        "id": "project_list",
        "name": "Project List",
        "definition": "Summary of projects executed or in progress, including scope, value, and timelines.",
        "validates": ["experience"]
    },
    {
        "id": "list_of_projects_completed",
        "name": "List of Project Completed",
        "definition": "Detailed list of successfully completed projects demonstrating execution capability.",
        "validates": ["experience", "past_performance"]
    },
    {
        "id": "client_list",
        "name": "Client List",
        "definition": "List of key customers served by the vendor, used to validate market presence and credibility.",
        "validates": ["experience", "credibility"]
    },
    {
        "id": "vendor_profile",
        "name": "Vendor Profile",
        "definition": "Structured vendor information including legal, financial, technical, and organizational details.",
        "validates": ["company_profile"]
    },
    {
        "id": "drawing",
        "name": "Drawing",
        "definition": "Engineering drawings or layouts submitted for technical evaluation and compliance.",
        "validates": ["technical_compliance"]
    },
    {
        "id": "jobs_executed_by_location",
        "name": "List of Jobs Executed as per Location",
        "definition": "Geographical breakup of executed projects showing regional execution capability.",
        "validates": ["experience", "vicinity"]
    },
    {
        "id": "tnp_list",
        "name": "T&P List",
        "definition": "Tools and Plants list indicating availability of construction and execution equipment.",
        "validates": ["technical_capacity"]
    },
    {
        "id": "boq_item",
        "name": "BOQ Item",
        "definition": "Bill of Quantities detailing item-wise scope, quantities, and measurement units.",
        "validates": ["scope_compliance"]
    },
    {
        "id": "specification",
        "name": "Specification",
        "definition": "Technical specifications defining standards, materials, codes, and performance requirements.",
        "validates": ["technical_compliance"]
    }
]

def document_selection(criteria_type: str) -> str:
    """
    Selects suitable documents from a predefined catalog based on the type of PQR criterion.
    
    This tool maps criterion types to the appropriate validation documents. Use this AFTER
    classifying what a criterion validates (e.g., if a criterion is about turnover, 
    the criteria_type should be "turnover").
    
    Args:
        criteria_type: The validation type for the criterion. Must be ONE of:
            - turnover
            - experience
            - statutory_compliance
            - technical_capability
            - financial_capacity
            - manufacturing_capability
            - manpower_capability
            - product_capability
            - net_worth
            - legal_identity
            - infrastructure
            - execution_capability
            - credibility
            - current_workload
            - commercial_compliance
            - commercial_history
            - company_profile
            - geographical_capability
            - market_presence
            - msme_eligibility
            - organizational_capability
            - past_performance
            - product_scope
            - regulatory_eligibility
            - scope_compliance
            - tax_compliance
            - tax_identity
            - technical_capacity
            - technical_compliance
            - asset_ownership
            - financial_health
    
    Returns:
        JSON string containing list of up to 3 suitable documents with:
        - id: Document identifier
        - name: Human-readable document name
        - definition: What the document validates
        
    Example:
        # For a criterion about annual turnover
        docs = document_selection("turnover")
        # Returns: ITR/CA Certificate, Financial Statements
    """
    import json
    
    results = []
    for doc in DOCUMENT_CATALOG:
        if criteria_type in doc["validates"]:
            results.append({
                "id": doc["id"],
                "name": doc["name"],
                "definition": doc["definition"]
            })
    
    # Return up to 3 documents
    selected_docs = results[:3]
    
    return json.dumps(selected_docs, indent=2)


# Wrap as ADK FunctionTool
from google.adk.tools import FunctionTool
document_selection_tool = FunctionTool(document_selection)
# Alias functions to prevent LLM hallucinations
def select_documents(criteria_type: str) -> str:
    """Alias for document_selection (semantic variation)."""
    return document_selection(criteria_type)

def choose_documents(criteria_type: str) -> str:
    """Alias for document_selection (alternative phrasing)."""
    return document_selection(criteria_type)

# Export alias tools
select_documents_tool = FunctionTool(select_documents)
choose_documents_tool = FunctionTool(choose_documents)
