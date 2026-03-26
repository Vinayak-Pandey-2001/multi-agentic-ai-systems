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

"""PQR Formulator Agent for converting criteria to PQR schema."""

from google.adk.agents import LlmAgent
from google.genai import types as genai_types
from . import formulator_prompt
from tools.document_selection import (
    document_selection_tool,
    select_documents_tool,
    choose_documents_tool,
)
from shared_libraries.types import controlled_config

# Configuration
MODEL = "gemini-2.5-pro"  # Using Pro for more reliable structured output

pqr_formulator_agent = LlmAgent(
    name="pqr_formulator_agent",
    model=MODEL,
    description=(
        "Converts extracted RFQ criteria into Pre-Qualifying Requirements (PQR) JSON schema. "
        "Receives criteria in the instruction, classifies each using document_selection tool, "
        "and outputs a JSON object with the formatted PQR criteria."
    ),
    instruction=formulator_prompt.return_instructions_pqr_formulator(),
    output_key="pqr_criteria",
    generate_content_config=controlled_config,  # Use controlled, not json (json breaks tools)
    tools=[
        document_selection_tool,  # Map criteria to documents
        # Aliases to tolerate hallucinations
        select_documents_tool,
        choose_documents_tool,
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
