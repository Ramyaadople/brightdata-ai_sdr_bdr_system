from crewai import Agent
from crewai.tools import BaseTool
from typing import Any, List, Dict
from pydantic import BaseModel, Field
import openai
import time
from .utils import safe_mcp_call, deduplicate_by_key, extract_domain_from_url
import os


class CompanyDiscoveryInput(BaseModel):
    industry: str = Field(description="Target industry")
    size_range: str = Field(description="Company size")
    location: str = Field(default="", description="Location")
    limit: int = Field(default=10, description="Target number of companies")

class CompanyDiscoveryTool(BaseTool):
    name: str = "discover_companies"
    description: str = "Find companies matching ICP using AI-based filtering"
    args_schema: type[BaseModel] = CompanyDiscoveryInput
    mcp: Any = None
    client: Any = None
    
    def __init__(self, mcp_client):
        super().__init__()
        self.mcp = mcp_client
        
        # Initialize OpenAI for "Smart Filtering"
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            print("⚠️ Warning: No OpenAI Key found. Smart filtering will be disabled.")
    
    def _run(self, industry: str, size_range: str, location: str = "", limit: int = 10) -> list:
        print(f"   [Discovery] Searching for {limit} {size_range} {industry} companies in {location}...")
        
        all_companies = []
        
        # 🛑 PAGINATION STRATEGY
        # We iterate through these query patterns to fetch different batches of results
        search_queries = [
            f'site:linkedin.com/company "{industry}" "{location}"',           # Page 1 Logic
            f'site:linkedin.com/company "{industry}" "{location}" "Overview"', # Page 2 Logic
            f'site:linkedin.com/company "{industry}" "{location}" "About"',    # Page 3 Logic
            f'"{industry}" companies in "{location}" -intitle:Top -intitle:List', # Broad Search
        ]
        
        for query in search_queries:
            # Stop if we have enough companies
            if len(all_companies) >= limit:
                break
                
            print(f"      🔎 Querying: {query}...")
            raw_results = safe_mcp_call(self.mcp, 'search_general', query)
            
            # Process & Filter
            batch = self._process_search_results(raw_results, industry)
            all_companies.extend(batch)
            
            # Deduplicate immediately to check real progress
            all_companies = deduplicate_by_key(all_companies, lambda c: c['name'].lower())
            print(f"      --> Found {len(batch)} new. Total unique: {len(all_companies)}")
            
            # Be nice to the API
            time.sleep(1)
        
        # Final Slice to requested limit
        return all_companies[:limit]

    def _process_search_results(self, raw_data: Dict, industry: str) -> List[Dict]:
        results_list = []
        if isinstance(raw_data, dict):
            results_list = raw_data.get('results') or raw_data.get('organic') or []
        elif isinstance(raw_data, list):
            results_list = raw_data
            
        found_companies = []

        for item in results_list:
            title = item.get('title', '').strip()
            link = item.get('link', '') or item.get('url', '')
            snippet = item.get('snippet', '') or item.get('description', '')

            # --- 1. STRUCTURAL FILTERING ---
            domain = extract_domain_from_url(link)
            if any(tld in domain for tld in ['.org', '.gov', '.edu']):
                continue
            
            if "/jobs/" in link or "/people/" in link: continue

            # --- 2. AI INTELLIGENCE CHECK ---
            if self.client:
                is_company = self._validate_with_ai(title, snippet)
                if not is_company:
                    continue

            # --- 3. CLEANING & SAVING ---
            clean_name = self._clean_name_logic(title)

            if clean_name and len(clean_name) > 1 and len(clean_name) < 50:
                # Try to find real website
                real_domain = self._find_official_website(clean_name) or domain

                found_companies.append({
                    'name': clean_name,
                    'industry': industry,
                    'domain': real_domain,
                    'linkedin_url': link,
                    'description': snippet[:200],
                    'source': 'linkedin_site_search',
                    'icp_score': 85
                })

        return found_companies

    def _find_official_website(self, company_name):
        """Finds the official website using a quick lookup."""
        query = f"{company_name} official website"
        result = safe_mcp_call(self.mcp, 'search_general', query)
        
        if result and (result.get('results') or result.get('organic')):
            items = result.get('results') or result.get('organic')
            for item in items:
                link = item.get('link', '') or item.get('url', '')
                ignore_hosts = ['linkedin', 'facebook', 'twitter', 'instagram', 'crunchbase', 'wikipedia']
                if any(host in link for host in ignore_hosts):
                    continue
                return extract_domain_from_url(link)
        return ""

    def _validate_with_ai(self, name, snippet):
        """Uses GPT to filter non-companies."""
        try:
            prompt = (
                f"Is '{name}' a specific FOR-PROFIT COMPANY? Reply YES or NO.\n"
                f"Context: {snippet}\n"
                f"Ignore: Foundations, Lists, Articles, Jobs."
            )
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2,
                temperature=0
            )
            return "YES" in response.choices[0].message.content.strip().upper()
        except:
            return True

    def _clean_name_logic(self, title):
        clean = title
        for sep in [" | ", " - ", " : ", " on LinkedIn"]:
            if sep in clean:
                clean = clean.split(sep)[0]
        return clean.strip()

def create_company_discovery_agent(mcp_client):
    return Agent(
        role='Company Discovery Specialist',
        goal='Find high-quality prospects',
        backstory='Expert at finding specific company entities.',
        tools=[CompanyDiscoveryTool(mcp_client)],
        verbose=True
    )