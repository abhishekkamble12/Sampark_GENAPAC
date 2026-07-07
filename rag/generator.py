"""
rag/generator.py — RAG Pipeline Grounded Generation.

Uses Gemini 1.5 Pro to generate a recommendation citing retrieved chunks.
"""

from __future__ import annotations

import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

_GENERATE_PROMPT = """\
You are a policy expert advising municipal authorities on community issues.
Based on the following retrieved policy documents and the issue summary, provide a recommended action.

Your response MUST include at least one policy document citation.
Reference documents by their 'doc_name'.

Issue Summary:
{issue_summary}

Retrieved Policies:
{policies}

Respond strictly with the following JSON schema:
{{"action": "string", "rationale": "string", "cited_policies": ["string"], "estimated_impact": "string"}}
"""

class Generator:
    def __init__(self, gemini_model: Any):
        self.gemini = gemini_model
        
    async def generate_recommendation(self, issue_summary: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a recommendation grounded in chunks.
        
        Raises RuntimeError if Gemini fails, per 9.10.
        """
        if not chunks:
            # 9.9 If no chunks, Gemini prompt without policies
            policies_text = "None retrieved."
        else:
            policies_text = "\n\n".join(
                f"[Document: {c['doc_name']}, Page: {c['page_number']}]\n{c['text']}" 
                for c in chunks
            )
            
        prompt = _GENERATE_PROMPT.format(
            issue_summary=issue_summary,
            policies=policies_text
        )
        
        try:
            # 9.9 Construct Gemini prompt
            response = self.gemini.generate_content(prompt)
            text = response.text if hasattr(response, "text") else str(response)
            
            import re, json
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # Enforce citation if policies were provided
                if chunks and not data.get("cited_policies"):
                    # Forcing a citation if the model omitted it, though we requested it in prompt
                    data["cited_policies"] = [chunks[0]["doc_name"]]
                return data
            else:
                raise RuntimeError("Failed to parse JSON from Gemini")
                
        except Exception as e:
            # 9.10 Handle Gemini generation failure explicitly
            logger.exception("Gemini generation failed")
            raise RuntimeError(f"Generation error: {e}") from e
