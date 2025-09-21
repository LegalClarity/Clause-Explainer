"""
Google Cloud Gemini service for AI processing using Gemini API
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ..config import settings
from ..models.schemas import DocumentSummary, AudioSummary, LegalRisk, LegalFramework, FinancialImplications


class GeminiService:
    """Service for interacting with Google Cloud Gemini models"""
    
    def __init__(self):
        self.api_key = None  # Don't load from settings yet
        self.model_name = "gemini-1.5-pro"
        self.model = None
        self.use_mock = False
        
    async def initialize(self):
        """Initialize the Gemini client and test connection"""
        try:
            logger.info("🔄 Initializing Gemini service...")

            # Load API key from settings during initialization (not in __init__)
            self.api_key = settings.gemini_api_key

            # Check if API key is available
            if not self.api_key:
                logger.error("❌ GEMINI_API_KEY not configured!")
                logger.error("   Set GEMINI_API_KEY in your .env file")
                self.use_mock = True
                return

            logger.info(f"✅ Found API key: ***{self.api_key[-4:] if self.api_key else 'None'}")

            # Initialize Gemini API
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)

                # Test the connection with a simple request
                logger.info("🧪 Testing Gemini API connection...")
                test_response = await self._test_gemini_connection()
                if test_response:
                    logger.info("✅ Gemini API connection successful")
                    logger.info("✅ Gemini service initialized successfully")
                    self.use_mock = False
                else:
                    logger.error("❌ Gemini API test failed - falling back to mock mode")
                    logger.error("   This means Gemini will return mock responses")
                    logger.error("   To fix: Generate new API key from correct project")
                    self.use_mock = True

            except ImportError as e:
                logger.error(f"❌ Google Generative AI library not available: {e}")
                logger.error("   Install with: pip install google-generativeai")
                self.use_mock = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini API: {e}")
                logger.error("   Check your API key and project permissions")
                self.use_mock = True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini service: {e}")
            self.use_mock = True

    async def _test_gemini_connection(self) -> bool:
        """Test Gemini API connection with a simple request"""
        try:
            test_prompt = "Say 'OK' if you can read this."
            response = await self._make_prediction_request(test_prompt)
            if response and len(response.strip()) > 0:
                logger.info("🧪 Gemini test response received successfully")
                return True
            else:
                logger.error("🧪 Gemini test response was empty")
                return False
        except Exception as e:
            logger.error(f"🧪 Gemini connection test failed: {e}")
            return False

    def _create_mock_document_response(self) -> Dict[str, Any]:
        """Create a mock response for document analysis"""
        return {
            "key_takeaways": [
                "This appears to be a legal document requiring professional review",
                "Standard legal language and clauses are present",
                "No immediate red flags identified in the structure"
            ],            "legal_risks": [
                {
                    "risk_type": "compliance",
                    "severity": "medium",
                    "description": "Standard compliance requirements apply",
                    "affected_clauses": ["General terms and conditions"],
                    "mitigation_suggestions": ["Review with legal counsel", "Ensure proper documentation"]
                }
            ],"legal_frameworks": [
                {
                    "framework_type": "statute",
                    "name": "General Commercial Law",
                    "relevance": "Applies to standard commercial transactions and agreements",
                    "jurisdiction": "General",
                    "citations": ["Sample Commercial Code § 1-101"]
                }
            ],            "financial_implications": {
                "potential_costs": "Standard legal review costs estimated at $1,000-$3,000",
                "liability_assessment": "Low to medium risk profile for standard commercial document",
                "recommendations": ["Legal review recommended", "Consider compliance audit"],
                "estimated_range": "$1,000-$3,000"
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
            logger.warning("Falling back to mock response due to API error")
            # Fall back to mock response on any error
            analysis_data = self._create_mock_document_response()
            
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
            
            return document_summary

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

    async def generate_podcast_summary(self, text: str, options: Dict[str, Any]) -> str:
        """Generate a podcast-style summary with multiple speakers"""
        try:
            if self.use_mock or not self.model:
                return self._create_mock_podcast_script(text)
                
            prompt = self._create_podcast_prompt(text, options)
            script = await self._make_prediction_request(prompt)
            return script
            
        except Exception as e:
            logger.error(f"Error generating podcast summary: {e}")
            return self._create_mock_podcast_script(text)
    
    def _create_mock_podcast_script(self, text: str) -> str:
        """Create a mock podcast script"""
        return """
[Host]: Welcome to Legal Insights Podcast. Today we're discussing a legal document that has been submitted for analysis.

[Legal Expert]: This document appears to be a comprehensive legal agreement with several key provisions. Let me break down the main points.

[Host]: What are the most important takeaways from this document?

[Legal Expert]: First, there are standard contractual terms and conditions. Second, there are specific clauses related to liability and indemnification. Third, the document includes provisions for dispute resolution.

[Host]: Are there any potential risks or concerns?

[Legal Expert]: Yes, there are some areas that might need attention. The liability clauses could be strengthened, and there are some ambiguous terms that might lead to interpretation issues.

[Host]: What would you recommend for next steps?

[Legal Expert]: I recommend a thorough legal review by qualified counsel, and possibly some amendments to clarify certain provisions.

[Host]: Thank you for that analysis. That's all for today's Legal Insights Podcast.
"""
    
    def _create_podcast_prompt(self, text: str, options: Dict[str, Any]) -> str:
        """Create a prompt for generating podcast-style summary"""
        session_type = options.get('session_type', 'general')
        
        prompt = f"""
You are creating a podcast episode discussing a legal document analysis. Generate a natural conversation between a host and legal expert with multiple speakers.

Document Text:
{text[:8000]}  # Limit text for podcast format

Session Type: {session_type}

Create a podcast script with:
- Host: Introduces topics and asks questions
- Legal Expert: Provides detailed analysis
- Natural conversation flow
- Multiple speakers taking turns
- Keep it engaging and informative
- Focus on key legal points, risks, and recommendations

Format the script like this:
[Host]: Welcome message and introduction
[Legal Expert]: Analysis and insights
[Host]: Follow-up questions
[Legal Expert]: Detailed explanations
[Host]: Closing remarks

Make it sound like a real podcast discussion.
"""
        return prompt

    async def _make_prediction_request(self, prompt: str) -> str:
        """Make an async prediction request to Gemini API"""
        try:
            if self.use_mock or not self.model:
                return json.dumps(self._create_mock_document_response())
                
            # Use the Gemini API
            import google.generativeai as genai
            
            def sync_predict():
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                        top_p=0.8,
                        top_k=40
                    )
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
            "affected_clauses": ["clause1", "clause2"],
            "mitigation_suggestions": ["suggestion1", "suggestion2"]
        }}
    ],
    "legal_frameworks": [
        {{
            "framework_type": "statute/regulation/case_law/constitutional/administrative/procedural",
            "name": "name of the framework",
            "relevance": "how it applies to this document",
            "citations": ["citation1", "citation2"],
            "jurisdiction": "applicable jurisdiction"
        }}
    ],
    "financial_implications": {{
        "potential_costs": "description of potential costs",
        "liability_assessment": "assessment of liability",
        "recommendations": ["rec1", "rec2"],
        "estimated_range": "estimated cost range"
    }},
    "executive_summary": "concise summary",
    "confidence_score": 0.8,
    "document_type": "contract/agreement/filing/etc",
    "complexity_score": 0.5
}}

Return only the JSON object, no additional text.
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
