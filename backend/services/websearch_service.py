import asyncio
import aiohttp
from typing import List, Dict, Any
from .llm_service import LLMService
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import LLMModel


class WebSearchService:
    def __init__(self):
        self.llm_service = LLMService()

    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search using DuckDuckGo and return results
        """
        try:
            # Use DuckDuckGo for web search
            async with aiohttp.ClientSession() as session:
                search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
                async with session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        # Extract search results
                        for item in data.get('RelatedTopics', [])[:max_results]:
                            if 'Text' in item and 'FirstURL' in item:
                                results.append({
                                    'title': item.get('Text', '').split(' - ')[0] if ' - ' in item.get('Text', '') else item.get('Text', ''),
                                    'url': item.get('FirstURL', ''),
                                    'snippet': item.get('Text', '')
                                })
                        
                        return results
                    else:
                        print(f"Search API error: {response.status}")
                        return []
        except Exception as e:
            print(f"Web search error: {e}")
            return []

    async def enhance_query_with_web_context(self, original_query: str, web_results: List[Dict[str, Any]]) -> str:
        """
        Use Claude to enhance the original query with web search context
        """
        if not web_results:
            return original_query

        # Prepare web context
        web_context = "\n".join([
            f"- {result['title']}: {result['snippet']}"
            for result in web_results
        ])

        system_prompt = """You are an AI assistant helping to answer financial questions. You have access to both local financial documents and web search results. Your task is to provide a comprehensive answer that combines information from both sources when relevant.

Always prioritize accuracy and cite your sources appropriately."""

        user_prompt = f"""Original question: {original_query}

Web search results:
{web_context}

Please provide a comprehensive answer that incorporates relevant information from both the web search results and any local financial documents that may be available. If the web results provide important context or recent updates, include them in your response."""

        try:
            enhanced_response = self.llm_service.execute_prompt(system_prompt, user_prompt)
            return enhanced_response or original_query
        except Exception as e:
            print(f"Error enhancing query with web context: {e}")
            return original_query