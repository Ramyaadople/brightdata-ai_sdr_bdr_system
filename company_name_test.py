import os
import json
from mcp_client import BrightDataMCP 

def search_companies_from_icp(icp_query):
    print(f"\n🔍 Searching for companies related to ICP: {icp_query}")

    client = BrightDataMCP()

    # STRATEGY CHANGE: 
    # We use Google to search ONLY within LinkedIn Company pages.
    # This guarantees the results are actual companies, not articles.
    # "site:linkedin.com/company" -> Forces LinkedIn Company pages
    # "India" -> Location
    # "Fintech" -> Industry
    
    # We construct a "Google Dork" query
    query = f'site:linkedin.com/company {icp_query}'
    
    print(f"🔍 Sending query: '{query}'") 
    
    result = client._mcp_search(query) 

    # Check for 'organic' (standard Google key)
    search_items = result.get('organic') or result.get('results')

    if not search_items:
        print("❌ No results found")
        return []

    companies = []
    
    print("\n🐛 Processing Titles...")
    for item in search_items:
        title = item.get('title', '').strip()
        link = item.get('link', '') # Get link to verify it's a company
        
        # SKIP LOGIC: Skip if it looks like a "Top 10 list" or a job posting
        if "Top" in title and "Companies" in title: 
            continue
        if "/jobs/" in link:
            continue

        # CLEANING LOGIC FOR LINKEDIN TITLES
        # LinkedIn titles usually look like: "Razorpay: Payment Gateway | LinkedIn"
        # or "CRED | LinkedIn"
        
        clean_name = title
        
        # 1. Remove " | LinkedIn" from the end
        if " | LinkedIn" in clean_name:
            clean_name = clean_name.split(" | LinkedIn")[0]
        
        # 2. Remove Taglines (everything after the first colon or hyphen)
        # Example: "Razorpay: Banking for Business" -> "Razorpay"
        if ":" in clean_name:
            clean_name = clean_name.split(":")[0]
        if " - " in clean_name:
             clean_name = clean_name.split(" - ")[0]

        clean_name = clean_name.strip()
            
        if clean_name and len(clean_name) > 1 and clean_name not in companies:
            companies.append(clean_name)

    print("\n🏢 Extracted Company Names:")
    for company in companies:
        print("•", company)

    return companies


if __name__ == "__main__":
    # UPDATED ICP STRING
    # We remove "Medium sized" because it's hard for Google keyword search.
    # Instead, we add keywords often found on medium company profiles.
    # Or we just keep it simple.
    
    # Option 1: Broad Search
    icp = '"Fintech" "India"'
    
    # Option 2 (Better): If you want size, you can try adding employee counts
    # icp = '"Fintech" "India" "50-200 employees"' 

    search_companies_from_icp(icp)