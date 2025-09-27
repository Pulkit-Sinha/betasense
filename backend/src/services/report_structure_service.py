from typing import Dict, List, Any
from dataclasses import dataclass
from .llm_service import LLMService

@dataclass
class ReportSection:
    title: str
    description: str
    estimated_pages: float
    key_topics: List[str]

@dataclass
class ReportStructure:
    title: str
    sections: List[ReportSection]
    total_estimated_pages: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "sections": [
                {
                    "title": section.title,
                    "description": section.description,
                    "estimated_pages": section.estimated_pages,
                    "key_topics": section.key_topics
                }
                for section in self.sections
            ],
            "total_estimated_pages": self.total_estimated_pages
        }

class ReportStructureService:
    def __init__(self):
        self.llm_service = LLMService()
    
    def generate_report_structure(self, topic: str, domain_context: str = "financial analysis") -> ReportStructure:
        system_prompt = f"""You are an expert report structuring assistant specializing in {domain_context}. 
        Your task is to create a comprehensive, logical report structure tailored to the specific topic and analysis type.
        
        Analyze the topic and determine:
        - What type of analysis this requires (valuation, growth, risk, comparison, etc.)
        - How many sections would best serve this analysis (3-6 sections typically)
        - What section names and order would be most logical
        - What content should be covered in each section
        
        For each section, provide:
        - Clear, descriptive title that fits the analysis type
        - Detailed description of what will be covered
        - Estimated page length (concise sections: 0.3-1.0 pages per section for faster generation)
        - 3-5 key topics/subtopics to be addressed
        
        Create a structure that flows logically from background/overview to detailed analysis to conclusions.
        Adapt section names and focus to match the specific question being asked.
        
        Respond with ONLY valid JSON in the specified format."""
        
        user_prompt = f"""Create a comprehensive report structure for the topic: "{topic}"
        
        Analyze this topic and design the most appropriate report structure:
        - Consider what type of analysis this question requires
        - Determine the optimal number of sections (3-6 sections)
        - Create section titles that directly address the topic
        - Structure should flow logically to answer the core question
        - Each section should build toward actionable insights
        
        Examples of different analysis types:
        - Valuation questions → Company Overview, Financial Analysis, Valuation Methods, Investment Recommendation
        - Growth questions → Market Analysis, Growth Drivers, Competitive Position, Future Outlook  
        - Comparison questions → Company Profiles, Comparative Analysis, Strengths/Weaknesses, Recommendation
        - Risk questions → Risk Assessment, Impact Analysis, Mitigation Strategies, Recommendations
        
        Return ONLY valid JSON in this format (no other text):
        {{
            "title": "Your Report Title Here",
            "sections": [
                {{
                    "title": "Section Title",
                    "description": "Detailed description of what this section will analyze and cover",
                    "estimated_pages": 0.8,
                    "key_topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4"]
                }}
            ]
        }}"""
        
        response = self.llm_service.execute_prompt(system_prompt, user_prompt, extract_json_output=True)
        
        try:
            if response is None:
                raise ValueError("LLM returned None response")
            
            # If response is already parsed as JSON (from extract_json_output=True)
            if isinstance(response, dict):
                structure_data = response
            else:
                import json
                structure_data = json.loads(response)
            
            sections = []
            total_pages = 0
            
            for section_data in structure_data.get("sections", []):
                section = ReportSection(
                    title=section_data.get("title", ""),
                    description=section_data.get("description", ""),
                    estimated_pages=section_data.get("estimated_pages", 1.0),
                    key_topics=section_data.get("key_topics", [])
                )
                sections.append(section)
                total_pages += section.estimated_pages
            
            return ReportStructure(
                title=structure_data.get("title", topic),
                sections=sections,
                total_estimated_pages=total_pages
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing report structure: {e}")
            fallback_sections = [
                ReportSection(
                    title="Key Takeaways",
                    description="Summary of main findings and conclusions",
                    estimated_pages=0.4,
                    key_topics=["Main findings", "Key insights", "Critical points"]
                ),
                ReportSection(
                    title="Executive Summary", 
                    description="Comprehensive overview and final assessment",
                    estimated_pages=0.8,
                    key_topics=["Background", "Analysis summary", "Conclusion"]
                ),
                ReportSection(
                    title="Detailed Analysis",
                    description="In-depth examination of the topic",
                    estimated_pages=0.8,
                    key_topics=["Data analysis", "Trends", "Implications"]
                )
            ]
            
            return ReportStructure(
                title=f"Analysis Report: {topic}",
                sections=fallback_sections,
                total_estimated_pages=2.0
            )