import os
import json
import csv
from mcp_client import BrightDataMCP

# ==========================================
# 📦 IMPORTS (Fixed for flat folder structure)
# ==========================================
from agents.company_discovery import CompanyDiscoveryTool
from agents.trigger_detection import TriggerDetectionTool
from agents.contact_research import ContactResearchTool
from agents.pipeline_manager import LeadScoringTool
from agents.message_generation import MessageGenerationTool

# ==========================================
# 🔌 THE ADAPTER
# ==========================================
class BrightDataAdapter:
    def __init__(self, mcp_client):
        self.client = mcp_client

    def _normalize_results(self, raw_result):
        if not raw_result: return []
        items = raw_result.get('organic') or raw_result.get('results') or []
        normalized = []
        for item in items:
            normalized.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', '') or item.get('description', ''),
                'url': item.get('link', '') or item.get('url', ''),
                'link': item.get('link', '') or item.get('url', '')
            })
        return normalized

    def search_general(self, query):
        print(f"   [Adapter] General Search: {query}")
        raw = self.client._mcp_search(query)
        return {'results': self._normalize_results(raw)}

    def search_company_news(self, query):
        print(f"   [Adapter] Searching news for: {query}")
        final_query = f"{query} latest business news"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def search_funding_news(self, query):
        print(f"   [Adapter] Checking funding for: {query}")
        final_query = f"{query} funding round series valuation"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def scrape_company_linkedin(self, company_name):
        print(f"   [Adapter] Scanning LinkedIn for: {company_name}")
        final_query = f"site:linkedin.com/company {company_name} hiring jobs"
        raw = self.client._mcp_search(final_query)
        normalized = self._normalize_results(raw)
        
        hiring_posts = []
        for item in normalized:
            text = (item['title'] + " " + item['snippet']).lower()
            if any(x in text for x in ['hiring', 'jobs', 'careers', 'vacancy']):
                hiring_posts.append(item)

        return {
            'hiring_posts': hiring_posts,
            'recent_activity': normalized[:2]
        }

# ==========================================
# 🚀 MAIN WORKFLOW
# ==========================================
def run_integrated_pipeline():
    print("==================================================")
    print("🤖 AI SDR AGENT: STARTING FULL LIFECYCLE")
    print("==================================================")

    # 1. SETUP
    real_client = BrightDataMCP()
    adapter = BrightDataAdapter(real_client) 

    # 2. PROSPECTING
    target_industry = "Fintech"
    target_size = "Medium"
    target_location = "India"

    print(f"\n🔍 Phase 1: Prospecting ({target_size} {target_industry} in {target_location})")
    
    # Initialize Tool
    discovery_tool = CompanyDiscoveryTool(mcp_client=adapter)
    
    # Run Tool
    pipeline = discovery_tool._run(industry=target_industry, size_range=target_size, location=target_location)
    
    if not pipeline:
        print("❌ No companies found. Stopping.")
        return

    # Limit to top 3 for speed/testing
    pipeline = pipeline[:3]
    print(f"✅ Pipeline Loaded: {[c['name'] for c in pipeline]}")

    # 3. TRIGGERS
    print("\n⚡ Phase 2: Detecting Trigger Events")
    trigger_agent = TriggerDetectionTool(mcp_client=adapter)
    pipeline = trigger_agent._run(pipeline)

    # 4. CONTACTS
    print("\n👥 Phase 3: Finding Decision Makers")
    contact_agent = ContactResearchTool(mcp_client=adapter)
    pipeline = contact_agent._run(pipeline, target_roles=["CTO", "VP Engineering", "Founder"])

    # 5. SCORING
    print("\n📊 Phase 4: Scoring Leads")
    scoring_agent = LeadScoringTool()
    pipeline = scoring_agent._run(pipeline)

    # 6. MESSAGING
    print("\n✍️  Phase 5: Generating Outreach")
    if os.getenv("OPENAI_API_KEY"):
        msg_agent = MessageGenerationTool()
        pipeline = msg_agent._run(pipeline)
    else:
        print("⚠️  Skipping message generation (No OpenAI API Key found)")

    # ==========================================
    # 💾 EXPORT SECTION
    # ==========================================
    
    # 1. Save JSON (Raw Data)
    with open('final_leads.json', 'w') as f:
        json.dump(pipeline, f, indent=2)
    print("\n💾 JSON saved to 'final_leads.json'")

    # 2. Save CSV (Excel Friendly)
    csv_filename = 'final_leads.csv'
    
    # Define columns
    fieldnames = [
        "Company Name", "Industry", "Website", "Lead Grade", "Lead Score", 
        "Top Trigger", "Contact Name", "Contact Title", "Email", "LinkedIn URL", 
        "Email Subject", "Email Body"
    ]

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for company in pipeline:
                # Prepare base company info
                trigger_text = ""
                if company.get('trigger_events'):
                    trigger_text = company['trigger_events'][0].get('description', '')

                base_data = {
                    "Company Name": company.get('name'),
                    "Industry": company.get('industry'),
                    "Website": company.get('domain'),
                    "Lead Grade": company.get('lead_grade'),
                    "Lead Score": company.get('lead_score'),
                    "Top Trigger": trigger_text
                }

                contacts = company.get('contacts', [])
                
                if not contacts:
                    # Write company row even if no contacts found
                    writer.writerow(base_data)
                else:
                    # Write one row per contact
                    for contact in contacts:
                        row = base_data.copy()
                        generated_msg = contact.get('generated_message', {})
                        
                        row.update({
                            "Contact Name": f"{contact.get('first_name','')} {contact.get('last_name','')}".strip(),
                            "Contact Title": contact.get('title'),
                            "Email": contact.get('email'),
                            "LinkedIn URL": contact.get('linkedin_url'),
                            "Email Subject": generated_msg.get('subject', ''),
                            "Email Body": generated_msg.get('body', '')
                        })
                        writer.writerow(row)
                        
        print(f"💾 CSV saved to '{csv_filename}'")
        
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")

if __name__ == "__main__":
    run_integrated_pipeline()

# ==========================================
# 🔌 THE ADAPTER
# ==========================================
class BrightDataAdapter:
    def __init__(self, mcp_client):
        self.client = mcp_client

    def _normalize_results(self, raw_result):
        if not raw_result: return []
        items = raw_result.get('organic') or raw_result.get('results') or []
        normalized = []
        for item in items:
            normalized.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', '') or item.get('description', ''),
                'url': item.get('link', '') or item.get('url', ''),
                'link': item.get('link', '') or item.get('url', '')
            })
        return normalized

    def search_general(self, query):
        print(f"   [Adapter] General Search: {query}")
        raw = self.client._mcp_search(query)
        return {'results': self._normalize_results(raw)}

    def search_company_news(self, query):
        print(f"   [Adapter] Searching news for: {query}")
        final_query = f"{query} latest business news"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def search_funding_news(self, query):
        print(f"   [Adapter] Checking funding for: {query}")
        final_query = f"{query} funding round series valuation"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def scrape_company_linkedin(self, company_name):
        print(f"   [Adapter] Scanning LinkedIn for: {company_name}")
        final_query = f"site:linkedin.com/company {company_name} hiring jobs"
        raw = self.client._mcp_search(final_query)
        normalized = self._normalize_results(raw)
        
        hiring_posts = []
        for item in normalized:
            text = (item['title'] + " " + item['snippet']).lower()
            if any(x in text for x in ['hiring', 'jobs', 'careers', 'vacancy']):
                hiring_posts.append(item)

        return {
            'hiring_posts': hiring_posts,
            'recent_activity': normalized[:2]
        }

# ==========================================
# 🚀 MAIN WORKFLOW
# ==========================================
def run_integrated_pipeline():
    print("==================================================")
    print("🤖 AI SDR AGENT: STARTING FULL LIFECYCLE")
    print("==================================================")

    # 1. SETUP
    real_client = BrightDataMCP()
    adapter = BrightDataAdapter(real_client) 

    # 2. PROSPECTING
    target_industry = "Fintech"
    target_size = "Medium"
    target_location = "India"

    print(f"\n🔍 Phase 1: Prospecting ({target_size} {target_industry} in {target_location})")
    
    discovery_tool = CompanyDiscoveryTool(mcp_client=adapter)
    pipeline = discovery_tool._run(industry=target_industry, size_range=target_size, location=target_location)
    
    if not pipeline:
        print("❌ No companies found. Stopping.")
        return

    # Limit to top 3 for speed
    pipeline = pipeline[:3]
    print(f"✅ Pipeline Loaded: {[c['name'] for c in pipeline]}")

    # 3. TRIGGERS
    print("\n⚡ Phase 2: Detecting Trigger Events")
    trigger_agent = TriggerDetectionTool(mcp_client=adapter)
    pipeline = trigger_agent._run(pipeline)

    # 4. CONTACTS
    print("\n👥 Phase 3: Finding Decision Makers")
    contact_agent = ContactResearchTool(mcp_client=adapter)
    pipeline = contact_agent._run(pipeline, target_roles=["CTO", "VP Engineering", "Founder"])

    # 5. SCORING
    print("\n📊 Phase 4: Scoring Leads")
    scoring_agent = LeadScoringTool()
    pipeline = scoring_agent._run(pipeline)

    # # 6. MESSAGING
    # print("\n✍️  Phase 5: Generating Outreach")
    # if os.getenv("OPENAI_API_KEY"):
    #     msg_agent = MessageGenerationTool()
    #     pipeline = msg_agent._run(pipeline)
    # else:
    #     print("⚠️  Skipping message generation (No OpenAI API Key found)")

    # ==========================================
    # 💾 EXPORT SECTION
    # ==========================================
    
    # 1. Save JSON (Raw Data)
    with open('final_leads.json', 'w') as f:
        json.dump(pipeline, f, indent=2)
    print("\n💾 JSON saved to 'final_leads.json'")

    # 2. Save CSV (Excel Friendly)
    csv_filename = 'final_lead.csv'
    
    # Define columns
    fieldnames = [
        "Company Name", "Industry", "Website", "Lead Grade", "Lead Score", 
        "Top Trigger", "Contact Name", "Contact Title", "Email", "LinkedIn URL"
    ]

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for company in pipeline:
                # Prepare base company info
                trigger_text = ""
                if company.get('trigger_events'):
                    trigger_text = company['trigger_events'][0].get('description', '')

                base_data = {
                    "Company Name": company.get('name'),
                    "Industry": company.get('industry'),
                    "Website": company.get('domain'),
                    "Lead Grade": company.get('lead_grade'),
                    "Lead Score": company.get('lead_score'),
                    "Top Trigger": trigger_text
                }

                contacts = company.get('contacts', [])
                
                if not contacts:
                    # Write company row even if no contacts found
                    writer.writerow(base_data)
                else:
                    # Write one row per contact
                    for contact in contacts:
                        row = base_data.copy()
                        generated_msg = contact.get('generated_message', {})
                        
                        row.update({
                            "Contact Name": f"{contact.get('first_name','')} {contact.get('last_name','')}".strip(),
                            "Contact Title": contact.get('title'),
                            "Email": contact.get('email'),
                            "LinkedIn URL": contact.get('linkedin_url')
                        })
                        writer.writerow(row)
                        
        print(f"💾 CSV saved to '{csv_filename}'")
        
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")

if __name__ == "__main__":
    run_integrated_pipeline()