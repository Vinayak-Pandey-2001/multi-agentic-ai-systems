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

"""Async runner for RFQ→PQR conversion workflow."""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
from google.adk import runners
from google.adk.agents import RunConfig
from google.genai import types

# Add the google-agent-adk-clientPQR-agent directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "client_pqr_agent"))

from agent import rfq_analyzer_coordinator
from shared_libraries import constants

# Load environment variables
load_dotenv()


async def run_rfq_to_pqr_conversion():
    """
    Run the complete RFQ→PQR conversion workflow.
    
    This executes the 3-stage process:
    1. Document Analysis
    2. Information Extraction  
    3. PQR Formulation
    
    The root coordinator agent orchestrates all stages and saves final results.
    """
    print("=" * 80)
    print("🚀 Starting RFQ→PQR Conversion Workflow")
    print("=" * 80)
    print()
    
    # Initial prompt to coordinator
    user_message = (
        "Please analyze the RFQ documents in the vector database and convert "
        "all qualifying criteria into Pre-Qualifying Requirements (PQR) format. "
        "Follow the 3-stage workflow: analyze structure, extract criteria, and "
        "formulate PQR with document classifications."
    )
    
    try:
        print("📤 Sending request to coordinator agent...")
        print(f"   Message: {user_message}")
        print()
        
        # Create InMemoryRunner (following google_agent_adk pattern)
        runner = runners.InMemoryRunner(agent=rfq_analyzer_coordinator)
        
        # Create session
        session_id = str(uuid.uuid4())
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="user",
            session_id=session_id,
        )
        
        print("⚙️  Running RFQ→PQR workflow...")
        print()
        
        # Configure run
        config = RunConfig()
        
        # Execute the workflow
        async for event in runner.run_async(
            user_id="user",
            session_id=session_id,
            run_config=config,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            ),
        ):
            # Print model responses
            if getattr(event.content, "role", None) == "model":
                if event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text)
        
        print("\n" + "=" * 80)
        print("✅ Workflow Execution Complete")
        print("=" * 80)
        
        # Access session state
        current_session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="user",
            session_id=session_id
        )
        
        if current_session:
            state = current_session.state
        else:
            state = {}
        
        # Print workflow summary
        print("\n📊 WORKFLOW SUMMARY")
        print("-" * 80)
        print(f"Session ID: {session_id}")
        print(f"Start Time: {state.get(constants.SYSTEM_TIME, 'N/A')}")
        print()
        
        # Stage completion status
        print("Stage Completion:")
        print(f"  ✓ Stage 1 (Analysis): {state.get(constants.STEP_1_ANALYSIS_COMPLETED, False)}")
        print(f"  ✓ Stage 2 (Extraction): {state.get(constants.STEP_2_EXTRACTION_COMPLETED, False)}")
        print(f"  ✓ Stage 3 (Formulation): {state.get(constants.STEP_3_FORMULATION_COMPLETED, False)}")
        print()
        
        # Extraction metrics
        print("Extraction Metrics:")
        print(f"  - Sections Analyzed: {state.get(constants.SECTIONS_ANALYZED, 0)}")
        print(f"  - Questions Asked: {state.get(constants.QUESTIONS_ASKED, 0)}")
        print(f"  - Criteria Extracted: {state.get(constants.CRITERIA_EXTRACTED_COUNT, 0)}")
        # Convert completeness to float if it's stored as string
        completeness = state.get(constants.EXTRACTION_COMPLETENESS, 0.0)
        if isinstance(completeness, str):
            completeness = float(completeness)
        print(f"  - Extraction Completeness: {completeness*100:.1f}%")
        print()
        
        # Final PQR output
        pqr_criteria = state.get(constants.PQR_CRITERIA, [])
        if isinstance(pqr_criteria, str):
            try:
                pqr_criteria = json.loads(pqr_criteria)
            except:
                pass
        
        print("PQR Output:")
        print(f"  - Total PQR Criteria: {len(pqr_criteria) if isinstance(pqr_criteria, list) else 'N/A'}")
        print()
        
        # Expected output file
        print(f"📁 Output File Pattern: pqr_outputs/pqr_results_{session_id}_*.json")
        print(f"   (Check pqr_outputs/ directory for the actual file)")
        print()
        
        # Cleanup
        try:
            await runner.close()
        except AttributeError:
            pass  # Ignore cleanup warnings
        
        print("=" * 80)
        print("✅ RFQ→PQR Conversion Complete!")
        print("=" * 80)
        
        return state
        
    except Exception as e:
        print(f"\n❌ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point for async execution."""
    asyncio.run(run_rfq_to_pqr_conversion())


if __name__ == "__main__":
    main()
