# integrated_test.py
import os
import json
from mcp_client import BrightDataMCP
from agents.company_discovery import CompanyDiscoveryTool, CompanyDiscoveryInput

# Import your Agents
# Ensure you have saved the agent code into these filenames:
from agents.trigger_detection import TriggerDetectionTool
from agents.contact_research import ContactResearchTool
from agents.pipeline_manager import LeadScoringTool
from agents.message_generation import MessageGenerationTool

# ==========================================
# 🔌 THE ADAPTER (Bridging the Gap)
# ==========================================
class BrightDataAdapter:
    """
    Translates Agent specific requests (like 'scrape_linkedin') 
    into generic queries for your BrightDataMCP.
    """
    def __init__(self, mcp_client):
        self.client = mcp_client

    def _normalize_results(self, raw_result):
        """Standardizes Bright Data 'organic' results into a simple list."""
        if not raw_result:
            return []
        
        # Handle different potential key names
        items = raw_result.get('organic') or raw_result.get('results') or []
        
        normalized = []
        for item in items:
            normalized.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', '') or item.get('description', ''),
                'url': item.get('link', ''),
                'link': item.get('link', '') # duplicate for safety
            })
        return normalized

    def search_company_news(self, query):
        """Agent asks for news -> We search Google News"""
        print(f"   [Adapter] Searching news for: {query}")
        final_query = f"{query} latest business news"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def search_funding_news(self, query):
        """Agent asks for funding -> We search funding specifically"""
        print(f"   [Adapter] Checking funding for: {query}")
        final_query = f"{query} funding round series valuation"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def scrape_company_linkedin(self, company_name):
        """
        Agent asks for LinkedIn data -> We search LinkedIn via Google 
        and simulate the structure the Trigger Agent expects.
        """
        print(f"   [Adapter] Scanning LinkedIn for: {company_name}")
        final_query = f"site:linkedin.com/company {company_name} hiring jobs"
        raw = self.client._mcp_search(final_query)
        normalized = self._normalize_results(raw)
        
        # The Trigger Agent expects keys like 'hiring_posts'
        # We simulate this by checking if the search snippets mention hiring
        hiring_posts = []
        for item in normalized:
            text = (item['title'] + " " + item['snippet']).lower()
            if any(x in text for x in ['hiring', 'jobs', 'careers', 'vacancy']):
                hiring_posts.append(item)

        return {
            'hiring_posts': hiring_posts,
            'recent_activity': normalized[:2] # Assume top 2 results are recent
        }

# ==========================================
# 🚀 MAIN WORKFLOW
# ==========================================
def run_integrated_pipeline(icp_query):
    print("==================================================")
    print("🤖 AI SDR AGENT: STARTING FULL LIFECYCLE")
    print("==================================================")

    # 1. INIT CLIENT & ADAPTER
    real_client = BrightDataMCP()
    adapter = BrightDataAdapter(real_client) # This is what we pass to agents!

    # 2. PROSPECTING (Find Companies)
    print(f"\n🔍 Phase 1: Prospecting (ICP: {icp_query})")
    company_names = search_companies_from_icp(icp_query)
    
    if not company_names:
        print("❌ No companies found.")
        return

    # Convert to format required by agents
    # Taking top 2 for speed
    pipeline = [{'name': name} for name in company_names[:2]]
    print(f"✅ Pipeline Loaded: {[c['name'] for c in pipeline]}")

    # 3. TRIGGER DETECTION
    print("\n⚡ Phase 2: Detecting Trigger Events")
    trigger_agent = TriggerDetectionTool(mcp_client=adapter)
    pipeline = trigger_agent._run(pipeline)
    
    for c in pipeline:
        triggers = c.get('trigger_events', [])
        print(f"   > {c['name']}: {len(triggers)} triggers found (Score: {c.get('trigger_score')})")
        if triggers:
            print(f"     Latest: {triggers[0]['description']}")

    # 4. CONTACT RESEARCH
    print("\nbusts Phase 3: Finding Decision Makers")
    contact_agent = ContactResearchTool(mcp_client=adapter)
    # We look for tech leaders
    pipeline = contact_agent._run(pipeline, target_roles=["CTO", "VP Engineering", "Founder"])

    for c in pipeline:
        contacts = c.get('contacts', [])
        print(f"   > {c['name']}: {len(contacts)} contacts found")
        for p in contacts:
            print(f"     - {p['first_name']} {p['last_name']} ({p['title']}) | {p.get('email', 'No Email')}")

    # 5. LEAD SCORING
    print("\n📊 Phase 4: Scoring Leads")
    scoring_agent = LeadScoringTool()
    pipeline = scoring_agent._run(pipeline)
    
    for c in pipeline:
        print(f"   > {c['name']}: Grade {c.get('lead_grade')} (Score: {c.get('lead_score')})")

    # 6. MESSAGE GENERATION
    print("\n✍️  Phase 5: Generating Outreach")
    if os.getenv("OPENAI_API_KEY"):
        msg_agent = MessageGenerationTool()
        pipeline = msg_agent._run(pipeline)
        
        for c in pipeline:
            contacts = c.get('contacts', [])
            if contacts and contacts[0].get('generated_message'):
                msg = contacts[0]['generated_message']
                print(f"\n[Draft Email for {c['name']}]")
                print("-" * 40)
                print(f"Subject: {msg['subject']}")
                print(msg['body'])
                print("-" * 40)
    else:
        print("⚠️  Skipping message generation (No OpenAI API Key found)")

    # 7. SAVE RESULTS
    with open('final_leads.json', 'w') as f:
        json.dump(pipeline, f, indent=2)
    print("\n💾 Results saved to final_leads.json")

if __name__ == "__main__":
    # Your specific ICP
    icp = '"Fintech" "India"'
    run_integrated_pipeline(icp)