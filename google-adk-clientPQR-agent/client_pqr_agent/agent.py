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

"""RFQ Analyzer Coordinator - Root orchestration agent."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types
import prompt
from sub_agents.rfq_extractor import rfq_extractor_agent
from sub_agents.formulator_agent import pqr_formulator_agent
from tools.memory import (
    memorize_rfq_data_tool,
    memor_ize_rfq_data,
    memororize_rfq_data,
    memorise_rfq_data,
    memorize_progress_tool,
    memorise_progress_tool,
    track_progress_tool,
    get_workflow_state_tool,
)
from tools.json_results_writer import (
    save_pqr_results_to_json_tool,
    save_pqr_results_tool,
    write_pqr_json_tool,
)
from tools.callbacks import (
    initialize_rfq_analysis_session,
    post_analysis_callback
)

# Add logging for agent calls
def log_agent_call_callback(callback_context):
    """Log when sub-agents are called."""
    from google.adk.callbacks import CallbackEventType
    event = callback_context.event
    
    if event.type == CallbackEventType.TOOL_CALL_START:
        tool_name = event.data.get('tool_name', 'unknown')
        print(f"\n🔧 COORDINATOR CALLING TOOL: {tool_name}")

# Configuration
MODEL = "gemini-2.5-pro"  # Most capable for orchestration and state injection

# Root coordinator agent
rfq_analyzer_coordinator = LlmAgent(
    name="rfq_analyzer_coordinator",
    model=MODEL,
    description=(
        "Orchestrates RFQ→PQR conversion workflow through 2 stages: " 
        "1) Iterative criteria extraction via adaptive RAG (technical-first), "
        "2) PQR formulation with document classification. "
        "Manages state injection between agents and ensures complete conversion."
    ),
    instruction=prompt.return_instructions_rfq_analyzer_coordinator(),
    output_key="pqr_conversion_results",
    tools=[
        # Sub-agents (NEW 2-agent architecture)
        AgentTool(agent=rfq_extractor_agent),     # Stage 1: Iterative extraction
        AgentTool(agent=pqr_formulator_agent),     # Stage 2: Formulation
        
        # Memory tools for state management
        memorize_rfq_data_tool,
        # Aliases to tolerate model hallucinations 
        memor_ize_rfq_data,
        memororize_rfq_data,
        memorise_rfq_data,
        memorize_progress_tool,
        memorise_progress_tool,
        track_progress_tool,
        get_workflow_state_tool,
        
        # Output tool with aliases
        save_pqr_results_to_json_tool,
        save_pqr_results_tool,
        write_pqr_json_tool,
    ],
    before_agent_callback=initialize_rfq_analysis_session,
    after_agent_callback=post_analysis_callback,
)
