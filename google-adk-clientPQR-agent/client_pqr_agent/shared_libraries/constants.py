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

"""Constants used as keys into ADK's session state for RFQ analysis."""


# System Metadata

SYSTEM_TIME = "_time"
RFQ_ANALYSIS_INITIALIZED = "_rfq_analysis_initialized"
SESSION_ID = "_session_id"


# Input State

RFQ_IDENTIFIER = "rfq_identifier"  # Document name or collection identifier
USER_INSTRUCTIONS = "user_instructions"  # Any special instructions from user


# Workflow Step Flags

STEP_1_ANALYSIS_COMPLETED = "step_1_analysis_completed"
STEP_2_EXTRACTION_COMPLETED = "step_2_extraction_completed"
STEP_3_FORMULATION_COMPLETED = "step_3_formulation_completed"


# Data State Keys

RFQ_STRUCTURE = "rfq_structure"  # DocumentAnalysisResult
EXTRACTION_PROGRESS = "extraction_progress"  # ExtractionProgress object
ASKED_QUESTIONS = "asked_questions"  # List of ResearchQuestion
EXTRACTED_CRITERIA = "extracted_criteria"  # List of ExtractedCriterion
PQR_CRITERIA = "pqr_criteria"  # Final List[PQRCriterion]


# Progress Tracking

SECTIONS_ANALYZED = "sections_analyzed"
QUESTIONS_ASKED = "questions_asked"
CRITERIA_EXTRACTED_COUNT = "criteria_extracted_count"
CURRENT_ITERATION = "current_iteration"


# Current Processing Context

CURRENT_CATEGORY = "current_category"  # Which category being extracted
CURRENT_QUESTION = "current_question"  # Current question being asked
LAST_QUERY_RESULTS = "last_query_results"  # Last vector DB results


# Summary Data

TOTAL_QUESTIONS = "total_questions"
TOTAL_CRITERIA = "total_criteria"
EXTRACTION_COMPLETENESS = "extraction_completeness"  # 0.0 to 1.0
