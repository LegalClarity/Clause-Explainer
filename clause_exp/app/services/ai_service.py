import openai
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel, Field
from ..config.settings import settings

logger = logging.getLogger(__name__)

class ClauseAnalysisResponse(BaseModel):
    """Structured response for clause analysis"""
    severity_level: int = Field(description="Severity level from 1-5")
    severity_reasoning: str = Field(description="Brief explanation of severity assessment")
    risk_factors: List[str] = Field(description="List of specific risk factors")
    legal_implications: str = Field(description="Detailed explanation of legal implications")
    plain_language_explanation: str = Field(description="Simple explanation for non-lawyers")
    compliance_flags: List[str] = Field(description="List of compliance issues")
    recommendations: List[str] = Field(description="List of actionable recommendations")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")

class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass

class AIService:
    """Service for AI-powered clause analysis using OpenAI or Google Gemini"""

    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AI clients based on configuration"""
        # Initialize OpenAI
        if settings.openai_api_key:
            try:
                openai.api_key = settings.openai_api_key.get_secret_value()
                self.openai_client = openai.OpenAI()
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

        # Initialize Google Gemini
        if settings.google_api_key:
            try:
                genai.configure(api_key=settings.google_api_key.get_secret_value())
                self.gemini_model = genai.GenerativeModel('gemini-2.5-pro')
                logger.info("Google Gemini client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

        if not self.openai_client and not self.gemini_model:
            logger.warning("No AI clients available - analysis will fail")

    def _get_preferred_client(self):
        """Get the preferred AI client"""
        if settings.ai_model_preference == "openai" and self.openai_client:
            return "openai"
        elif settings.ai_model_preference == "google" and self.gemini_model:
            return "google"
        elif self.openai_client:
            return "openai"
        elif self.gemini_model:
            return "google"
        else:
            raise AIServiceError("No AI clients available")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def analyze_clause(
        self,
        clause_text: str,
        clause_type: str,
        document_type: str
    ) -> Dict[str, Any]:
        """Analyze a single clause for severity, risks, and implications"""
        try:
            client = self._get_preferred_client()

            prompt = self._build_clause_analysis_prompt(clause_text, clause_type, document_type)

            if client == "openai":
                return await self._analyze_with_openai(prompt)
            else:
                return await self._analyze_with_gemini(prompt, clause_text, clause_type, document_type)

        except Exception as e:
            logger.error(f"Failed to analyze clause: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Return fallback analysis with more detailed error info
            return self._get_fallback_analysis(clause_text, clause_type, str(e))

    async def analyze_clauses_batch(
        self,
        clauses: List[Dict[str, Any]],
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Analyze multiple clauses in batch"""
        results = []

        for clause_data in clauses:
            try:
                analysis = await self.analyze_clause(
                    clause_data['text'],
                    clause_data['type'],
                    document_type
                )
                results.append({
                    'clause_id': clause_data['clause_id'],
                    'analysis': analysis
                })
            except Exception as e:
                logger.error(f"Failed to analyze clause {clause_data.get('clause_id', 'unknown')}: {str(e)}")
                import traceback
                logger.error(f"Batch analysis error traceback: {traceback.format_exc()}")
                # Add fallback analysis with error details
                results.append({
                    'clause_id': clause_data['clause_id'],
                    'analysis': self._get_fallback_analysis(
                        clause_data['text'],
                        clause_data['type'],
                        str(e)
                    )
                })

        return results

    def _build_clause_analysis_prompt(self, clause_text: str, clause_type: str, document_type: str) -> str:
        """Build the analysis prompt for AI"""
        return f"""You are a legal document analysis assistant. Analyze contract clauses and respond ONLY with valid JSON.

Required JSON format:
{{
    "severity_level": 3,
    "severity_reasoning": "brief explanation",
    "risk_factors": ["risk1", "risk2"],
    "legal_implications": "legal explanation",
    "plain_language_explanation": "simple explanation",
    "compliance_flags": ["flag1"],
    "recommendations": ["rec1", "rec2"],
    "confidence_score": 0.85
}}

Document Type: {document_type}
Clause Type: {clause_type}
Clause Content: {clause_text[:800]}

Guidelines:
- Severity: 1=Low, 2=Minor, 3=Moderate, 4=High, 5=Critical
- Be factual and professional
- Confidence score 0.0-1.0

Output only JSON:"""

    async def _analyze_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Analyze using OpenAI GPT"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a legal expert analyzing contract clauses. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()

            # Try to parse JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Extract JSON from response if wrapped in text
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    return json.loads(json_content)
                else:
                    raise ValueError("No JSON found in response")

        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise

    async def _analyze_with_gemini(self, prompt: str, clause_text: str = "", clause_type: str = "", document_type: str = "") -> Dict[str, Any]:
        """Analyze using Google Gemini with structured output"""
        try:
            # Use structured output for consistent JSON responses
            analysis_prompt = f"""Analyze this {clause_type} clause from a {document_type} document.

Clause content: {clause_text[:1000]}

Provide a detailed legal analysis focusing on risks, implications, and recommendations."""

            response = self.gemini_model.generate_content(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                    top_p=0.1,
                    top_k=1,
                    response_mime_type="application/json",
                    response_schema=ClauseAnalysisResponse
                )
            )

            # With structured output, Gemini should return parsed data directly
            if hasattr(response, 'parsed') and response.parsed:
                parsed_data = response.parsed
                if isinstance(parsed_data, ClauseAnalysisResponse):
                    logger.info("Successfully parsed structured response from Gemini")
                    return parsed_data.model_dump()
                else:
                    logger.warning(f"Unexpected parsed response type: {type(parsed_data)}")

            # Fallback: check for text content and parse JSON manually with better error handling
            try:
                content = response.text.strip()
                if content:
                    logger.info(f"Gemini raw response: {content[:500]}...")

                    # Try to fix common JSON issues
                    content = self._fix_malformed_json(content)

                    parsed_json = json.loads(content)
                    # Validate it matches our schema
                    validated = ClauseAnalysisResponse(**parsed_json)
                    return validated.model_dump()
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                # Try to extract partial data if JSON is malformed
                partial_data = self._extract_partial_json(content)
                if partial_data:
                    try:
                        validated = ClauseAnalysisResponse(**partial_data)
                        logger.info("Successfully extracted partial structured data")
                        return validated.model_dump()
                    except Exception as partial_e:
                        logger.warning(f"Partial data extraction also failed: {partial_e}")

            # Check for safety/filtering issues
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finishReason'):
                    finish_reason = candidate.finishReason
                    if finish_reason == "SAFETY":
                        logger.warning("Gemini response blocked by safety filters")
                        raise ValueError("Gemini response blocked by safety filters")

            # Last resort: use fallback analysis
            logger.warning("Structured output failed, using fallback analysis")
            return self._get_fallback_analysis(clause_text, clause_type, "Structured output failed")

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            raise

    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract and validate JSON from AI response using multiple strategies"""

        if not content or not content.strip():
            return None

        # Clean the content
        content = content.strip()

        # Strategy 1: Direct JSON parsing
        try:
            parsed = json.loads(content)
            if self._validate_json_structure(parsed):
                return parsed
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown code blocks
        import re
        json_patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json\n{content}\n```
            r'```(?:json)?\s*\n(\{.*?\})\n```',  # ```json\n{content}\n``` or ```\n{content}\n```
            r'```\s*\n(\{.*?\})\s*\n```',  # ```\n{content}\n```
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the match
                    cleaned_match = match.strip()
                    if not cleaned_match:
                        continue

                    parsed = json.loads(cleaned_match)
                    if self._validate_json_structure(parsed):
                        return parsed
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse JSON from pattern {pattern}: {e}")
                    continue

        # Strategy 3: Find the largest JSON-like content between braces
        json_candidates = []
        brace_count = 0
        start_idx = -1

        for i, char in enumerate(content):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        json_content = content[start_idx:i+1]
                        parsed = json.loads(json_content)
                        if self._validate_json_structure(parsed):
                            json_candidates.append((len(json_content), parsed))
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1

        # Return the largest valid JSON candidate
        if json_candidates:
            json_candidates.sort(key=lambda x: x[0], reverse=True)
            return json_candidates[0][1]

        # Strategy 4: Try to extract JSON from common response formats
        # Remove common prefixes that might interfere with JSON parsing
        prefixes_to_remove = [
            "Here's the analysis:",
            "Analysis:",
            "Here's my analysis:",
            "Based on the clause,",
            "The analysis is:",
            "JSON Response:",
        ]

        for prefix in prefixes_to_remove:
            if content.upper().startswith(prefix.upper()):
                cleaned_content = content[len(prefix):].strip()
                try:
                    parsed = json.loads(cleaned_content)
                    if self._validate_json_structure(parsed):
                        return parsed
                except json.JSONDecodeError:
                    pass

        # Strategy 5: Look for JSON within the text using more aggressive pattern matching
        # Find all potential JSON objects (balanced braces)
        potential_jsons = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        for potential_json in potential_jsons:
            try:
                parsed = json.loads(potential_json)
                if self._validate_json_structure(parsed):
                    return parsed
            except json.JSONDecodeError:
                continue

        logger.warning(f"Could not extract valid JSON from response: {content[:200]}...")
        return None

    async def _try_simplified_analysis(self, clause_text: str, clause_type: str, document_type: str) -> Optional[Dict[str, Any]]:
        """Try a simplified analysis when the main analysis fails"""
        try:
            # Create a very basic fallback analysis first
            fallback = self._get_basic_fallback_analysis(clause_text, clause_type, document_type)
            logger.info("Using basic fallback analysis due to AI service issues")

            # Try simplified AI analysis as enhancement
            try:
                simplified_prompt = f"""Analyze this contract clause briefly.

Clause type: {clause_type}
Content: {clause_text[:300]}

Return only: {{"severity": 1-5, "risks": ["risk1"], "issues": "brief"}}"""

                response = self.gemini_model.generate_content(
                    simplified_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=500,
                    )
                )

                # Check for blocked response
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finishReason') and candidate.finishReason == "SAFETY":
                        logger.warning("Simplified analysis also blocked by safety filters")
                        return fallback

                content = response.text.strip()
                if content:
                    logger.info(f"Simplified analysis response: {content[:200]}...")
                    # Try to enhance fallback with AI response
                    try:
                        enhanced = self._extract_json_from_response(content)
                        if enhanced:
                            # Merge with fallback
                            fallback.update({
                                k: v for k, v in enhanced.items()
                                if k in fallback and v is not None
                            })
                    except:
                        pass

            except Exception as e:
                logger.warning(f"Simplified AI analysis failed: {e}")

            return fallback

        except Exception as e:
            logger.error(f"Simplified analysis failed: {e}")
            return self._get_fallback_analysis(clause_text, clause_type, str(e))

    def _get_basic_fallback_analysis(self, clause_text: str, clause_type: str, document_type: str) -> Dict[str, Any]:
        """Get a basic fallback analysis without AI"""
        severity_level = 3
        risk_factors = ["Requires manual review"]
        compliance_flags = ["Pending analysis"]

        # Basic type-based assessment
        if clause_type in ['termination', 'liability', 'penalty']:
            severity_level = 4
            risk_factors = ["High risk clause type", "Requires legal review"]
        elif clause_type in ['payment', 'financial']:
            severity_level = 3
            risk_factors = ["Financial terms need verification"]

        return {
            "severity_level": severity_level,
            "severity_reasoning": f"Basic assessment for {clause_type} clause - requires detailed legal review",
            "risk_factors": risk_factors,
            "legal_implications": f"This {clause_type} clause may have significant legal implications that require professional review",
            "plain_language_explanation": f"This is a {clause_type} clause that affects your rights and obligations",
            "compliance_flags": compliance_flags,
            "recommendations": ["Consult legal professional", "Review clause carefully"],
            "confidence_score": 0.3
        }

    def _fix_malformed_json(self, content: str) -> str:
        """Try to fix common JSON formatting issues"""
        # Remove any trailing commas before closing braces/brackets
        content = content.strip()

        # Fix unterminated strings by ensuring quotes are balanced
        # This is a basic fix - in production you'd want more sophisticated parsing
        if content.count('"') % 2 != 0:
            # Odd number of quotes, try to close the last string
            last_quote_pos = content.rfind('"')
            if last_quote_pos != -1 and last_quote_pos < len(content) - 1:
                # Check if there's more content after the last quote
                remaining = content[last_quote_pos + 1:]
                if remaining and not remaining[0].isspace() and remaining[0] not in [',', '}', ']']:
                    # Try to close the string
                    content = content[:last_quote_pos + 1] + '"' + remaining

        return content

    def _extract_partial_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Try to extract partial JSON data when full parsing fails"""
        try:
            # Look for key-value pairs using regex
            import re

            # Extract severity_level
            severity_match = re.search(r'"severity_level"\s*:\s*(\d+)', content)
            severity_level = int(severity_match.group(1)) if severity_match else 3

            # Extract confidence_score
            confidence_match = re.search(r'"confidence_score"\s*:\s*([0-9.]+)', content)
            confidence_score = float(confidence_match.group(1)) if confidence_match else 0.5

            # Extract arrays
            risk_factors = []
            risk_match = re.search(r'"risk_factors"\s*:\s*\[([^\]]*)\]', content)
            if risk_match:
                items = re.findall(r'"([^"]*)"', risk_match.group(1))
                risk_factors = [item for item in items if item]

            compliance_flags = []
            compliance_match = re.search(r'"compliance_flags"\s*:\s*\[([^\]]*)\]', content)
            if compliance_match:
                items = re.findall(r'"([^"]*)"', compliance_match.group(1))
                compliance_flags = [item for item in items if item]

            recommendations = []
            rec_match = re.search(r'"recommendations"\s*:\s*\[([^\]]*)\]', content)
            if rec_match:
                items = re.findall(r'"([^"]*)"', rec_match.group(1))
                recommendations = [item for item in items if item]

            # Extract strings
            severity_reasoning = self._extract_string_field(content, "severity_reasoning") or f"Analysis level {severity_level} - requires review"
            legal_implications = self._extract_string_field(content, "legal_implications") or "Legal implications require professional review"
            plain_language = self._extract_string_field(content, "plain_language_explanation") or f"This clause has been assessed at level {severity_level}"

            return {
                "severity_level": severity_level,
                "severity_reasoning": severity_reasoning,
                "risk_factors": risk_factors,
                "legal_implications": legal_implications,
                "plain_language_explanation": plain_language,
                "compliance_flags": compliance_flags,
                "recommendations": recommendations,
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.warning(f"Partial JSON extraction failed: {e}")
            return None

    def _extract_string_field(self, content: str, field_name: str) -> Optional[str]:
        """Extract a string field value from malformed JSON"""
        import re
        pattern = f'"{field_name}"\s*:\s*"([^"]*(?:\\\\.[^"]*)*)"'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
        return None

    def _validate_json_structure(self, data: Dict[str, Any]) -> bool:
        """Validate that the parsed JSON has the expected structure"""
        required_keys = [
            'severity_level', 'severity_reasoning', 'risk_factors',
            'legal_implications', 'plain_language_explanation',
            'compliance_flags', 'recommendations', 'confidence_score'
        ]

        if not isinstance(data, dict):
            return False

        # Check if all required keys exist
        for key in required_keys:
            if key not in data:
                return False

        # Validate severity_level is an integer 1-5
        if not isinstance(data.get('severity_level'), int) or not (1 <= data['severity_level'] <= 5):
            return False

        # Validate confidence_score is a float 0.0-1.0
        if not isinstance(data.get('confidence_score'), (int, float)) or not (0.0 <= data['confidence_score'] <= 1.0):
            return False

        # Validate array fields are lists
        array_fields = ['risk_factors', 'compliance_flags', 'recommendations']
        for field in array_fields:
            if not isinstance(data.get(field), list):
                return False

        return True

    def _get_fallback_analysis(self, clause_text: str, clause_type: str, error_message: str = None) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails"""
        logger.warning("Using fallback analysis due to AI service failure")

        # Basic fallback based on clause type and content
        severity_level = 3  # Default moderate
        risk_factors = []
        compliance_flags = []
        recommendations = ["Consult with legal professional for detailed analysis"]

        # Adjust based on clause type with more comprehensive analysis
        if clause_type in ['termination', 'liability']:
            severity_level = 4
            risk_factors = ["Requires legal review", "High liability exposure"]
            compliance_flags = ["Potential compliance issues"]
        elif clause_type in ['payment', 'financial']:
            severity_level = 3
            risk_factors = ["Financial terms require verification"]
            compliance_flags = ["Review payment terms"]
        elif clause_type in ['confidentiality', 'intellectual_property']:
            severity_level = 4
            risk_factors = ["Potential legal exposure", "IP protection concerns"]
            compliance_flags = ["IP compliance review needed"]
        elif clause_type in ['maintenance', 'notice']:
            severity_level = 2
            risk_factors = ["Standard clause", "Verify compliance with local laws"]
        elif clause_type in ['governing_law', 'jurisdiction']:
            severity_level = 3
            risk_factors = ["Jurisdictional considerations"]
            compliance_flags = ["Review governing law provisions"]
        else:
            risk_factors = ["Unknown clause type - requires manual review"]

        # Enhanced keyword analysis
        high_risk_keywords = [
            'penalty', 'forfeit', 'liable', 'terminate immediately', 'breach',
            'liquidated damages', 'indemnify', 'hold harmless', 'unlimited liability',
            'automatic termination', 'without cause', 'discretionary'
        ]

        medium_risk_keywords = [
            'may', 'shall', 'must', 'required', 'obligated',
            'consent', 'approval', 'discretion'
        ]

        # Check for high-risk keywords
        high_risk_found = [kw for kw in high_risk_keywords if kw in clause_text.lower()]
        if high_risk_found:
            severity_level = max(severity_level, 4)
            risk_factors.append(f"High-risk language detected: {', '.join(high_risk_found[:3])}")

        # Check for medium-risk keywords
        medium_risk_found = [kw for kw in medium_risk_keywords if kw in clause_text.lower()]
        if medium_risk_found and severity_level < 4:
            severity_level = max(severity_level, 3)
            risk_factors.append(f"Review recommended: {', '.join(medium_risk_found[:3])}")

        # Length-based assessment
        if len(clause_text) > 1000:
            risk_factors.append("Long clause - detailed review recommended")
            recommendations.append("Consider simplifying complex clauses")

        error_info = f" (AI Error: {error_message})" if error_message else ""

        if error_message:
            recommendations.insert(0, "AI analysis failed - manual legal review strongly recommended")

        return {
            "severity_level": severity_level,
            "severity_reasoning": f"AI analysis unavailable - automated assessment performed{error_info}",
            "risk_factors": list(set(risk_factors)),  # Remove duplicates
            "legal_implications": f"Unable to provide detailed legal analysis at this time{error_info}. Basic keyword analysis performed.",
            "plain_language_explanation": f"This is a {clause_type} clause. {'High-risk terms detected requiring legal review.' if severity_level >= 4 else 'Standard clause with moderate risk level.'}{error_info}",
            "compliance_flags": compliance_flags,
            "recommendations": list(set(recommendations)),  # Remove duplicates
            "confidence_score": 0.2  # Lower confidence for fallback analysis
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of AI services"""
        health_status = {
            "openai": {"available": False, "error": None, "model": None},
            "gemini": {"available": False, "error": None, "model": None},
            "preferred_client": None,
            "timestamp": None
        }

        try:
            health_status["preferred_client"] = self._get_preferred_client()
        except Exception as e:
            health_status["preferred_client"] = f"Error: {str(e)}"

        # Test OpenAI
        if self.openai_client:
            try:
                # Simple test call
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5,
                    timeout=10.0  # Add timeout
                )
                health_status["openai"]["available"] = True
                health_status["openai"]["model"] = "gpt-3.5-turbo"
                health_status["openai"]["response_time"] = getattr(response, 'usage', {}).get('total_tokens', 'N/A')
            except Exception as e:
                health_status["openai"]["error"] = str(e)
                health_status["openai"]["model"] = "gpt-3.5-turbo"

        # Test Gemini
        if self.gemini_model:
            try:
                # Use a safer test prompt to avoid safety filter blocks
                response = self.gemini_model.generate_content(
                    "Please respond with just the word 'OK' to confirm you can generate responses.",
                    generation_config=genai.types.GenerationConfig(max_output_tokens=10)
                )

                # Check response structure based on API documentation
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]

                    # Check finish reason
                    if hasattr(candidate, 'finishReason'):
                        finish_reason = candidate.finishReason
                        if finish_reason == "STOP":
                            # Check if we have content
                            if hasattr(candidate, 'content') and candidate.content.parts:
                                part = candidate.content.parts[0]
                                if hasattr(part, 'text') and part.text.strip():
                                    health_status["gemini"]["available"] = True
                                    health_status["gemini"]["model"] = "gemini-2.5-pro"
                                else:
                                    health_status["gemini"]["error"] = "Empty response content"
                            else:
                                health_status["gemini"]["error"] = "No content in response"
                        elif finish_reason == "SAFETY":
                            health_status["gemini"]["error"] = "Response blocked by safety filters"
                        else:
                            health_status["gemini"]["error"] = f"Response finished with: {finish_reason}"
                    else:
                        health_status["gemini"]["error"] = "No finish reason in response"
                else:
                    health_status["gemini"]["error"] = "No candidates in response"

                # Fallback check using the text property
                if not health_status["gemini"]["available"]:
                    try:
                        text_content = response.text
                        if text_content and text_content.strip():
                            health_status["gemini"]["available"] = True
                            health_status["gemini"]["model"] = "gemini-2.5-pro"
                            health_status["gemini"]["error"] = None  # Clear any previous error
                    except ValueError as text_error:
                        if "requires the response to contain a valid" in str(text_error):
                            health_status["gemini"]["error"] = "Response blocked by safety filters"
                        else:
                            health_status["gemini"]["error"] = f"Text extraction error: {str(text_error)}"

            except Exception as e:
                health_status["gemini"]["error"] = str(e)
                health_status["gemini"]["model"] = "gemini-2.5-pro"

        # Add diagnostic information
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat()

        # Add system information
        health_status["diagnostics"] = {
            "openai_configured": bool(settings.openai_api_key),
            "gemini_configured": bool(settings.google_api_key),
            "fallback_available": True
        }

        return health_status

    async def generate_document_summary(
        self,
        clauses_analysis: List[Dict[str, Any]],
        document_type: str
    ) -> Dict[str, Any]:
        """Generate overall document summary and recommendations"""
        try:
            # Aggregate clause data
            total_clauses = len(clauses_analysis)
            severity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            all_risk_factors = []
            all_compliance_flags = []

            for clause_data in clauses_analysis:
                analysis = clause_data.get('analysis', {})
                severity = analysis.get('severity_level', 3)
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

                all_risk_factors.extend(analysis.get('risk_factors', []))
                all_compliance_flags.extend(analysis.get('compliance_flags', []))

            # Calculate overall risk score
            weighted_score = sum(level * count for level, count in severity_counts.items())
            overall_risk_score = weighted_score / total_clauses if total_clauses > 0 else 3.0

            # Generate summary
            high_risk_count = severity_counts.get(4, 0) + severity_counts.get(5, 0)
            medium_risk_count = severity_counts.get(3, 0)

            critical_issues = list(set(all_risk_factors))[:5]  # Top 5 unique issues
            compliance_issues = list(set(all_compliance_flags))[:3]  # Top 3 compliance issues

            # Generate recommendations based on analysis
            recommendations = self._generate_recommendations(
                severity_counts, all_risk_factors, document_type
            )

            compliance_score = max(0, 100 - (high_risk_count * 10) - (len(compliance_issues) * 15))

            return {
                "high_risk_clauses": high_risk_count,
                "medium_risk_clauses": medium_risk_count,
                "low_risk_clauses": severity_counts.get(1, 0) + severity_counts.get(2, 0),
                "critical_issues": critical_issues,
                "recommendations": recommendations,
                "compliance_score": compliance_score,
                "overall_sentiment": self._get_overall_sentiment(overall_risk_score)
            }

        except Exception as e:
            logger.error(f"Failed to generate document summary: {e}")
            return self._get_fallback_summary()

    def _generate_recommendations(
        self,
        severity_counts: Dict[int, int],
        risk_factors: List[str],
        document_type: str
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        if severity_counts.get(5, 0) > 0:
            recommendations.append("URGENT: Review critical clauses with legal counsel immediately")

        if severity_counts.get(4, 0) > 2:
            recommendations.append("Multiple high-risk clauses identified - comprehensive legal review recommended")

        # Document-specific recommendations
        if document_type == "rental_agreement":
            if "termination" in " ".join(risk_factors).lower():
                recommendations.append("Consider adding 30-day notice period for termination")
            if "deposit" in " ".join(risk_factors).lower():
                recommendations.append("Ensure security deposit terms comply with local rent control laws")

        if "compliance" in " ".join(risk_factors).lower():
            recommendations.append("Address compliance issues to avoid legal challenges")

        if not recommendations:
            recommendations.append("Document appears standard - regular legal review recommended")

        return recommendations[:5]  # Limit to top 5

    def _get_overall_sentiment(self, risk_score: float) -> str:
        """Convert risk score to sentiment"""
        if risk_score >= 4.5:
            return "critical_risk"
        elif risk_score >= 3.5:
            return "high_risk"
        elif risk_score >= 2.5:
            return "moderate_risk"
        elif risk_score >= 1.5:
            return "low_risk"
        else:
            return "minimal_risk"

    def _get_fallback_summary(self) -> Dict[str, Any]:
        """Fallback document summary"""
        return {
            "high_risk_clauses": 0,
            "medium_risk_clauses": 0,
            "low_risk_clauses": 0,
            "critical_issues": ["AI analysis unavailable"],
            "recommendations": ["Consult legal professional for comprehensive review"],
            "compliance_score": 50.0,
            "overall_sentiment": "unknown_risk"
        }

# Global AI service instance
ai_service = AIService()
