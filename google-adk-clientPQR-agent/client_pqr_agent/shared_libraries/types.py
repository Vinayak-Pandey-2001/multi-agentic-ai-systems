# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common data schema and types for RFQ analysis system."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from google.genai import types as genai_types


# ============================================
# Configuration for JSON response generation
# ============================================
json_response_config = genai_types.GenerateContentConfig(
    response_mime_type="application/json"
)

# Deterministic generation for consistent analysis
deterministic_config = genai_types.GenerateContentConfig(
    temperature=0.1,
    top_p=0.5
)

# Creative generation for diverse question generation
creative_config = genai_types.GenerateContentConfig(
    temperature=0.7,
    top_p=0.9
)

# Controlled generation for extraction
controlled_config = genai_types.GenerateContentConfig(
    temperature=0.3,
    top_p=0.7
)

# Force function calling - prevents LLM from just describing actions
force_function_calling_config = genai_types.GenerateContentConfig(
    temperature=0.3,
    top_p=0.7,
    tool_config=genai_types.ToolConfig(
        function_calling_config=genai_types.FunctionCallingConfig(
            mode=genai_types.FunctionCallingConfigMode.ANY  # Force tool use
        )
    )
)


# ============================================
# Document Type Definition
# ============================================
# All possible document types that can be required for PQR validation
DOCUMENT_TYPES = Literal[
    "asset_ownership",
    "commercial_compliance",
    "commercial_history",
    "company_profile",
    "credibility",
    "current_workload",
    "execution_capability",
    "experience",
    "financial_capacity",
    "financial_health",
    "geographical_capability",
    "infrastructure",
    "legal_identity",
    "manufacturing_capability",
    "manpower_capability",
    "market_presence",
    "msme_eligibility",
    "net_worth",
    "organizational_capability",
    "past_performance",
    "product_capability",
    "product_scope",
    "regulatory_eligibility",
    "scope_compliance",
    "statutory_compliance",
    "tax_compliance",
    "tax_identity",
    "technical_capability",
    "technical_capacity",
    "technical_compliance",
    "turnover"
]


# ============================================
# RFQ Analysis Models
# ============================================
class RFQSection(BaseModel):
    """A section identified in the RFQ document"""
    section_name: str = Field(description="Name of the section (e.g., 'Eligibility Criteria', 'Technical Requirements')")
    category: str = Field(description="Category of requirements (eligibility, financial, technical, experience)")
    importance: str = Field(description="Importance level: 'high', 'medium', 'low'", default="medium")
    content_summary: str = Field(description="Brief summary of what this section contains")


class DocumentAnalysisResult(BaseModel):
    """Output from document analysis stage"""
    document_type: str = Field(description="Type of RFQ document (RFQ/RFP/Tender/EOI)")
    sections_found: List[RFQSection] = Field(description="Key sections identified in the document")
    extraction_strategy: str = Field(description="Plan for extracting criteria from this document")
    key_areas: List[str] = Field(description="Critical areas to focus on during extraction")
    total_sections: int = Field(description="Total number of sections to analyze")


# ============================================
# Information Extraction Models
# ============================================
class ResearchQuestion(BaseModel):
    """A question to be asked to the vector database"""
    question: str = Field(description="The question to ask")
    target_category: str = Field(description="Which category this question targets (eligibility, financial, etc.)")
    rationale: str = Field(description="Why this question is important")
    iteration: int = Field(description="Which iteration this question belongs to (1, 2, 3...)", default=1)


class ExtractedCriterion(BaseModel):
    """A single criterion extracted from the RFQ"""
    criteria_description: str = Field(description="Clear description of the criterion/requirement")
    category: str = Field(description="Category: technical, financial, eligibility, experience, location, compliance")
    document_type_hint: str = Field(
        description="Suggested document type from the 31 predefined types to validate this criterion",
        default=""
    )
    source_references: List[str] = Field(
        description="References to source chunks (URLs, page numbers, section names)",
        default_factory=list
    )
    confidence: float = Field(
        description="Confidence in extraction quality (0.0-1.0)",
        ge=0.0,
        le=1.0,
        default=0.8
    )


class ExtractedCriteriaList(BaseModel):
    """Complete list of criteria extracted from RFQ - enforces structured output"""
    criteria: List[ExtractedCriterion] = Field(
        description="All criteria extracted from the RFQ document",
        default_factory=list
    )


class ExtractionProgress(BaseModel):
    """Progress tracking for information extraction"""
    questions_asked: List[ResearchQuestion] = Field(default_factory=list)
    criteria_extracted: List[ExtractedCriterion] = Field(default_factory=list)
    categories_covered: List[str] = Field(default_factory=list)
    current_iteration: int = Field(default=1)
    extraction_complete: bool = Field(default=False)
    completeness_score: float = Field(
        description="How complete is the extraction (0.0-1.0)",
        ge=0.0,
        le=1.0,
        default=0.0
    )


# ============================================
# PQR Output Models (Final Schema)
# ============================================
class PQRCriterion(BaseModel):
    """Single PQR criterion - matches user's required schema"""
    criteria: str = Field(description="Description of the criterion")
    required_documents: List[str] = Field(
        description="List of documents required to validate the criterion (max 3)",
        max_length=3,
        default_factory=list
    )
    references: List[str] = Field(
        description="List of references from the RFQ Document (sources, page numbers, sections)",
        default_factory=list
    )


class PQRCriteriaSet(BaseModel):
    """Complete set of PQR criteria - output schema"""
    criteria_list: List[PQRCriterion] = Field(
        description="List of all extracted PQR criteria",
        default_factory=list
    )


class PQROutput(BaseModel):
    """Complete PQR output with metadata"""
    pqr_criteria: List[PQRCriterion] = Field(description="List of PQR criteria")
    metadata: dict = Field(
        description="Metadata about the extraction (session_id, timestamp, source_document, etc.)",
        default_factory=dict
    )
    total_criteria: int = Field(description="Total number of criteria extracted")
    extraction_summary: str = Field(description="Summary of the extraction process")


# ============================================
# Workflow State Models
# ============================================
class WorkflowProgress(BaseModel):
    """Current workflow progress snapshot"""
    current_step: str = Field(description="Current step name")
    sections_analyzed: int = Field(default=0)
    questions_asked: int = Field(default=0)
    criteria_extracted: int = Field(default=0)
    step_statuses: dict = Field(default_factory=dict)


class RFQAnalysisSession(BaseModel):
    """Complete session state"""
    session_id: str
    workflow_progress: WorkflowProgress
    rfq_structure: Optional[DocumentAnalysisResult] = None
    extraction_progress: Optional[ExtractionProgress] = None
    pqr_criteria: List[PQRCriterion] = Field(default_factory=list)

# Ultra-controlled config for maximum determinism (Phase 2 improvement)
ultra_controlled_config = genai_types.GenerateContentConfig(
    temperature=0.2,  # Very low for consistent, deterministic outputs
    top_p=0.8,        # Focused sampling
    top_k=20,         # Limit token choices
    candidate_count=1,
)
