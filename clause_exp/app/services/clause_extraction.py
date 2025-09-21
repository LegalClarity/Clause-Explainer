import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from ..models import ClauseCreate, PositionInDocument, AnalysisMetadata
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ClauseExtractionError(Exception):
    """Custom exception for clause extraction errors"""
    pass

class ClauseExtractor:
    """Service for extracting and segmenting clauses from legal documents"""

    # Common clause numbering patterns in legal documents
    CLAUSE_PATTERNS = [
        # Arabic numerals: 1., 1.1, 1.1.1
        r'^\s*(\d+(?:\.\d+)*)\.?\s+(.+)',
        # Roman numerals: I., II., III.
        r'^\s*(I{1,3}|IV|V|VI{1,3}|IX|X)\.?\s+(.+)',
        # Letter numbering: (a), (b), A., B.
        r'^\s*([a-zA-Z])\.?\s*\)?\s*(.+)',
        # Parenthetical numbers: (1), (2)
        r'^\s*\((\d+)\)\s+(.+)',
        # Section headers: Section 1, Article 1
        r'^\s*(?:Section|Article|Clause)\s+(\d+)[.:]?\s+(.+)',
        # Bullet points with numbers
        r'^\s*[•\-\*]\s*(\d+)\.?\s+(.+)',
    ]

    # Keywords that indicate clause boundaries
    CLAUSE_KEYWORDS = [
        'agreement', 'party', 'parties', 'term', 'condition', 'obligation',
        'right', 'rights', 'liability', 'termination', 'breach', 'default',
        'payment', 'fee', 'compensation', 'damages', 'warranty', 'representation',
        'confidentiality', 'intellectual property', 'force majeure', 'governing law',
        'jurisdiction', 'arbitration', 'dispute', 'notice', 'amendment', 'assignment',
        'severability', 'entire agreement', 'waiver', 'indemnification', 'insurance',
        'maintenance', 'repair', 'security deposit', 'rent', 'lease', 'tenant',
        'landlord', 'property', 'premises'
    ]

    # Clause type mapping based on keywords
    CLAUSE_TYPE_MAPPING = {
        'payment': ['payment', 'fee', 'compensation', 'rent', 'deposit', 'money'],
        'termination': ['termination', 'end', 'cancel', 'expire', 'breach', 'default'],
        'liability': ['liability', 'responsible', 'obligation', 'duty', 'indemnify'],
        'confidentiality': ['confidential', 'secret', 'private', 'disclose', 'protect'],
        'governing_law': ['governing law', 'jurisdiction', 'court', 'arbitration'],
        'force_majeure': ['force majeure', 'act of god', 'unforeseeable', 'emergency'],
        'intellectual_property': ['intellectual property', 'copyright', 'trademark', 'patent'],
        'maintenance': ['maintenance', 'repair', 'condition', 'fix', 'restore'],
        'security_deposit': ['security deposit', 'deposit', 'refund', 'return'],
        'notice': ['notice', 'notify', 'communication', 'contact', 'address'],
        'assignment': ['assignment', 'transfer', 'sublet', 'delegate'],
        'amendment': ['amendment', 'modify', 'change', 'alter', 'revise'],
        'severability': ['severability', 'separate', 'independent', 'invalid'],
        'waiver': ['waiver', 'forgo', 'relinquish', 'abandon'],
        'insurance': ['insurance', 'insure', 'coverage', 'policy']
    }

    @staticmethod
    def extract_clauses(text: str, document_id: str) -> List[ClauseCreate]:
        """Extract individual clauses from document text"""
        try:
            # Split text into paragraphs/lines
            paragraphs = ClauseExtractor._split_into_paragraphs(text)

            # Identify clause boundaries
            clauses_data = ClauseExtractor._identify_clauses(paragraphs, document_id)

            # Convert to ClauseCreate objects
            clauses = []
            for i, clause_data in enumerate(clauses_data, 1):
                clause = ClauseCreate(
                    clause_id=f"clause_{document_id}_{i:03d}",
                    document_id=document_id,
                    sequence_number=i,
                    clause_text=clause_data['text'],
                    clause_title=clause_data['title'],
                    clause_type=clause_data['type'],
                    severity_level=3,  # Default, will be analyzed later
                    severity_color="#EAB308",  # Default yellow
                    risk_factors=[],  # Will be analyzed later
                    legal_implications="",  # Will be analyzed later
                    plain_language_explanation="",  # Will be analyzed later
                    related_clauses=[],  # Will be determined later
                    compliance_flags=[],  # Will be analyzed later
                    position_in_document=PositionInDocument(
                        start_char=clause_data['start_char'],
                        end_char=clause_data['end_char'],
                        page_number=clause_data.get('page_number')
                    ),
                    analysis_metadata=AnalysisMetadata(
                        analyzed_at=datetime.utcnow(),
                        confidence_score=0.5,  # Initial confidence
                        ai_model_used="clause_extractor_v1"
                    )
                )
                clauses.append(clause)

            logger.info(f"Extracted {len(clauses)} clauses from document {document_id}")
            return clauses

        except Exception as e:
            logger.error(f"Failed to extract clauses from document {document_id}: {e}")
            raise ClauseExtractionError(f"Clause extraction failed: {str(e)}")

    @staticmethod
    def _split_into_paragraphs(text: str) -> List[Dict[str, Any]]:
        """Split text into paragraphs with position tracking"""
        paragraphs = []
        current_pos = 0

        # Split by double newlines (paragraph breaks)
        raw_paragraphs = re.split(r'\n\s*\n', text)

        for para in raw_paragraphs:
            para = para.strip()
            if para:
                start_pos = text.find(para, current_pos)
                if start_pos == -1:  # Fallback if exact match not found
                    start_pos = current_pos

                paragraphs.append({
                    'text': para,
                    'start_char': start_pos,
                    'end_char': start_pos + len(para),
                    'length': len(para)
                })

                current_pos = start_pos + len(para)

        return paragraphs

    @staticmethod
    def _identify_clauses(paragraphs: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """Identify clause boundaries and extract clause information"""
        clauses = []
        current_clause_text = ""
        current_clause_start = 0
        current_title = ""

        for i, para in enumerate(paragraphs):
            para_text = para['text']

            # Check if this paragraph starts a new clause
            is_clause_start = ClauseExtractor._is_clause_start(para_text)

            if is_clause_start or i == 0:
                # Save previous clause if it exists
                if current_clause_text.strip():
                    clause_data = ClauseExtractor._create_clause_data(
                        current_clause_text.strip(),
                        current_title,
                        current_clause_start,
                        paragraphs[i-1]['end_char'] if i > 0 else para['end_char']
                    )
                    if clause_data:
                        clauses.append(clause_data)

                # Start new clause
                current_clause_text = para_text
                current_clause_start = para['start_char']
                current_title = ClauseExtractor._extract_clause_title(para_text)

            else:
                # Continue current clause
                current_clause_text += "\n\n" + para_text

        # Add the last clause
        if current_clause_text.strip():
            last_end = paragraphs[-1]['end_char'] if paragraphs else len(current_clause_text)
            clause_data = ClauseExtractor._create_clause_data(
                current_clause_text.strip(),
                current_title,
                current_clause_start,
                last_end
            )
            if clause_data:
                clauses.append(clause_data)

        # Post-process clauses to ensure reasonable sizes
        clauses = ClauseExtractor._post_process_clauses(clauses)

        return clauses

    @staticmethod
    def _is_clause_start(text: str) -> bool:
        """Determine if text starts a new clause"""
        text = text.strip()

        # Check numbered patterns
        for pattern in ClauseExtractor.CLAUSE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        # Check for clause keywords at the beginning
        first_50_chars = text[:50].lower()

        for keyword in ClauseExtractor.CLAUSE_KEYWORDS:
            if first_50_chars.startswith(keyword) or f" {keyword}" in first_50_chars:
                # Make sure it's not just a reference within text
                words = text.split()[:3]  # First 3 words
                if any(keyword in word.lower() for word in words):
                    return True

        # Check for common legal section headers
        header_patterns = [
            r'^\s*(?:WHEREAS|NOW THEREFORE|IN WITNESS WHEREOF)',
            r'^\s*(?:This|The)\s+(?:Agreement|Contract|Lease)',
            r'^\s*Definitions?\s*:',
            r'^\s*Schedule\s+\d+:',
            r'^\s*Exhibit\s+\w+:',
        ]

        for pattern in header_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def _extract_clause_title(text: str) -> str:
        """Extract a title for the clause"""
        text = text.strip()

        # Try to find numbered title
        for pattern in ClauseExtractor.CLAUSE_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                title_part = match.group(2).strip()
                # Limit title length
                if len(title_part) <= 100:
                    return title_part

        # Extract first meaningful sentence
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences[:2]:  # Check first 2 sentences
            sentence = sentence.strip()
            if 10 <= len(sentence) <= 100:
                return sentence

        # Fallback: first 50 characters
        return text[:50].strip()

    @staticmethod
    def _create_clause_data(text: str, title: str, start_char: int, end_char: int) -> Optional[Dict[str, Any]]:
        """Create clause data dictionary"""
        if not text.strip() or len(text.strip()) < 20:  # Minimum clause length
            return None

        clause_type = ClauseExtractor._determine_clause_type(text)

        return {
            'text': text,
            'title': title or f"Clause {uuid.uuid4().hex[:8]}",
            'type': clause_type,
            'start_char': start_char,
            'end_char': end_char
        }

    @staticmethod
    def _determine_clause_type(text: str) -> str:
        """Determine clause type based on content analysis"""
        text_lower = text.lower()

        # Check each type's keywords
        for clause_type, keywords in ClauseExtractor.CLAUSE_TYPE_MAPPING.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return clause_type

        # Default classification based on content patterns
        if any(word in text_lower for word in ['rent', 'lease', 'tenant', 'landlord']):
            return 'property_details'
        elif any(word in text_lower for word in ['party', 'parties', 'agreement']):
            return 'party_details'
        else:
            return 'general'

    @staticmethod
    def _post_process_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process extracted clauses for quality"""
        processed_clauses = []

        for clause in clauses:
            # Skip very short clauses (likely headers or artifacts)
            if len(clause['text']) < 50:
                continue

            # Merge very short clauses with previous if they seem related
            if (processed_clauses and
                len(clause['text']) < 200 and
                processed_clauses[-1]['type'] == clause['type']):

                # Merge with previous clause
                processed_clauses[-1]['text'] += "\n\n" + clause['text']
                processed_clauses[-1]['end_char'] = clause['end_char']
            else:
                processed_clauses.append(clause)

        # Ensure we have reasonable number of clauses (not too many tiny ones)
        if len(processed_clauses) > 50:
            # Merge smaller clauses
            merged_clauses = []
            current_clause = None

            for clause in processed_clauses:
                if current_clause is None:
                    current_clause = clause.copy()
                elif len(current_clause['text']) < 500:
                    current_clause['text'] += "\n\n" + clause['text']
                    current_clause['end_char'] = clause['end_char']
                else:
                    merged_clauses.append(current_clause)
                    current_clause = clause.copy()

            if current_clause:
                merged_clauses.append(current_clause)

            processed_clauses = merged_clauses

        return processed_clauses

    @staticmethod
    def get_clause_summary(clauses: List[ClauseCreate]) -> Dict[str, Any]:
        """Generate summary statistics for extracted clauses"""
        if not clauses:
            return {}

        types_count = {}
        total_length = 0

        for clause in clauses:
            clause_type = clause.clause_type
            types_count[clause_type] = types_count.get(clause_type, 0) + 1
            total_length += len(clause.clause_text)

        return {
            'total_clauses': len(clauses),
            'clause_types': types_count,
            'average_clause_length': total_length // len(clauses) if clauses else 0,
            'total_text_length': total_length
        }

# Global extractor instance
clause_extractor = ClauseExtractor()
