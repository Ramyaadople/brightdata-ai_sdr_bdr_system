from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import Any, List
import spacy
import re

# ==========================================
# 1. INPUT SCHEMA
# ==========================================
class ContactResearchInput(BaseModel):
    companies: List[dict] = Field(description="List of companies to research contacts for")
    target_roles: List[str] = Field(description="List of target roles (e.g. CTO, Founder)")

# ==========================================
# 2. MAIN TOOL CLASS
# ==========================================
class ContactResearchTool(BaseTool):
    name: str = "research_contacts"
    description: str = "Find decision-maker contact information using Smart Role Matching"
    args_schema: type[BaseModel] = ContactResearchInput
    
    mcp: Any = Field(default=None, description="The MCP Client", exclude=True)
    _nlp: Any = PrivateAttr() 

    def __init__(self, mcp_client):
        super().__init__()
        self.mcp = mcp_client
        try:
            self._nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("   [System] Downloading Spacy AI Model (en_core_web_sm)...")
            from spacy.cli import download
            download("en_core_web_sm")
            self._nlp = spacy.load("en_core_web_sm")
    
    def _run(self, companies, target_roles) -> list:
        if not companies: return []
        if not isinstance(target_roles, list): target_roles = [target_roles]
        
        print(f"   [Contact Research] Searching for roles: {', '.join(target_roles)}")
        
        for company in companies:
            all_contacts = []
            
            for role in target_roles:
                # 1. Smart Search
                role_contacts = self._smart_role_search(company, role)
                
                for contact in role_contacts:
                    # 2. Enrich
                    enriched = self._enrich_contact_data(contact, company)
                    if self._validate_contact(enriched):
                        all_contacts.append(enriched)
            
            company['contacts'] = self._deduplicate_contacts(all_contacts)
            print(f"   [Contact Research] {company['name']}: Found {len(company['contacts'])} contacts.")
        
        return companies

    def _smart_role_search(self, company, role):
        # Expanded Synonyms (VP = Vice President)
        synonyms_map = {
            "CTO": ["Chief Technology Officer", "VP Engineering", "Vice President Engineering", "Head of Engineering"],
            "CEO": ["Chief Executive Officer", "Founder", "Co-Founder", "Managing Director", "MD", "Owner"],
            "CFO": ["Chief Financial Officer", "VP Finance", "Vice President Finance"],
            "CMO": ["Chief Marketing Officer", "VP Marketing", "Vice President Marketing"],
            "VP Sales": ["Head of Sales", "Chief Revenue Officer", "CRO", "Director of Sales", "Vice President Sales"],
            "Founder": ["Co-Founder", "CEO", "Owner"]
        }
        
        search_terms = [role]
        if role in synonyms_map:
            search_terms.extend(synonyms_map[role])
            
        for term in search_terms:
            # 🛑 FIX 1: REMOVED QUOTES from Company Name for broader matching
            # Query: M2P Fintech "Chief Technology Officer" site:linkedin.com/in/
            query = f'{company["name"]} "{term}" site:linkedin.com/in/'
            
            result = self._safe_mcp_call(self.mcp, 'search_general', query)
            
            if result and result.get('results'):
                contact = self._extract_contact_from_results(
                    result['results'], 
                    target_role=term,
                    company_name=company['name']
                )
                
                if contact:
                    return [contact] # Return list for consistency
        
        return []

    def _extract_contact_from_results(self, results, target_role, company_name):
        for res in results:
            title = res.get('title', '').strip()
            snippet = res.get('snippet', '').strip()
            link = res.get('link', '') or res.get('url', '')
            full_text = (title + " " + snippet).lower()
            
            # 1. Check for 'Past' indicators (using regex boundaries to avoid "Experience" matching "Ex")
            if re.search(r'\b(former|past|ex-|previous|retired)\b', title.lower()):
                continue

            # 🛑 FIX 2: RELAXED ROLE CHECK
            # Instead of checking ALL words, we check KEYWORDS.
            # e.g. If looking for "VP Engineering", match "Vice President" OR "VP" AND "Engineering"
            
            # Normalize role for checking (VP -> Vice President handling)
            role_keywords = target_role.lower().replace("vp ", "vice president ").split()
            
            # Check if enough keywords exist to be confident
            # We require at least one major word (like "Engineering" or "Technology") + title (CTO/VP)
            # Simplified: Check if the main part of the role exists
            matches = sum(1 for word in role_keywords if word in full_text)
            
            # If < 50% of the role words are found, skip.
            if matches / len(role_keywords) < 0.5:
                continue

            # 3. Name Extraction
            names = self._extract_names_from_text(title, company_name)
            
            if names:
                primary_name = names[0]
                return {
                    'first_name': primary_name[0],
                    'last_name': " ".join(primary_name[1:]),
                    'title': target_role, # Use the specific term found (e.g. "Founder")
                    'linkedin_url': link,
                    'source': 'mcp'
                }
                
        return None

    def _extract_names_from_text(self, text, company_name=""):
        if not text: return []
        
        # Clean Titles
        titles = [r'\bFAAN\b', r'\bDNP\b', r'\bPhD\b', r'\bMD\b', r'\bDr\.\b', r'\bMBA\b']
        clean_text = text
        for t in titles:
            clean_text = re.sub(t, '', clean_text, flags=re.IGNORECASE)

        doc = self._nlp(clean_text)
        names = []
        
        BAD_WORDS = ["Health", "Medical", "System", "Holdings", "Group", "Global", 
                     "China", "Payment", "Services", "Inc", "Ltd", "Contact", "Team", 
                     "Profile", "View", "LinkedIn", "Member"]
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name_text = ent.text.strip()
                
                # Filter bad names
                if company_name and (name_text.lower() in company_name.lower() or company_name.lower() in name_text.lower()):
                    continue
                if any(bad.lower() in name_text.lower() for bad in BAD_WORDS): continue
                if any(x in name_text.lower() for x in [' pvt', ' ltd', ' inc', ' corp']): continue

                parts = name_text.split()
                
                # 🛑 FIX 3: RELAXED NAME VALIDATION
                # Allow: "Ravi P.", "Jean-Luc"
                if len(parts) >= 2:
                    is_valid_name = True
                    for p in parts:
                        # Allow letters, dots, hyphens
                        if not re.match(r"^[A-Za-z\.\-]+$", p):
                            is_valid_name = False
                            break
                        # Must start Uppercase
                        if p[0].isalpha() and not p[0].isupper():
                            is_valid_name = False
                            break
                    
                    if is_valid_name:
                        names.append(parts)
        
        return names

    def _enrich_contact_data(self, contact, company):
        first = contact.get('first_name')
        last = contact.get('last_name')
        domain = company.get('domain')
        
        if all([first, last, domain]):
            # Clean names for email
            f_clean = re.sub(r'[^a-zA-Z]', '', first.lower())
            l_clean = re.sub(r'[^a-zA-Z]', '', last.lower())
            
            contact['email'] = f"{f_clean}.{l_clean}@{domain}"
            contact['email_valid'] = False 
            contact['confidence_score'] = 50 
        else:
            contact['email'] = ""
            contact['confidence_score'] = 10
        return contact

    def _deduplicate_contacts(self, contacts):
        unique = {}
        for c in contacts:
            key = f"{c['first_name']}{c['last_name']}"
            if key not in unique: unique[key] = c
        return list(unique.values())

    def _validate_contact(self, contact):
        return contact.get('first_name') and contact.get('last_name')

    def _safe_mcp_call(self, client, method, query):
        try:
            if hasattr(client, method):
                return getattr(client, method)(query)
            return client._mcp_search(query)
        except:
            return {}

def create_contact_research_agent(mcp_client):
    return Agent(
        role='Contact Researcher',
        goal='Find decision-maker contact information',
        backstory='Expert at finding email addresses and validating contact details.',
        tools=[ContactResearchTool(mcp_client)],
        verbose=True
    )