import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json

# --- 1. FIXED IMPORTS (Flat Structure) ---
# We assume all your python files are in the same main folder
from mcp_client import BrightDataMCP
from agents.company_discovery import CompanyDiscoveryTool
from agents.trigger_detection import TriggerDetectionTool
from agents.contact_research import ContactResearchTool
from agents.message_generation import MessageGenerationTool
from agents.pipeline_manager import LeadScoringTool, CRMIntegrationTool

load_dotenv()

st.set_page_config(
    page_title="AI BDR/SDR System",
    page_icon="🤖",
    layout="wide"
)

# --- 2. THE ADAPTER (CRITICAL FOR AGENTS TO WORK) ---
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
        # Pass-through for Discovery Agent
        raw = self.client._mcp_search(query)
        return {'results': self._normalize_results(raw)}

    def search_company_news(self, query):
        final_query = f"{query} latest business news"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def search_funding_news(self, query):
        final_query = f"{query} funding round series valuation"
        raw = self.client._mcp_search(final_query)
        return {'results': self._normalize_results(raw)}

    def scrape_company_linkedin(self, company_name):
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

# --- 3. UI LAYOUT ---
st.title("🤖 AI BDR/SDR Agent System")
st.markdown("**Real-time prospecting with multi-agent intelligence and trigger-based personalization**")

if 'workflow_results' not in st.session_state:
    st.session_state.workflow_results = None

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Ideal Customer Profile")
    industry = st.selectbox("Industry", ["SaaS", "FinTech", "E-commerce", "Healthcare", "AI/ML", "Quantitative Hedge Funds"])
    size_range = st.selectbox("Company Size", ["startup", "small", "medium", "enterprise"])
    location = st.text_input("Location (optional)", placeholder="San Francisco, NY, etc.")
    max_companies = st.slider("Max Companies", 5, 50, 5)
    
    st.subheader("Target Decision Makers")
    all_roles = ["CEO", "CTO", "VP Engineering", "Head of Product", "VP Sales", "CMO", "CFO","Head of Quantitative Strategies","Business Development Director","Hedge Fund Solutions","Head of Quant Research","Chief Investment Science Officer","Head of Quantitative Research","Quant PM"]
    target_roles = st.multiselect("Roles", all_roles, default=["CEO", "CTO", "VP Engineering","CFO"])
    
    st.subheader("Outreach Configuration")
    message_types = st.multiselect(
        "Message Types",
        ["cold_email", "linkedin_message"],
        default=["cold_email"]
    )
    
    with st.expander("Advanced Intelligence"):
        min_lead_grade = st.selectbox("Min CRM Export Grade", ["A", "B", "C"], index=1)
    
    st.divider()
    st.subheader("🔗 API Status")
    
    # Simple Check
    if os.getenv("BRIGHT_DATA_API_TOKEN"):
        st.success("🌐 Bright Data Connected")
    else:
        st.error("❌ Bright Data Missing")

    if os.getenv("OPENAI_API_KEY"):
        st.success("🧠 OpenAI Connected")
    else:
        st.error("❌ OpenAI Missing")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🚀 AI Prospecting Workflow")
    
    if st.button("Start Multi-Agent Prospecting", type="primary", use_container_width=True):
        if not os.getenv("BRIGHT_DATA_API_TOKEN"):
            st.error("Missing Bright Data Token")
            st.stop()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # --- 4. INITIALIZE TOOLS ---
            raw_client = BrightDataMCP()
            adapter = BrightDataAdapter(raw_client) # Wrap client in adapter!
            
            # Instantiate Tool Classes Directly (Robust method)
            discovery_tool = CompanyDiscoveryTool(mcp_client=adapter)
            trigger_tool = TriggerDetectionTool(mcp_client=adapter)
            contact_tool = ContactResearchTool(mcp_client=adapter)
            message_tool = MessageGenerationTool()
            scoring_tool = LeadScoringTool()
            crm_tool = CRMIntegrationTool()
            
            # --- PHASE 1: DISCOVERY ---
            status_text.text(f"🔍 Discovering {size_range} {industry} companies in {location}...")
            progress_bar.progress(10)
            
            companies = discovery_tool._run(industry, size_range, location)
            
            # Limit to user selection
            companies = companies[:max_companies]
            
            if not companies:
                st.error("No companies found. Try broadening your criteria.")
                st.stop()
                
            st.success(f"✅ Discovered {len(companies)} companies")
            
            # --- PHASE 2: TRIGGERS ---
            status_text.text("🎯 Analyzing trigger events (Funding, Hiring)...")
            progress_bar.progress(30)
            
            companies_with_triggers = trigger_tool._run(companies)
            total_triggers = sum(len(c.get('trigger_events', [])) for c in companies_with_triggers)
            st.success(f"✅ Detected {total_triggers} trigger events")
            
            # --- PHASE 3: CONTACTS ---
            status_text.text("👥 Finding decision-maker contacts & verifying emails...")
            progress_bar.progress(50)
            
            companies_with_contacts = contact_tool._run(companies_with_triggers, target_roles)
            total_contacts = sum(len(c.get('contacts', [])) for c in companies_with_contacts)
            st.success(f"✅ Found {total_contacts} verified contacts")
            
            # --- PHASE 4: SCORING ---
            status_text.text("📊 Scoring leads...")
            progress_bar.progress(70)
            
            final_companies = scoring_tool._run(companies_with_contacts)
            
            # --- PHASE 5: MESSAGING ---
            status_text.text("✍️ Generating personalized outreach...")
            progress_bar.progress(85)
            
            if os.getenv("OPENAI_API_KEY"):
                final_companies = message_tool._run(final_companies, message_types[0])
                total_messages = sum(1 for c in final_companies for p in c.get('contacts', []) if p.get('generated_message'))
                st.success(f"✅ Generated {total_messages} drafts")
            
            # --- FINISH ---
            progress_bar.progress(100)
            status_text.text("✅ Workflow completed successfully!")
            
            # Calculate Stats
            qualified_leads = [c for c in final_companies if c.get('lead_grade', 'D') in ['A', 'B']]
            
            st.session_state.workflow_results = {
                'companies': final_companies,
                'total_companies': len(final_companies),
                'total_triggers': total_triggers,
                'total_contacts': total_contacts,
                'qualified_leads': len(qualified_leads),
                'crm_results': {"success": 0, "errors": 0},
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            st.error(f"❌ Workflow failed: {str(e)}")
            st.write("Check your terminal for detailed logs.")

# --- 5. RESULTS DISPLAY ---
if st.session_state.workflow_results:
    results = st.session_state.workflow_results
    
    st.markdown("---")
    st.subheader("📊 Workflow Results")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏢 Companies", results['total_companies'])
    c2.metric("⚡ Triggers", results['total_triggers'])
    c3.metric("👥 Contacts", results['total_contacts'])
    c4.metric("⭐ Qualified Leads", results['qualified_leads'])
    
    st.subheader("🏢 Company Intelligence")
    
    for company in results['companies']:
        grade_color = "🟢" if company.get('lead_grade') == 'A' else "🟡" if company.get('lead_grade') == 'B' else "🔴"
        
        with st.expander(f"{grade_color} {company.get('name', 'Unknown')} - Grade {company.get('lead_grade')} (Score: {company.get('lead_score', 0)})"):
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown(f"**Website:** {company.get('domain')}")
                st.markdown(f"**Industry:** {company.get('industry')}")
                
                triggers = company.get('trigger_events', [])
                if triggers:
                    st.markdown("**🔥 Key Signals:**")
                    for t in triggers:
                        st.markdown(f"- {t.get('description')}")
            
            with col_b:
                contacts = company.get('contacts', [])
                if contacts:
                    st.markdown("**👥 Contacts:**")
                    for c in contacts:
                        st.markdown(f"**{c.get('first_name')} {c.get('last_name')}** ({c.get('title')})")
                        st.markdown(f"📧 `{c.get('email')}`")
                        
                        msg = c.get('generated_message')
                        if msg:
                            st.info(f"**Subject:** {msg.get('subject')}\n\n{msg.get('body')[:150]}...")
                        st.divider()

    # --- EXPORT SECTION ---
    st.subheader("📥 Export")
    
    # Prepare CSV
    csv_data = []
    for comp in results['companies']:
        trigger_txt = comp['trigger_events'][0]['description'] if comp.get('trigger_events') else ""
        for cont in comp.get('contacts', []):
            csv_data.append({
                "Company": comp.get('name'),
                "Industry": comp.get('industry'),
                "Website": comp.get('domain'),
                "Grade": comp.get('lead_grade'),
                "Trigger": trigger_txt,
                "Contact": f"{cont.get('first_name')} {cont.get('last_name')}",
                "Role": cont.get('title', 'Unknown'), # <--- ADDED ROLE HERE
                "Email": cont.get('email'),
                "LinkedIn": cont.get('linkedin_url', ''),
                "Subject": cont.get('generated_message', {}).get('subject')
            })
            
    if csv_data:
        df = pd.DataFrame(csv_data)
        # Reorder columns to put Role next to Contact
        cols = ["Company", "Industry", "Website", "Grade", "Trigger", "Contact", "Role", "Email", "LinkedIn", "Subject"]
        df = df[cols]
        
        csv = df.to_csv(index=False)
        st.download_button("📄 Download CSV", csv, "leads.csv", "text/csv")