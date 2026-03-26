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

"""Memory tools for RFQ analysis session state management."""

from datetime import datetime
import json
from typing import Dict, Any
from google.adk.tools import ToolContext, FunctionTool


def memorize_rfq_data(key: str, value: str, tool_context: ToolContext) -> dict:
    """
    Store RFQ analysis workflow data in session state.
    
    Args:
        key: State variable key from constants module
        value: Data to store (will be JSON serialized if needed)
        tool_context: ADK tool context with state access
    
    Returns:
        Status message confirming storage
        
    Example:
        memorize_rfq_data("rfq_structure", analysis_json, tool_context)
        memorize_rfq_data("current_category", "financial", tool_context)
    """
    tool_context.state[key] = value
    print(f"💾 Stored '{key}' = '{value}' in session state")
    return {"status": f'Stored "{key}" in session state'}


def memorize_list_append(key: str, value: str, tool_context: ToolContext) -> dict:
    """
    Append to a list in session state (for accumulating results).
    
    Use for:
    - Accumulating asked questions
    - Building extracted criteria list
    - Collecting references
    
    Args:
        key: State variable key for the list
        value: Item to append to the list
        tool_context: ADK tool context
        
    Returns:
        Status message confirming append
        
    Example:
        memorize_list_append("asked_questions", question_json, tool_context)
        memorize_list_append("extracted_criteria", criterion_json, tool_context)
    """
    print(f"📝 memorize_list_append called - key: {key}")
    
    if key not in tool_context.state:
        tool_context.state[key] = []
    elif not isinstance(tool_context.state[key], list):
        # If the key exists but is not a list, convert it to a list
        tool_context.state[key] = [tool_context.state[key]]
    
    # Avoid duplicates for certain keys
    if value not in tool_context.state[key]:
        tool_context.state[key].append(value)
        print(f"✅ Stored item in '{key}' list (now has {len(tool_context.state[key])} items)")
        return {"status": f'Appended to "{key}" list (now has {len(tool_context.state[key])} items)'}
    else:
        print(f"⚠️  Duplicate value in '{key}' list, skipped")
        return {"status": f'Value already in "{key}" list, skipped duplicate'}


def memorize_progress(step: str, status: str, tool_context: ToolContext) -> dict:
    """
    Track workflow progress for user visibility and decision making.
    
    Args:
        step: Workflow step name (analysis, extraction, formulation)
        status: Status (in_progress, completed, failed)
        tool_context: ADK tool context
        
    Returns:
        Status message with timestamp
        
    Example:
        memorize_progress("analysis", "completed", tool_context)
        memorize_progress("extraction", "in_progress", tool_context)
    """
    progress_key = f"step_{step}_status"
    timestamp_key = f"step_{step}_timestamp"
    
    tool_context.state[progress_key] = status
    tool_context.state[timestamp_key] = datetime.now().isoformat()
    
    return {
        "status": f"Step '{step}' marked as '{status}'",
        "timestamp": tool_context.state[timestamp_key]
    }


def get_workflow_state(tool_context: ToolContext) -> dict:
    """
    Retrieve current workflow state for display or decision making.
    
    Provides a snapshot of:
    - Sections analyzed
    - Questions asked
    - Criteria extracted
    - Workflow step statuses
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Dictionary with workflow progress metrics
    """
    from shared_libraries import constants
    
    state = tool_context.state
    
    questions_list = state.get(constants.ASKED_QUESTIONS, [])
    criteria_list = state.get(constants.EXTRACTED_CRITERIA, [])
    
    return {
        "workflow_state": {
            "sections_analyzed": state.get(constants.SECTIONS_ANALYZED, 0),
            "questions_asked": len(questions_list),
            "criteria_extracted": len(criteria_list),
            "current_iteration": state.get(constants.CURRENT_ITERATION, 1),
        },
        "step_statuses": {
            "step_1_analysis": state.get(constants.STEP_1_ANALYSIS_COMPLETED, False),
            "step_2_extraction": state.get(constants.STEP_2_EXTRACTION_COMPLETED, False),
            "step_3_formulation": state.get(constants.STEP_3_FORMULATION_COMPLETED, False),
        },
        "extraction_completeness": state.get(constants.EXTRACTION_COMPLETENESS, 0.0),
    }


def get_extracted_criteria(tool_context: ToolContext) -> dict:
    """
    Retrieve the full list of extracted criteria from session state.
    
    This tool is specifically for the PQR formulator agent to access
    the criteria that were extracted in Stage 2.
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Dictionary with extracted criteria list and count
    """
    from shared_libraries import constants
    
    state = tool_context.state
    criteria_list = state.get(constants.EXTRACTED_CRITERIA, [])
    
    print(f"\n📊 get_extracted_criteria called!")
    print(f"   Found {len(criteria_list)} criteria in session state")
    if len(criteria_list) > 0:
        print(f"   First criterion: {criteria_list[0][:100]}...")
    
    return {
        "criteria_count": len(criteria_list),
        "extracted_criteria": criteria_list,
        "message": f"Retrieved {len(criteria_list)} criteria from session state"
    }


def capture_workflow_snapshot(tool_context: ToolContext) -> dict:
    """
    Capture complete workflow state snapshot for debugging/logging.
    
    Provides comprehensive view of:
    - All workflow flags
    - All data counts
    - Progress metrics
    - Timestamps
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Complete state snapshot dictionary
    """
    from shared_libraries import constants
    
    state = tool_context.state
    
    return {
        "snapshot_timestamp": datetime.now().isoformat(),
        "system_metadata": {
            "session_id": state.get(constants.SESSION_ID, "unknown"),
            "system_time": state.get(constants.SYSTEM_TIME),
            "initialized": state.get(constants.RFQ_ANALYSIS_INITIALIZED, False),
        },
        "workflow_status": {
            "analysis_completed": state.get(constants.STEP_1_ANALYSIS_COMPLETED, False),
            "extraction_completed": state.get(constants.STEP_2_EXTRACTION_COMPLETED, False),
            "formulation_completed": state.get(constants.STEP_3_FORMULATION_COMPLETED, False),
        },
        "data_counts": {
            "questions": len(state.get(constants.ASKED_QUESTIONS, [])),
            "criteria": len(state.get(constants.EXTRACTED_CRITERIA, [])),
        },
        "progress": {
            "sections_analyzed": state.get(constants.SECTIONS_ANALYZED, 0),
            "questions_asked": state.get(constants.QUESTIONS_ASKED, 0),
            "criteria_extracted": state.get(constants.CRITERIA_EXTRACTED_COUNT, 0),
            "current_iteration": state.get(constants.CURRENT_ITERATION, 1),
        }
    }


# Alias FunctionTool to catch common LLM hallucinated tool names
# Each alias needs a unique function for Gemini API
def memor_ize_rfq_data_func(key: str, value: str, tool_context: ToolContext) -> dict:
    """Alias for memorize_rfq_data (hyphenated)."""
    return memorize_rfq_data(key, value, tool_context)

def memororize_rfq_data_func(key: str, value: str, tool_context: ToolContext) -> dict:
    """Alias for memorize_rfq_data (extra 'o' typo)."""
    return memorize_rfq_data(key, value, tool_context)

def memorise_rfq_data_func(key: str, value: str, tool_context: ToolContext) -> dict:
    """Alias for memorize_rfq_data (British spelling)."""
    return memorize_rfq_data(key, value, tool_context)

# Create FunctionTools - the tool name will be the function name
memorize_rfq_data_tool = FunctionTool(memorize_rfq_data)
memor_ize_rfq_data = FunctionTool(memor_ize_rfq_data_func)
memororize_rfq_data = FunctionTool(memororize_rfq_data_func)
memorise_rfq_data = FunctionTool(memorise_rfq_data_func)

memorize_list_append_tool = FunctionTool(memorize_list_append)
memorize_progress_tool = FunctionTool(memorize_progress)
get_workflow_state_tool = FunctionTool(get_workflow_state)
get_extracted_criteria_tool = FunctionTool(get_extracted_criteria)
capture_workflow_snapshot_tool = FunctionTool(capture_workflow_snapshot)

# Additional aliases for memorize_progress
def memorise_progress_func(step: str, status: str, tool_context: ToolContext) -> dict:
    """Alias for memorize_progress (British spelling)."""
    return memorize_progress(step, status, tool_context)

def track_progress_func(step: str, status: str, tool_context: ToolContext) -> dict:
    """Alias for memorize_progress (semantic variation)."""
    return memorize_progress(step, status, tool_context)

# Export progress aliases
memorise_progress_tool = FunctionTool(memorise_progress_func)
track_progress_tool = FunctionTool(track_progress_func)
