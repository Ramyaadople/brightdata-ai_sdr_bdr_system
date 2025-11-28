import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
#  Apollo Email/Phone Lookup
# ---------------------------------------------------------
from agents.apollo_email_phone import apollo_lookup_by_linkedin

# ---------------------------------------------------------
# Existing Project Imports
# ---------------------------------------------------------
from mcp_client import BrightDataMCP
from agents.company_discovery import CompanyDiscoveryTool
from agents.trigger_detection import TriggerDetectionTool
from agents.contact_research import ContactResearchTool
from agents.message_generation import MessageGenerationTool
from agents.pipeline_manager import LeadScoringTool, CRMIntegrationTool

load_dotenv()

# ---------------------------------------------------------
# Streamlit Page Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI BDR/SDR System",
    page_icon="🤖",
    layout="wide"
)

# ---------------------------------------------------------
# Bright Data Adapter
# ---------------------------------------------------------
class BrightDataAdapter:
    def __init__(self, mcp_client):
        self.client = mcp_client

    def _normalize_results(self, raw_result):
        if not raw_result:
            return []
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
        raw = self.client._mcp_search(query)
        return {'results': self._normalize_results(raw)}

    def search_company_news(self, query):
        raw = self.client._mcp_search(f"{query} latest business news")
        return {'results': self._normalize_results(raw)}

    def search_funding_news(self, query):
        raw = self.client._mcp_search(f"{query} funding round series valuation")
        return {'results': self._normalize_results(raw)}

    def scrape_company_linkedin(self, company_name):
        raw = self.client._mcp_search(f"site:linkedin.com/company {company_name} hiring jobs")
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


# ---------------------------------------------------------
# Sidebar UI
# ---------------------------------------------------------
st.title("🤖 AI BDR/SDR Agent System")

with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("Ideal Customer Profile")
    industry = st.selectbox(
        "Industry",
        ["SaaS", "FinTech", "E-commerce", "Healthcare", "AI/ML", "Quant Funds"]
    )
    size_range = st.selectbox("Company Size", ["startup", "small", "medium", "enterprise"])
    location = st.text_input("Location", "")
    max_companies = st.slider("Max Companies", 5, 50, 10)

    st.subheader("Decision Maker Roles")
    all_roles = ["CEO", "CTO", "VP Engineering", "CFO",
                 "Head of Quantitative Research", "Head of Product", "VP Sales"]
    target_roles = st.multiselect("Roles", all_roles, default=["CEO", "CTO"])

    st.subheader("Message Type")
    message_types = st.multiselect(
        "Message Types",
        ["cold_email", "linkedin_message"],
        default=["cold_email"]
    )

    st.subheader("Apollo Settings")
    include_phone = st.radio("Include Phone Numbers?", ["No", "Yes"], index=0)

    st.subheader("API Status")
    st.success("🌐 Bright Data Connected") if os.getenv("BRIGHT_DATA_API_TOKEN") else st.error("Missing BRIGHT_DATA_API_TOKEN")
    st.success("🧠 OpenAI Connected") if os.getenv("OPENAI_API_KEY") else st.error("Missing OPENAI_API_KEY")
    st.success("📡 Apollo Connected") if os.getenv("APOLLO_API_KEY") else st.error("Missing APOLLO_API_KEY")

if "workflow_results" not in st.session_state:
    st.session_state.workflow_results = None


# ---------------------------------------------------------
# Run Workflow
# ---------------------------------------------------------
if st.button("🚀 Start Multi-Agent Prospecting", type="primary", use_container_width=True):

    try:
        raw_client = BrightDataMCP()
        adapter = BrightDataAdapter(raw_client)

        discovery = CompanyDiscoveryTool(mcp_client=adapter)
        trigger_tool = TriggerDetectionTool(mcp_client=adapter)
        contact_tool = ContactResearchTool(mcp_client=adapter)
        message_tool = MessageGenerationTool()
        scoring_tool = LeadScoringTool()
        crm_tool = CRMIntegrationTool()

        # ----------------- STEP 1: DISCOVERY -----------------
        companies = discovery._run(industry, size_range, location)
        companies = companies[:max_companies]

        # ----------------- STEP 2: TRIGGER EVENTS -----------------
        companies = trigger_tool._run(companies)

        # ----------------- STEP 3: CONTACT RESEARCH -----------------
        companies = contact_tool._run(companies, target_roles)

        # ----------------- STEP 4: APOLLO ENRICHMENT -----------------
        reveal_phone = (include_phone == "Yes")

        for comp in companies:
            for person in comp.get("contacts", []):
                linkedin_url = person.get("linkedin_url")
                if linkedin_url:
                    enriched = apollo_lookup_by_linkedin(linkedin_url, reveal_phone)
                    if enriched.get("email"):
                        person["email"] = enriched["email"]
                    if reveal_phone:
                        person["phone"] = enriched.get("phone")
                else:
                    person["phone"] = None

        # ----------------- STEP 5: SCORING -----------------
        companies = scoring_tool._run(companies)

        # ----------------- STEP 6: MESSAGE GENERATION -----------------
        companies = message_tool._run(companies, message_types[0])

        st.session_state.workflow_results = {
            "companies": companies,
            "timestamp": datetime.now()
        }

        st.success("✅ Workflow Completed Successfully!")

    except Exception as e:
        st.error(f"Workflow Failed: {str(e)}")


# ---------------------------------------------------------
# Display Results + CSV
# ---------------------------------------------------------
if st.session_state.workflow_results:
    companies = st.session_state.workflow_results["companies"]

    st.subheader("📊 Workflow Results")

    # -----------------------------------------------------
    # Build CSV Export
    # -----------------------------------------------------
    csv_rows = []

    for comp in companies:
        trigger_desc = ""
        trigger_url = ""

        if comp.get("trigger_events"):
            trigger_desc = comp["trigger_events"][0].get("description", "")
            trigger_url = comp["trigger_events"][0].get("url", "")

        for cont in comp.get("contacts", []):
            csv_rows.append({
                "Company": comp.get("name"),
                "Industry": comp.get("industry"),
                "Website": comp.get("domain"),
                "Contact": f"{cont.get('first_name')} {cont.get('last_name')}",
                "Role": cont.get("title"),
                "Email": cont.get("email"),
                "Phone": cont.get("phone") if include_phone == "Yes" else None,
                "Trigger": trigger_desc,
                "Trigger URL": trigger_url,
                "LinkedIn": cont.get("linkedin_url"),
                "Subject": cont.get("generated_message", {}).get("subject")
            })

    df = pd.DataFrame(csv_rows)

    st.download_button(
        "📄 Download CSV",
        df.to_csv(index=False),
        "leads.csv"
    )

    # -----------------------------------------------------
    # Display Company → Contacts → Triggers
    # -----------------------------------------------------
    st.subheader("🏢 Company Insights")

    for comp in companies:
        with st.expander(comp.get("name", "Company")):

            # --- TRIGGERS ---
            triggers = comp.get("trigger_events", [])
            if triggers:
                st.markdown("### 🔥 Trigger Events")
                for t in triggers:
                    if t.get("url"):
                        st.markdown(f"- **{t['description']}** — [View Source]({t['url']})")
                    else:
                        st.markdown(f"- **{t['description']}**")
                st.divider()

            # --- CONTACTS ---
            st.markdown("### 👥 Contacts")
            for cont in comp.get("contacts", []):
                st.markdown(f"**{cont.get('first_name')} {cont.get('last_name')}** ({cont.get('title')})")
                st.markdown(f"📧 Email: `{cont.get('email')}`")
                if include_phone == "Yes":
                    st.markdown(f"📞 Phone: `{cont.get('phone')}`")
                st.markdown(f"🔗 LinkedIn: {cont.get('linkedin_url')}")
                st.divider()
