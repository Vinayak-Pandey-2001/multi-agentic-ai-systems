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

"""Callback functions for RFQ analysis workflow lifecycle management."""

from datetime import datetime
import json
import os
import uuid
from typing import Dict, Any
from google.adk.agents.callback_context import CallbackContext
from shared_libraries import constants


def initialize_rfq_analysis_session(callback_context: CallbackContext):
    """
    Initialize session state before workflow starts.
    Called via before_agent_callback on root agent.
    
    Sets up:
    - System metadata (time, session ID)
    - Workflow step flags (all set to False initially)
    - Empty data structures for accumulating results
    
    Args:
        callback_context: The ADK callback context with state access
    """
    state = callback_context.state
    
    # Only initialize once per session
    if constants.RFQ_ANALYSIS_INITIALIZED in state:
        print(f"⚡ Session already initialized (ID: {state.get(constants.SESSION_ID)})") 
        return
    
    print("🚀 Initializing RFQ analysis session...")
    
    # System metadata
    state[constants.SYSTEM_TIME] = datetime.now().isoformat()
    state[constants.SESSION_ID] = str(uuid.uuid4())[:8]  # Short ID for readability
    state[constants.RFQ_ANALYSIS_INITIALIZED] = True
    
    # Workflow step flags (NEW 2-STAGE WORKFLOW)
    state["step_1_extraction_completed"] = False  # Stage 1: Extraction
    state["step_2_formulation_completed"] = False  # Stage 2: Formulation
    
    # Initialize empty data structures
    state[constants.EXTRACTED_CRITERIA] = []  # Extracted criteria from Stage 1
    state[constants.PQR_CRITERIA] = []  # Final PQR output from Stage 2
    
    # Progress counters
    state[constants.CRITERIA_EXTRACTED_COUNT] = 0
    state[constants.TOTAL_CRITERIA] = 0  # Total PQR criteria (updated after formulation)
    
    print(f"✅ Session initialized (ID: {state[constants.SESSION_ID]})")
    print(f"   - Time: {state[constants.SYSTEM_TIME]}")
    print(f"   - Ready for RFQ analysis workflow")



def post_analysis_callback(callback_context: CallbackContext):
    """
    Post-processing after analysis completes.
    Called via after_agent_callback on coordinator.
    
    Performs:
    - Incremental save to JSON file after extraction completes
    - Validation of PQR criteria structure
    - Summary statistics generation
    
    Args:
        callback_context: The ADK callback context with state access
    """
    state = callback_context.state
    
    print("\n📊 Post-analysis processing...")
    
    pqr_criteria = state.get(constants.PQR_CRITERIA, [])
    
    if not pqr_criteria:
        print("⚠️  No PQR criteria found in state")
        return
    
    # Save incremental checkpoint
    _save_incremental_checkpoint(state, pqr_criteria)
    
    # Mark formulation step as complete
    state[constants.STEP_3_FORMULATION_COMPLETED] = True
    
    # Print summary
    print(f"✅ Analysis complete:")
    print(f"   - Total PQR criteria: {len(pqr_criteria)}")
    print(f"   - Questions asked: {state.get(constants.QUESTIONS_ASKED, 0)}")
    print(f"   - Extraction iterations: {state.get(constants.CURRENT_ITERATION, 1)}")


def _save_incremental_checkpoint(state: Dict[str, Any], pqr_criteria: list):
    """
    Save incremental checkpoint during analysis.
    This ensures no data is lost even if the process crashes.
    
    Args:
        state: Current session state
        pqr_criteria: List of extracted PQR criteria
    """
    try:
        from pathlib import Path
        
        # Create output directory
        output_dir = Path("pqr_outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create checkpoint filename
        session_id = state.get(constants.SESSION_ID, "unknown")
        checkpoint_file = output_dir / f"pqr_checkpoint_{session_id}.json"
        
        # Parse pqr_criteria if it's a string
        criteria_list = pqr_criteria
        if isinstance(pqr_criteria, str):
            try:
                criteria_list = json.loads(pqr_criteria)
            except:
                criteria_list = []
        
        # Also get actual count from extracted_criteria in state
        extracted_criteria = state.get(constants.EXTRACTED_CRITERIA, [])
        asked_questions = state.get(constants.ASKED_QUESTIONS, [])
        
        # Create checkpoint data
        checkpoint_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "total_criteria": len(criteria_list) if isinstance(criteria_list, list) else 0,
            "questions_asked": len(asked_questions),
            "pqr_criteria": criteria_list if isinstance(criteria_list, list) else [],
            "extraction_completeness": state.get(constants.EXTRACTION_COMPLETENESS, 0.0)
        }
        
        # Write to file
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        
        print(f"💾 Checkpoint saved: {checkpoint_file.name}")
        print(f"   ({len(criteria_list) if isinstance(criteria_list, list) else 0} criteria extracted)")
        
    except Exception as e:
        print(f"⚠️  Failed to save checkpoint: {e}")


def cleanup_session_callback(callback_context: CallbackContext):
    """
    Cleanup callback for session end (optional).
    
    Performs:
    - Archive final state to file
    - Clear large temporary data to free memory
    - Log session summary
    
    Args:
        callback_context: The ADK callback context with state access
    """
    state = callback_context.state
    
    session_id = state.get(constants.SESSION_ID, "unknown")
    print(f"\n🧹 Cleaning up session {session_id}...")
    
    # Archive final state to file (optional)
    try:
        archive_dir = "pqr_outputs/session_states"
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = f"{archive_dir}/session_{session_id}_state.json"
        
        # Create a serializable snapshot
        snapshot = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "sections_analyzed": state.get(constants.SECTIONS_ANALYZED, 0),
            "questions_asked": state.get(constants.QUESTIONS_ASKED, 0),
            "criteria_extracted": state.get(constants.CRITERIA_EXTRACTED_COUNT, 0),
            "workflow_completed": state.get(constants.STEP_3_FORMULATION_COMPLETED, False),
        }
        
        with open(archive_path, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        print(f"   - State archived to {archive_path}")
    except Exception as e:
        print(f"   - Failed to archive state: {e}")
    
    print(f"✅ Session {session_id} cleanup complete")
