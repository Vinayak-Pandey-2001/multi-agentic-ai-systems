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

"""RFQ Extractor Agent - Iterative RAG-based criteria extraction."""

from google.adk.agents import LlmAgent
from google.genai import types as genai_types
from . import extractor_prompt
from tools.query_vector_db import (
    query_vector_db_tool,
    # Aliases to handle LLM hallucinations
    query_Vectordb_tool,
    query_vectordb_tool,
    queryVectorDb_tool,
    query_vector_Db_tool,
    query_vactor_db_tool,
)
from shared_libraries.types import ExtractedCriteriaList, ultra_controlled_config

# Configuration
MODEL = "gemini-2.5-pro"  # Complex iterative extraction with adaptive reasoning

rfq_extractor_agent = LlmAgent(
    name="rfq_extractor_agent",
    model=MODEL,
    description=(
        "Iteratively extracts Pre-Qualifying Requirements from RFQ documents via adaptive RAG querying. "
        "Prioritizes technical specifications, then financial and location requirements. "
        "Uses query_vector_db multiple times, analyzing results and refining questions until complete. "
        "Returns structured JSON list of all extracted criteria."
    ),
    instruction=extractor_prompt.return_instructions_rfq_extractor(),
    output_key="extracted_criteria",
    output_schema=ExtractedCriteriaList,  # Enforce structured JSON output
    tools=[
        query_vector_db_tool,  # Primary tool - use iteratively
        # Aliases to tolerate LLM hallucinations
        query_Vectordb_tool,
        query_vectordb_tool,
        queryVectorDb_tool,
        query_vector_Db_tool,
        query_vactor_db_tool,  # Typo: vactor instead of vector
    ],
    generate_content_config=ultra_controlled_config,  # Phase 2: Low temp for determinism
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
