import asyncio
import aiohttp
from typing import List, Dict, Any
from .llm_service import LLMService
import sys
import os
from playwright.async_api import async_playwright
from ..constants import LLMModel


class WebSearchService:
    def __init__(self):
        self.llm_service = LLMService()

    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search using DuckDuckGo and return results
        """
        try:
            # Use DuckDuckGo for web search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            async with aiohttp.ClientSession() as session:
                search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
                async with session.get(search_url, headers=headers) as response:
                    if response.status in [200, 202]:
                        try:
                            # Try JSON first
                            data = await response.json()
                        except Exception as parse_error:
                            # If JSON fails, try parsing as text
                            text_response = await response.text()
                            print(f"DuckDuckGo API JSON parse error: {parse_error}")
                            if 'DDG.ready' in text_response:
                                # This is the JavaScript callback, return fallback results
                                print("DuckDuckGo returned JavaScript callback, using fallback results")
                                return self._get_fallback_search_results(query)
                            return self._get_fallback_search_results(query)
                        
                        results = []
                        
                        # Extract search results from RelatedTopics
                        for item in data.get('RelatedTopics', [])[:max_results]:
                            if 'Text' in item and 'FirstURL' in item:
                                results.append({
                                    'title': item.get('Text', '').split(' - ')[0] if ' - ' in item.get('Text', '') else item.get('Text', ''),
                                    'url': item.get('FirstURL', ''),
                                    'snippet': item.get('Text', '')
                                })
                        
                        # If no RelatedTopics, try Results
                        if not results:
                            for item in data.get('Results', [])[:max_results]:
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
            return self._get_fallback_search_results(query)
    
    def _get_fallback_search_results(self, query: str) -> List[Dict[str, Any]]:
        """
        Provide fallback search results when external API fails
        """
        print(f"Using fallback search results for query: {query}")
        
        # For financial queries, construct targeted URLs based on the query
        fallback_results = []
        
        # Extract potential company names or financial terms
        query_lower = query.lower()
        
        if 'jio' in query_lower or 'jiofin' in query_lower:
            fallback_results.extend([
                {
                    'title': f'Jio Financial Services - MoneyControl', 
                    'url': 'https://www.moneycontrol.com/india/stockpricequote/finance-investments/jiofinancialservices/JFS',
                    'snippet': f'MoneyControl comprehensive analysis and latest news on Jio Financial Services including financials, ratios, and expert opinions'
                },
                {
                    'title': f'Jio Financial Services - Economic Times',
                    'url': 'https://economictimes.indiatimes.com/jio-financial-services-ltd/stocks/companyid-72001.cms',
                    'snippet': f'Economic Times coverage of Jio Financial Services with market news, financial results and analysis'
                },
                {
                    'title': f'Jio Financial Services - Business Standard',
                    'url': 'https://www.business-standard.com/company/jio-financ-22032/information/company-profile',
                    'snippet': f'Business Standard profile and latest updates on Jio Financial Services business and performance'
                }
            ])
        else:
            # Generic financial sites for other queries
            fallback_results.extend([
                {
                    'title': f"Financial analysis for {query}",
                    'url': 'https://finance.yahoo.com',
                    'snippet': f"Yahoo Finance data for {query}"
                },
                {
                    'title': f"Market analysis for {query}",
                    'url': 'https://www.moneycontrol.com',
                    'snippet': f"MoneyControl financial analysis for {query}"
                },
                {
                    'title': f"Economic insights for {query}",
                    'url': 'https://economictimes.indiatimes.com/markets',
                    'snippet': f"Economic Times market analysis for {query}"
                }
            ])
        
        return fallback_results[:3]  # Return top 3 fallback results

    def extract_relevant_sections(self, content: str, query: str) -> str:
        """
        Extract sections of content most relevant to the query using keyword scoring
        """
        if not content or not query:
            return content[:2000] if content else ""
            
        # Prepare query keywords
        query_words = set(query.lower().split())
        # Add financial keywords to boost relevance
        financial_keywords = {'stock', 'financial', 'earnings', 'revenue', 'profit', 'market', 'analyst', 'forecast'}
        query_words.update(financial_keywords)
        
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        # Score paragraphs based on keyword matches
        scored_paragraphs = []
        for para in paragraphs:
            para_lower = para.lower()
            # Count keyword matches
            keyword_score = sum(1 for word in query_words if word in para_lower)
            # Boost score for longer, substantive paragraphs
            length_score = min(len(para) / 500, 2)  # Cap at 2x boost
            # Boost for financial terms
            financial_score = sum(0.5 for word in financial_keywords if word in para_lower)
            
            total_score = keyword_score + length_score + financial_score
            
            if total_score > 0:
                scored_paragraphs.append((total_score, para))
        
        if not scored_paragraphs:
            # Fallback to first 2000 chars if no relevant content found
            return content[:2000]
        
        # Sort by relevance and take top paragraphs
        scored_paragraphs.sort(reverse=True)
        relevant_content = '\n\n'.join([para for _, para in scored_paragraphs[:3]])
        
        # Ensure we don't exceed token limits
        return relevant_content[:2000]

    async def extract_smart_content(self, page, query: str) -> str:
        """
        Extract relevant content from page, removing noise elements
        """
        try:
            # Remove common noise elements
            await page.evaluate("""
                // Remove navigation, ads, and other noise
                const noiseSelectors = [
                    'nav', 'header', 'footer', '.nav', '.navigation',
                    '.ad', '.ads', '.advertisement', '.sidebar', '.menu',
                    '.cookie', '.popup', '.modal', '.overlay',
                    'script', 'style', '.social', '.share'
                ];
                
                noiseSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => el.remove());
                });
            """)
            
            # Try to find main content areas first
            content_selectors = [
                'article', '.article', '#article',
                '.content', '#content', '.main-content',
                '.post', '.entry', '.story',
                'main', '#main', '.main'
            ]
            
            content_text = ""
            
            # Try each selector to find main content
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content_text = await element.inner_text()
                        if len(content_text) > 200:  # Found substantial content
                            break
                except:
                    continue
            
            # Fallback to paragraphs if no main content found
            if not content_text or len(content_text) < 200:
                paragraphs = await page.query_selector_all('p')
                paragraph_texts = []
                
                for p in paragraphs[:15]:  # Limit to first 15 paragraphs
                    try:
                        text = await p.inner_text()
                        if len(text.strip()) > 30:  # Skip very short paragraphs
                            paragraph_texts.append(text.strip())
                    except:
                        continue
                
                content_text = '\n\n'.join(paragraph_texts)
            
            return content_text
            
        except Exception as e:
            print(f"Error extracting smart content: {e}")
            # Fallback to basic body text
            try:
                return await page.inner_text("body")
            except:
                return ""

    async def fetch_clean_html_with_playwright(self, url: str, query: str = "") -> str:
        """
        Fetch clean HTML content using playwright with smart extraction
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=VizDisplayCompositor',
                        '--no-sandbox',
                        '--disable-setuid-sandbox'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Set additional headers to look more like a real browser
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                # Navigate with retries
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        await page.goto(url, timeout=15000, wait_until='domcontentloaded')
                        await page.wait_for_timeout(2000)  # Wait for content to load
                        break
                    except Exception as nav_error:
                        if attempt == max_retries - 1:
                            raise nav_error
                        await page.wait_for_timeout(1000)  # Wait before retry
                
                # Extract smart content
                raw_content = await self.extract_smart_content(page, query)
                
                await browser.close()
                
                # Apply keyword-based relevance extraction
                relevant_content = self.extract_relevant_sections(raw_content, query)
                
                return relevant_content
                
        except Exception as e:
            print(f"Error fetching content from {url}: {e}")
            return ""

    async def search_and_scrape_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Enhanced web search that fetches actual content from top results with smart extraction
        """
        # First get search results
        search_results = await self.search_web(query, max_results)
        
        if not search_results:
            return []
        
        # Scrape content from top results with rate limiting
        enhanced_results = []
        for i, result in enumerate(search_results[:max_results]):
            url = result.get('url', '')
            if not url:
                continue
                
            print(f"Scraping content from: {url}")
            # Add delay between requests to avoid rate limiting
            if i > 0:
                await asyncio.sleep(1)
                
            # Pass query to extraction for relevance scoring
            content = await self.fetch_clean_html_with_playwright(url, query)
            
            enhanced_results.append({
                'title': result.get('title', ''),
                'url': url,
                'snippet': result.get('snippet', ''),
                'content': content if content else result.get('snippet', ''),
                'source': 'web'
            })
            
            # If no content was scraped, the result still contains the URL and snippet
            # which is sufficient for web source references
        
        return enhanced_results

    async def enhance_query_with_combined_context(self, original_query: str, local_context: str, web_results: List[Dict[str, Any]]) -> str:
        """
        Use Claude to enhance the original query with both local document and web search context
        """
        if not web_results and not local_context:
            system_prompt = "You are a financial AI assistant. Answer the user's question accurately and professionally."
            return self.llm_service.execute_prompt(system_prompt, original_query)

        # Prepare web context
        web_context = ""
        if web_results:
            web_context = "\n\n".join([
                f"Web Source: {result['title']} ({result['url']})\n{result['content']}"
                for result in web_results
            ])

        system_prompt = """You are a financial AI assistant with access to both local financial documents and current web information. Provide comprehensive answers that combine information from both sources when relevant.

Always prioritize accuracy and cite your sources appropriately using [Source: filename] for documents and [Web: URL] for web sources. When information conflicts, note the discrepancy and explain the difference."""

        context_parts = []
        if local_context:
            context_parts.append(f"Local Financial Documents:\n{local_context}")
        if web_context:
            context_parts.append(f"Current Web Information:\n{web_context}")

        user_prompt = f"""Question: {original_query}

{chr(10).join(context_parts)}

Please provide a comprehensive answer that incorporates relevant information from the available sources. If you find complementary information between local documents and web sources, highlight how they work together. If there are any conflicts or updates in the web information compared to the documents, please note them."""

        try:
            enhanced_response = self.llm_service.execute_prompt(system_prompt, user_prompt)
            return enhanced_response or "I couldn't generate a comprehensive response based on the available information."
        except Exception as e:
            print(f"Error enhancing query with combined context: {e}")
            return "Error processing the combined information sources."