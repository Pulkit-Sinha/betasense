from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import asyncio

from .llm_service import LLMService
from .hybrid_search_service import HybridSearchService
from .websearch_service import WebSearchService
from .report_structure_service import ReportStructureService, ReportStructure
from .research_plan_service import ResearchPlanService, ResearchPlan

@dataclass
class ReportContent:
    structure: ReportStructure
    research_plan: ResearchPlan
    sections: Dict[str, str]  # section_title -> content
    sources_used: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure": self.structure.to_dict(),
            "research_plan": {
                "topic": self.research_plan.topic,
                "search_strategy": self.research_plan.search_strategy,
                "query_count": len(self.research_plan.get_all_search_queries())
            },
            "sections": self.sections,
            "sources_used": self.sources_used,
            "web_results": self.web_results,
            "metadata": {
                "total_sections": len(self.sections),
                "estimated_pages": self.structure.total_estimated_pages,
                "sources_count": len(self.sources_used),
                "web_sources_count": len(self.web_results)
            }
        }

class ComprehensiveReportService:
    def __init__(self):
        self.llm_service = LLMService()
        self.hybrid_search_service = HybridSearchService()
        self.websearch_service = WebSearchService()
        self.structure_service = ReportStructureService()
        self.research_service = ResearchPlanService()
    
    async def generate_comprehensive_report(
        self, 
        topic: str, 
        sources: Dict[str, Any],
        enable_web_search: bool = False,
        domain_context: str = "financial analysis"
    ) -> ReportContent:
        """Generate a comprehensive structured report"""
        
        # Step 1: Generate report structure
        print(f"Generating report structure for: {topic}")
        report_structure = self.structure_service.generate_report_structure(topic, domain_context)
        
        # Step 2: Create research plan based on structure
        print("Creating detailed research plan...")
        research_plan = self.research_service.generate_research_plan(report_structure)
        print(f"Research plan created with {len(research_plan.research_queries)} queries")
        
        # Step 3: Execute searches based on research plan
        print("Executing searches based on research plan...")
        all_search_results = await self._execute_research_searches(
            research_plan, sources, enable_web_search
        )
        
        # Step 4: Generate content for each section
        print("Generating content for each section...")
        section_contents = await self._generate_section_contents(
            report_structure, research_plan, all_search_results
        )
        
        return ReportContent(
            structure=report_structure,
            research_plan=research_plan,
            sections=section_contents,
            sources_used=all_search_results.get("local_sources", []),
            web_results=all_search_results.get("web_results", [])
        )
    
    async def _execute_research_searches(
        self, 
        research_plan: ResearchPlan, 
        sources: Dict[str, Any],
        enable_web_search: bool
    ) -> Dict[str, Any]:
        """Execute all searches based on research plan"""
        
        # Convert sources to filters
        filters = self._map_source_selection_to_filters(sources)
        
        all_local_results = []
        all_web_results = []
        
        # Get optimized queries for different search types
        keyword_queries = research_plan.get_high_priority_queries()[:5]  # Top 5 high-priority
        vector_queries = research_plan.get_all_search_queries()[:8]      # Top 8 overall
        
        print(f"Research plan has {len(research_plan.research_queries)} research queries")
        print(f"High priority queries: {keyword_queries}")
        print(f"All queries: {vector_queries}")
        print(f"Executing {len(keyword_queries)} keyword searches and {len(vector_queries)} vector searches")
        
        # Execute local document searches
        unique_queries = set(keyword_queries + vector_queries)
        print(f"Unique queries to search: {len(unique_queries)}")
        
        for i, query in enumerate(unique_queries):
            print(f"Searching {i+1}/{len(unique_queries)}: {query}")
            try:
                local_results = self.hybrid_search_service.search_documents_expanded(
                    query=query,
                    categories=filters['categories'] if filters['categories'] else None,
                    subcategories=filters['subcategories'] if filters['subcategories'] else None,
                    keyword_count=5,  # Fewer per query but more queries
                    vector_count=5
                )
                print(f"Found {len(local_results) if local_results else 0} results for query: {query[:50]}...")
                if local_results:
                    all_local_results.extend(local_results)
            except Exception as e:
                print(f"Error searching for query '{query}': {e}")
                continue
        
        print(f"Total local results collected: {len(all_local_results)}")
        
        # If no local results found, add fallback search with broader terms
        if not all_local_results:
            print("No local results found, trying fallback searches...")
            # Clean the topic for search - remove special characters and truncate
            clean_topic = research_plan.topic.replace(":", "").replace("-", " ").replace(",", "")
            topic_words = clean_topic.split()[:4]  # Take first 4 words
            
            fallback_queries = [
                " ".join(topic_words),
                "JioFin financial analysis",
                "financial services analysis"
            ]
            for query in fallback_queries:
                try:
                    fallback_results = self.hybrid_search_service.search_documents_expanded(
                        query=query,
                        categories=None,
                        subcategories=None,
                        keyword_count=10,
                        vector_count=10
                    )
                    if fallback_results:
                        print(f"Fallback search found {len(fallback_results)} results for: {query}")
                        all_local_results.extend(fallback_results)
                        break
                except Exception as e:
                    print(f"Fallback search error for '{query}': {e}")
                    continue
        
        # Execute web searches if enabled
        print(f"Web search enabled: {enable_web_search}")
        if enable_web_search:
            web_queries = research_plan.get_high_priority_queries()[:3]  # Top 3 for web
            print(f"Starting web search with {len(web_queries)} queries: {web_queries}")
            for query in web_queries:
                print(f"Web searching for: {query}")
                try:
                    # Add timeout for web search to prevent hanging
                    web_results = await asyncio.wait_for(
                        self.websearch_service.search_and_scrape_web(query),
                        timeout=30.0  # 30 second timeout per query
                    )
                    print(f"Web search returned {len(web_results) if web_results else 0} results for query: {query[:50]}...")
                    if web_results:
                        all_web_results.extend(web_results)
                except Exception as e:
                    print(f"Error web searching for query '{query}': {e}")
                    continue
        
        # Deduplicate and rank results
        deduplicated_local = self._deduplicate_results(all_local_results)
        deduplicated_web = self._deduplicate_web_results(all_web_results)
        
        print(f"Final search results - Local: {len(deduplicated_local)}, Web: {len(deduplicated_web)}")
        
        return {
            "local_sources": deduplicated_local[:20],  # Top 20 local results
            "web_results": deduplicated_web[:10]        # Top 10 web results
        }
    
    async def _generate_section_contents(
        self, 
        structure: ReportStructure, 
        research_plan: ResearchPlan,
        search_results: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate content for each section of the report"""
        
        section_contents = {}
        local_sources = search_results.get("local_sources", [])
        web_sources = search_results.get("web_results", [])
        
        # Create comprehensive context from all sources
        local_context = self._create_context_from_sources(local_sources)
        web_context = self._create_context_from_web_sources(web_sources)
        
        for i, section in enumerate(structure.sections):
            print(f"Generating content for section {i+1}/{len(structure.sections)}: {section.title}")
            
            # Find relevant research queries for this section
            relevant_queries = [
                rq for rq in research_plan.research_queries 
                if rq.section_title == section.title
            ]
            print(f"Found {len(relevant_queries)} relevant queries for this section")
            
            section_context = self._filter_context_for_section(
                local_context, web_context, section, relevant_queries
            )
            print(f"Context length for section: {len(section_context)} characters")
            
            print(f"Calling LLM for section: {section.title}")
            content = await self._generate_single_section_content(
                section, section_context, structure.title
            )
            print(f"LLM returned {len(content)} characters for section: {section.title}")
            
            section_contents[section.title] = content
        
        return section_contents
    
    async def _generate_single_section_content(
        self, 
        section, 
        context: str, 
        report_title: str
    ) -> str:
        """Generate content for a single section"""
        
        system_prompt = f"""You are an expert analyst writing a concise section of a comprehensive report titled "{report_title}".

        Write the "{section.title}" section following these guidelines:
        - Use the provided research context to support your analysis
        - Write in a professional, analytical tone
        - Include specific data, figures, and citations where available
        - Be concise and focused - aim for approximately {section.estimated_pages} pages of content (about 200-400 words per section)
        - Always cite sources with [Source: filename] format for documents and [Web: URL] format for web sources
        - Focus specifically on: {', '.join(section.key_topics)}
        - Provide actionable insights rather than lengthy explanations
        
        Section Description: {section.description}"""
        
        user_prompt = f"""Write a concise "{section.title}" section using the following research context:

{context}

The section should directly address these key topics:
{chr(10).join([f"- {topic}" for topic in section.key_topics])}

Provide a focused, well-structured analysis (200-400 words) that synthesizes the key information and delivers actionable insights."""
        
        try:
            content = self.llm_service.execute_prompt(system_prompt, user_prompt)
            return content or f"# {section.title}\n\nContent could not be generated for this section."
        except Exception as e:
            print(f"Error generating content for section {section.title}: {e}")
            return f"# {section.title}\n\nError generating content for this section."
    
    def _create_context_from_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Create formatted context string from local sources"""
        if not sources:
            return ""
        
        context_parts = []
        for source in sources:
            context_parts.append(
                f"Source: {source.get('source_file', 'Unknown')} "
                f"(Score: {source.get('combined_score', 0):.3f})\n"
                f"{source.get('text', '')}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _create_context_from_web_sources(self, web_sources: List[Dict[str, Any]]) -> str:
        """Create formatted context string from web sources"""
        if not web_sources:
            return ""
        
        context_parts = []
        for source in web_sources:
            context_parts.append(
                f"Web Source: {source.get('url', 'Unknown')}\n"
                f"Title: {source.get('title', 'No title')}\n"
                f"{source.get('content', '')}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _filter_context_for_section(
        self, 
        local_context: str, 
        web_context: str, 
        section, 
        relevant_queries: List
    ) -> str:
        """Filter and combine context relevant to a specific section"""
        # For now, return all context - could be enhanced with semantic filtering
        combined_context = ""
        
        if local_context:
            combined_context += "## Document Sources:\n" + local_context
        
        if web_context:
            combined_context += "\n\n## Web Sources:\n" + web_context
        
        return combined_context
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on content similarity"""
        if not results:
            return results
        
        seen_chunks = set()
        deduplicated = []
        
        for result in results:
            chunk_id = result.get('chunk_id')
            if chunk_id and chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                deduplicated.append(result)
        
        # Sort by combined score
        return sorted(deduplicated, key=lambda x: x.get('combined_score', 0), reverse=True)
    
    def _deduplicate_web_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate web results based on URL"""
        if not results:
            return results
        
        seen_urls = set()
        deduplicated = []
        
        for result in results:
            url = result.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(result)
        
        return deduplicated
    
    def _map_source_selection_to_filters(self, sources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Convert frontend source selection to search filters"""
        categories = []
        subcategories = []
        
        for category, config in sources.items():
            if config.get('enabled', False):
                if category == 'brokerResearch':
                    categories.append('broker_research')
                    for sub, enabled in config.get('subcategories', {}).items():
                        if enabled:
                            subcategories.append(sub)
                elif category == 'companyDocs':
                    categories.append('company_docs')
                    for sub, enabled in config.get('subcategories', {}).items():
                        if enabled:
                            subcategories.append(sub)
        
        return {'categories': categories, 'subcategories': subcategories}