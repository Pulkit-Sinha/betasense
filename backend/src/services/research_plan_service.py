from typing import Dict, List, Any
from dataclasses import dataclass
import re
from .llm_service import LLMService
from .report_structure_service import ReportStructure, ReportSection

@dataclass
class ResearchQuery:
    section_title: str
    search_queries: List[str]
    key_concepts: List[str]
    search_priority: int  # 1-5, where 5 is highest priority

@dataclass
class ResearchPlan:
    topic: str
    research_queries: List[ResearchQuery]
    search_strategy: str
    
    def get_all_search_queries(self) -> List[str]:
        """Get all search queries flattened from all sections"""
        queries = []
        for research_query in self.research_queries:
            queries.extend(research_query.search_queries)
        return queries
    
    def get_high_priority_queries(self, min_priority: int = 4) -> List[str]:
        """Get high priority search queries only"""
        queries = []
        for research_query in self.research_queries:
            if research_query.search_priority >= min_priority:
                queries.extend(research_query.search_queries)
        return queries

class ResearchPlanService:
    def __init__(self):
        self.llm_service = LLMService()
    
    def generate_research_plan(self, report_structure: ReportStructure) -> ResearchPlan:
        """Generate detailed research plan based on report structure"""
        
        system_prompt = """You are an expert research planner. Your task is to create specific, actionable search queries 
        for each section of a report structure. Focus on creating queries that will find the most relevant and comprehensive 
        information for each section.
        
        For each section, generate:
        - 3-5 specific search queries that target the key information needed
        - Key concepts/keywords that should be prioritized in search results
        - Search priority (1-5, where 5 is most critical for the report)
        
        Make queries specific and varied - include different phrasings, synonyms, and approaches.
        Consider both keyword-based and semantic search needs."""
        
        sections_text = "\n".join([
            f"Section: {section.title}\nDescription: {section.description}\nKey Topics: {', '.join(section.key_topics)}"
            for section in report_structure.sections
        ])
        
        user_prompt = f"""Create a detailed research plan for this report:
        
        Topic: {report_structure.title}
        
        Report Sections:
        {sections_text}
        
        For each section, generate specific search queries that will find the most relevant information.
        Analyze each section's focus and create targeted queries that match the analysis type:
        
        Query Guidelines:
        1. Extract key entities/companies from the topic
        2. Match search terms to the section's analytical focus
        3. Include both specific metrics and broader analysis terms
        4. Consider synonyms and alternate phrasings
        5. Prioritize sections that are most critical to answering the main question
        
        Search Priority Levels:
        - 5: Critical for answering the main question
        - 4: Important supporting analysis  
        - 3: Background/context information
        
        Return ONLY valid JSON in this format (no other text):
        {{
            "search_strategy": "Describe your overall research approach for this topic",
            "research_queries": [
                {{
                    "section_title": "Exact section title from above",
                    "search_queries": ["specific query 1", "specific query 2", "specific query 3"],
                    "key_concepts": ["concept1", "concept2", "concept3"],
                    "search_priority": 4
                }}
            ]
        }}"""
        
        response = self.llm_service.execute_prompt(system_prompt, user_prompt, extract_json_output=True)
        
        try:
            if response is None:
                raise ValueError("LLM returned None response")
            
            # If response is already parsed as JSON (from extract_json_output=True)
            if isinstance(response, dict):
                plan_data = response
            else:
                import json
                plan_data = json.loads(response)
            
            print(f"Research plan data: {plan_data}")
            print(f"Research queries count: {len(plan_data.get('research_queries', []))}")
            
            research_queries = []
            for query_data in plan_data.get("research_queries", []):
                research_query = ResearchQuery(
                    section_title=query_data.get("section_title", ""),
                    search_queries=query_data.get("search_queries", []),
                    key_concepts=query_data.get("key_concepts", []),
                    search_priority=query_data.get("search_priority", 3)
                )
                research_queries.append(research_query)
            
            return ResearchPlan(
                topic=report_structure.title,
                research_queries=research_queries,
                search_strategy=plan_data.get("search_strategy", "Comprehensive multi-angle research approach")
            )
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error parsing research plan: {e}")
            print(f"Raw LLM response: {response}")
            # Fallback: Generate basic queries from report structure
            return self._generate_fallback_plan(report_structure)
    
    def _generate_fallback_plan(self, report_structure: ReportStructure) -> ResearchPlan:
        """Generate a basic research plan if LLM parsing fails"""
        research_queries = []
        
        # Extract the main topic and clean it
        clean_title = report_structure.title.replace(":", "").replace("-", " ")
        
        # Generate specific queries for JioFin/financial analysis
        base_queries = [
            "JioFin business model revenue streams",
            "Jio Financial Services financial performance",
            "JioFin stock analysis investment",
            "Reliance Jio Financial Services management",
            "JioFin competitive advantages market position"
        ]
        
        for i, section in enumerate(report_structure.sections):
            # Generate section-specific queries
            if i < len(base_queries):
                queries = [base_queries[i]]
            else:
                queries = [f"JioFin {section.title.lower().replace('analysis', '').replace('assessment', '').strip()}"]
            
            # Clean up queries to remove problematic characters for Solr
            clean_queries = []
            for query in queries:
                # Remove special characters and normalize
                clean_query = re.sub(r'[^\w\s]', ' ', query)
                clean_query = ' '.join(clean_query.split())  # Remove extra spaces
                clean_queries.append(clean_query)
            
            research_query = ResearchQuery(
                section_title=section.title,
                search_queries=clean_queries,
                key_concepts=section.key_topics,
                search_priority=4  # Higher priority for fallback
            )
            research_queries.append(research_query)
        
        return ResearchPlan(
            topic=clean_title,
            research_queries=research_queries,
            search_strategy="Focused keyword-based search with topic extraction"
        )
    
    def optimize_queries_for_search(self, research_plan: ResearchPlan, search_type: str = "hybrid") -> List[str]:
        """Optimize research queries for specific search engine types"""
        if search_type == "keyword":
            # For keyword search, use shorter, more focused queries
            optimized = []
            for rq in research_plan.research_queries:
                for query in rq.search_queries:
                    # Extract key terms and concepts
                    optimized.append(query)
                    # Add concept-based variations
                    for concept in rq.key_concepts[:2]:  # Top 2 concepts
                        optimized.append(f"{concept} {research_plan.topic}")
            return optimized
            
        elif search_type == "vector":
            # For vector search, use more natural language queries
            optimized = []
            for rq in research_plan.research_queries:
                for query in rq.search_queries:
                    # Create natural language versions
                    optimized.append(f"What is the analysis of {query}?")
                    optimized.append(f"How does {query} impact the overall assessment?")
            return optimized
            
        else:  # hybrid
            return research_plan.get_all_search_queries()