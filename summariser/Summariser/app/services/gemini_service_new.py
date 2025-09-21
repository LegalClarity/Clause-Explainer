"""
Google Cloud Vertex AI Gemini service for AI processing
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

from ..config import settings
from ..models.schemas import DocumentSummary, AudioSummary, LegalRisk, LegalFramework, FinancialImplications


class GeminiService:
    """Service for interacting with Google Cloud Vertex AI Gemini models"""
    
    def __init__(self):
        self.project_id = settings.google_cloud_project_id
        self.location = settings.vertex_ai_region
        self.model_name = "gemini-1.5-pro-001"
        self.model = None
        self.use_mock = False
        
    async def initialize(self):
        """Initialize the Vertex AI client"""
        try:
            # Check if credentials are available
            credentials_path = settings.google_application_credentials
            if not credentials_path or not os.path.exists(credentials_path):
                logger.warning("Google Cloud credentials not found. Using mock responses for testing.")
                self.use_mock = True
                return
                
            # Try to initialize Vertex AI
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel
                
                vertexai.init(project=self.project_id, location=self.location)
                self.model = GenerativeModel(self.model_name)
                logger.info("Gemini service initialized successfully")
            except ImportError:
                logger.warning("Vertex AI library not available. Using mock responses.")
                self.use_mock = True
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex AI, using mock responses: {e}")
                self.use_mock = True
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            self.use_mock = True

    def _create_mock_document_response(self) -> Dict[str, Any]:
        """Create a mock response for document analysis"""
        return {
            "key_takeaways": [
                "This appears to be a legal document requiring professional review",
                "Standard legal language and clauses are present",
                "No immediate red flags identified in the structure"
            ],
            "legal_risks": [
                {
                    "risk_type": "compliance",
                    "severity": "medium",
                    "description": "Standard compliance requirements apply",
                    "mitigation_steps": ["Review with legal counsel", "Ensure proper documentation"],
                    "likelihood": 0.5,
                    "impact_score": 0.6
                }
            ],
            "legal_frameworks": [
                {
                    "framework_type": "statute",
                    "jurisdiction": "General",
                    "applicable_laws": ["Standard commercial law"],
                    "compliance_requirements": ["Basic documentation requirements"],
                    "citations": []
                }
            ],
            "financial_implications": {
                "estimated_costs": 0.0,
                "potential_savings": 0.0,
                "cost_breakdown": {},
                "financial_risks": [],
                "roi_analysis": "Analysis requires specific financial data"
            },
            "executive_summary": "This document has been processed using a mock analysis due to Google Cloud credentials not being available. For accurate analysis, please configure proper Google Cloud credentials.",
            "confidence_score": 0.3,
            "document_type": "legal_document",
            "complexity_score": 0.5
        }

    def _create_mock_audio_response(self) -> Dict[str, Any]:
        """Create a mock response for audio analysis"""
        return {
            "key_takeaways": [
                "Audio transcription processed successfully",
                "Mock analysis provided due to missing credentials"
            ],
            "key_participants": [
                {
                    "name": "Speaker 1",
                    "role": "unknown",
                    "speaking_time_percentage": 60.0,
                    "key_contributions": ["Primary speaker in the session"]
                }
            ],
            "action_items": [
                {
                    "task": "Configure Google Cloud credentials for full analysis",
                    "assigned_to": "System Administrator", 
                    "deadline": None,
                    "priority": "high",
                    "status": "pending"
                }
            ],
            "objections_rulings": [],
            "executive_summary": "This audio transcription has been processed using a mock analysis due to Google Cloud credentials not being available.",
            "confidence_score": 0.3,
            "session_type": "general",
            "total_duration": 0.0
        }

    async def analyze_document(self, text: str, options: Dict[str, Any]) -> DocumentSummary:
        """Analyze a legal document using Gemini or mock response"""
        try:
            if self.use_mock or not self.model:
                logger.info("Using mock document analysis response")
                analysis_data = self._create_mock_document_response()
            else:
                # Real Gemini analysis would go here
                prompt = self._create_document_analysis_prompt(text, options)
                result_text = await self._make_prediction_request(prompt)
                
                # Parse JSON response
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_text = result_text[start_idx:end_idx]
                else:
                    json_text = result_text
                    
                analysis_data = json.loads(json_text)
            
            # Convert to DocumentSummary model
            legal_risks = [
                LegalRisk(**risk) for risk in analysis_data.get('legal_risks', [])
            ]
            
            legal_frameworks = [
                LegalFramework(**framework) for framework in analysis_data.get('legal_frameworks', [])
            ]
            
            financial_implications = FinancialImplications(**analysis_data.get('financial_implications', {}))
            
            document_summary = DocumentSummary(
                key_takeaways=analysis_data.get('key_takeaways', []),
                legal_risks=legal_risks,
                legal_frameworks=legal_frameworks,
                financial_implications=financial_implications,
                executive_summary=analysis_data.get('executive_summary', ''),
                confidence_score=analysis_data.get('confidence_score', 0.8),
                document_type=analysis_data.get('document_type'),
                complexity_score=analysis_data.get('complexity_score')
            )
            
            logger.info("Document analysis completed successfully")
            return document_summary
            
        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            raise

    async def analyze_audio_transcription(self, transcription_data: Dict[str, Any], options: Dict[str, Any]) -> AudioSummary:
        """Analyze an audio transcription using Gemini or mock response"""
        try:
            if self.use_mock or not self.model:
                logger.info("Using mock audio analysis response")
                analysis_data = self._create_mock_audio_response()
            else:
                # Real Gemini analysis would go here
                prompt = self._create_audio_analysis_prompt(transcription_data, options)
                result_text = await self._make_prediction_request(prompt)
                
                # Parse JSON response
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_text = result_text[start_idx:end_idx]
                else:
                    json_text = result_text
                    
                analysis_data = json.loads(json_text)
            
            # Convert to AudioSummary model
            from ..models.schemas import KeyParticipant, ActionItem, ObjectionRuling
            
            key_participants = [
                KeyParticipant(**participant) for participant in analysis_data.get('key_participants', [])
            ]
            
            action_items = [
                ActionItem(**item) for item in analysis_data.get('action_items', [])
            ]
            
            objections_rulings = [
                ObjectionRuling(**ruling) for ruling in analysis_data.get('objections_rulings', [])
            ]
            
            audio_summary = AudioSummary(
                key_takeaways=analysis_data.get('key_takeaways', []),
                key_participants=key_participants,
                action_items=action_items,
                objections_rulings=objections_rulings,
                executive_summary=analysis_data.get('executive_summary', ''),
                confidence_score=analysis_data.get('confidence_score', 0.8),
                session_type=analysis_data.get('session_type'),
                total_duration=analysis_data.get('total_duration', 0.0)
            )
            
            logger.info("Audio analysis completed successfully")
            return audio_summary
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            raise

    async def _make_prediction_request(self, prompt: str) -> str:
        """Make an async prediction request to Vertex AI"""
        try:
            if self.use_mock or not self.model:
                return json.dumps(self._create_mock_document_response())
                
            # Use the Vertex AI GenerativeModel API
            def sync_predict():
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 8192,
                        "top_p": 0.8,
                        "top_k": 40
                    }
                )
                return response.text
            
            # Run the synchronous function in a thread pool
            response_text = await asyncio.get_event_loop().run_in_executor(None, sync_predict)
            return response_text
            
        except Exception as e:
            logger.error(f"Error making prediction request: {e}")
            raise

    def _create_document_analysis_prompt(self, text: str, options: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for document analysis"""
        summary_length = options.get('summary_length', 'comprehensive')
        include_financial = options.get('include_financial_analysis', True)
        include_risk = options.get('include_risk_assessment', True)
        
        prompt = f"""
You are a legal AI assistant specializing in document analysis. Analyze the following legal document and provide a comprehensive summary in JSON format.

Document Text:
{text[:10000]}  # Limit text to prevent token overflow

Analysis Requirements:
- Summary Length: {summary_length}
- Include Financial Analysis: {include_financial}
- Include Risk Assessment: {include_risk}

Please provide your analysis in the following JSON structure:
{{
    "key_takeaways": ["list of key points"],
    "legal_risks": [
        {{
            "risk_type": "type of risk",
            "severity": "low/medium/high/critical", 
            "description": "detailed description",
            "mitigation_steps": ["step1", "step2"],
            "likelihood": 0.0-1.0,
            "impact_score": 0.0-1.0
        }}
    ],
    "legal_frameworks": [
        {{
            "framework_type": "statute/regulation/case_law/constitutional/administrative/procedural",
            "jurisdiction": "applicable jurisdiction",
            "applicable_laws": ["law1", "law2"],
            "compliance_requirements": ["req1", "req2"],
            "citations": ["citation1", "citation2"]
        }}
    ],
    "financial_implications": {{
        "estimated_costs": 0.0,
        "potential_savings": 0.0,
        "cost_breakdown": {{"category": "amount"}},
        "financial_risks": ["risk1", "risk2"],
        "roi_analysis": "analysis text"
    }},
    "executive_summary": "concise summary",
    "confidence_score": 0.0-1.0,
    "document_type": "contract/agreement/filing/etc",
    "complexity_score": 0.0-1.0
}}

Ensure all fields are properly filled and the response is valid JSON.
"""
        return prompt

    def _create_audio_analysis_prompt(self, transcription_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for audio analysis"""
        session_type = options.get('session_type', 'general')
        include_speakers = options.get('include_speaker_analysis', True)
        include_actions = options.get('include_action_items', True)
        
        transcript_text = transcription_data.get('transcript', '')
        
        prompt = f"""
You are a legal AI assistant specializing in audio transcription analysis. Analyze the following legal audio transcript and provide a comprehensive summary in JSON format.

Transcript:
{transcript_text[:10000]}  # Limit text to prevent token overflow

Session Type: {session_type}
Include Speaker Analysis: {include_speakers}
Include Action Items: {include_actions}

Please provide your analysis in the following JSON structure:
{{
    "key_takeaways": ["list of key points"],
    "key_participants": [
        {{
            "name": "participant name",
            "role": "judge/attorney/witness/plaintiff/defendant/court_reporter/bailiff/expert_witness/unknown",
            "speaking_time_percentage": 0.0-100.0,
            "key_contributions": ["contribution1", "contribution2"]
        }}
    ],
    "action_items": [
        {{
            "task": "task description",
            "assigned_to": "person/role",
            "deadline": "date or null",
            "priority": "low/medium/high/critical",
            "status": "pending/in_progress/completed"
        }}
    ],
    "objections_rulings": [
        {{
            "objection_type": "hearsay/relevance/leading/speculation/other",
            "ruling": "sustained/overruled",
            "context": "context description",
            "timestamp": "time in transcript"
        }}
    ],
    "executive_summary": "concise summary",
    "confidence_score": 0.0-1.0,
    "session_type": "{session_type}",
    "total_duration": 0.0
}}

Ensure all fields are properly filled and the response is valid JSON.
"""
        return prompt


# Global Gemini service instance
gemini_service = GeminiService()
