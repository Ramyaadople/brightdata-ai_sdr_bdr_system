import os
import json # Added for cleaner debug printing
from mcp_client import BrightDataMCP  # your client class

def search_companies_from_icp(icp_query):
    """Search Google for companies matching the ICP and return names."""
    print(f"\n🔍 Searching for companies related to ICP: {icp_query}")

    # Initialize MCP client
    client = BrightDataMCP()

    # Query construction
    query = icp_query 
    
    print(f"🔍 Sending query: '{query}'") 
    
    # 1. CALL API (Only Once!)
    result = client._mcp_search(query) 

    # 2. DEBUG BLOCK
    print("\n🐛 DEBUG: Raw Result Inspection")
    if isinstance(result, dict):
        print(f"Keys found: {list(result.keys())}")
        # Uncomment the line below if you need to see the full messy data
        # print(json.dumps(result, indent=2)) 
    else:
        print(f"Result type: {type(result)}")
        print(result)
    print("------------------------------\n")

    # 3. SMART DATA EXTRACTION
    # We check for 'organic' (common in SERP) OR 'results' (common in other APIs)
    search_items = result.get('organic') or result.get('results')

    if not search_items:
        print("❌ No results found (checked 'organic' and 'results' keys)")
        return []

    companies = []
    
    # Iterate through the list we found
    for item in search_items:
        title = item.get('title', '').strip()
        
        # BASIC CLEANING
        if " - " in title:
            title = title.split(" - ")[0]
        if " | " in title:
            title = title.split(" | ")[0]
        if "..." in title: # Removes truncated titles
            title = title.replace("...", "").strip()
            
        if title and len(title) > 2:
            companies.append(title)

    print("\n🏢 Extracted Company Names:")
    for company in companies:
        print("•", company)

    return companies


if __name__ == "__main__":
    # ICP
    icp = "Medium sized Fintech companies in India"
    search_companies_from_icp(icp)