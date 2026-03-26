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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, EITHER express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool for writing PQR criteria results to JSON file."""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from google.adk.tools import ToolContext, FunctionTool


def save_pqr_results_to_json(
    pqr_criteria_json: str,
    filename: str = "",
    tool_context: ToolContext = None
) -> dict:
    """
    Save extracted PQR criteria to JSON file with validation.
    
    Args:
        pqr_criteria_json: JSON string containing list of PQR criteria.
                          Each criterion should have:
                          - criteria: description
                          - required_documents: list of documents (max 3)
                          - references: list of source references
        filename: Optional filename (default: auto-generated with timestamp)
        tool_context: ADK tool context (provides session info)
    
    Returns:
        Dictionary with status, filepath, and statistics
        
    Example:
        pqr_json = json.dumps([
            {
                "criteria": "Annual turnover must exceed $1M",
                "required_documents": ["itr_or_ca_certificate", "financial_statements"],
                "references": ["RFQ Section 2.1, Page 5"]
            }
        ])
        save_pqr_results_to_json(pqr_json, tool_context=tool_context)
    """
    try:
        # Parse the input JSON
        pqr_criteria = json.loads(pqr_criteria_json)
        
        if not isinstance(pqr_criteria, list):
            return {
                "status": "error",
                "message": "pqr_criteria must be a list of criteria objects"
            }
        
        # Validate schema
        validation_warnings = _validate_pqr_schema(pqr_criteria)
        
        # Create output directory
        output_dir = Path("pqr_outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = tool_context.state.get("_session_id", "unknown") if tool_context else "unknown"
            filename = f"pqr_results_{session_id}_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = output_dir / filename
        
        # Add metadata
        from shared_libraries import constants
        asked_questions = tool_context.state.get(constants.ASKED_QUESTIONS, []) if tool_context else []
        
        output_data = {
            "metadata": {
                "session_id": tool_context.state.get("_session_id") if tool_context else "N/A",
                "generation_time": datetime.now().isoformat(),
                "total_criteria": len(pqr_criteria),
                "questions_asked": len(asked_questions),
            },
            "pqr_criteria": pqr_criteria
        }
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        result = {
            "status": "success",
            "message": f"✅ Results saved successfully to {filename}",
            "filepath": str(filepath.absolute()),
            "total_criteria": len(pqr_criteria),
        }
        
        if validation_warnings:
            result["warnings"] = validation_warnings
        
        print(f"\n✅ PQR results saved: {filepath.name}")
        print(f"   - Total criteria: {len(pqr_criteria)}")
        if validation_warnings:
            print(f"   ⚠️  Warnings: {len(validation_warnings)}")
            for warning in validation_warnings[:3]:  # Show first 3
                print(f"      - {warning}")
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON format: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save results: {str(e)}"
        }


def _validate_pqr_schema(pqr_criteria: List[Dict[str, Any]]) -> List[str]:
    """
    Validate PQR criteria schema and return warnings.
    
    Expected schema:
    [
        {
            "criteria": "<description>",
            "required_documents": ["<doc1>", "<doc2>"],
            "references": ["<ref1>", "<ref2>"]
        }
    ]
    
    Returns:
        List of validation warning messages
    """
    warnings = []
    
    for idx, criterion in enumerate(pqr_criteria, 1):
        # Check required fields
        if "criteria" not in criterion:
            warnings.append(f"Criterion {idx}: Missing 'criteria' field")
        elif not criterion["criteria"].strip():
            warnings.append(f"Criterion {idx}: Empty 'criteria' description")
        
        if "required_documents" not in criterion:
            warnings.append(f"Criterion {idx}: Missing 'required_documents' field")
        else:
            docs = criterion["required_documents"]
            if not isinstance(docs, list):
                warnings.append(f"Criterion {idx}: 'required_documents' must be a list")
            elif len(docs) == 0:
                warnings.append(f"Criterion {idx}: No documents specified")
            elif len(docs) > 3:
                warnings.append(f"Criterion {idx}: More than 3 documents specified (max is 3)")
        
        if "references" not in criterion:
            warnings.append(f"Criterion {idx}: Missing 'references' field")
        elif not isinstance(criterion["references"], list):
            warnings.append(f"Criterion {idx}: 'references' must be a list")
        elif len(criterion["references"]) == 0:
            warnings.append(f"Criterion {idx}: No source references provided")
    
    return warnings


# Wrap as ADK FunctionTool
save_pqr_results_to_json_tool = FunctionTool(save_pqr_results_to_json)

# Alias functions to prevent LLM hallucinations
def save_pqr_results(pqr_criteria_json: str, filename: str = "", tool_context: ToolContext = None) -> dict:
    """Alias for save_pqr_results_to_json (shortened name)."""
    return save_pqr_results_to_json(pqr_criteria_json, filename, tool_context)

def write_pqr_json(pqr_criteria_json: str, filename: str = "", tool_context: ToolContext = None) -> dict:
    """Alias for save_pqr_results_to_json (semantic variation)."""
    return save_pqr_results_to_json(pqr_criteria_json, filename, tool_context)

# Export alias tools
save_pqr_results_tool = FunctionTool(save_pqr_results)
write_pqr_json_tool = FunctionTool(write_pqr_json)
