# utils.py
from typing import List, Dict, Any
import re
import os

def validate_companies_input(companies: Any) -> List[Dict]:
    """Validate and normalize companies input."""
    if isinstance(companies, dict) and 'companies' in companies:
        companies = companies['companies']
    if not isinstance(companies, list):
        return []
    if not companies:
        return []
    valid_companies = []
    for company in companies:
        if isinstance(company, dict):
            valid_companies.append(company)
    return valid_companies

def safe_mcp_call(mcp_client, method_name: str, *args, **kwargs) -> Dict:
    """Safely call MCP methods."""
    try:
        # Check if the client has the specific method (e.g., search_general)
        if hasattr(mcp_client, method_name):
            method = getattr(mcp_client, method_name)
            result = method(*args, **kwargs)
            return result if result and not result.get('error') else {}
        # Fallback to generic search if specific method not found
        elif hasattr(mcp_client, '_mcp_search'):
             return mcp_client._mcp_search(*args)
        return {}
    except Exception as e:
        print(f"Error calling MCP {method_name}: {str(e)}")
        return {}

def deduplicate_by_key(items: List[Dict], key_func) -> List[Dict]:
    """Remove duplicates."""
    seen = set()
    unique_items = []
    for item in items:
        key = key_func(item)
        if key and key not in seen:
            seen.add(key)
            unique_items.append(item)
    return unique_items

def extract_domain_from_url(url: str) -> str:
    """
    Extract domain, but handle LinkedIn URLs intelligently.
    """
    if not url: return ""
    
    try:
        # 1. Clean up protocol
        clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        
        # 2. FIX: Handle LinkedIn URLs to guess real domain
        if "linkedin.com" in clean_url:
            # Ex: linkedin.com/company/razorpay-inc -> razorpay.com
            if "/company/" in clean_url:
                parts = clean_url.split("/company/")
                if len(parts) > 1:
                    slug = parts[1].split('/')[0].split('?')[0]
                    # Clean slug (razorpay-inc -> razorpay)
                    clean_slug = slug.split('-')[0] 
                    return f"{clean_slug}.com" 
            return "" # Return empty if we can't guess

        # 3. Standard extraction for real websites
        domain = clean_url.split('/')[0]
        return domain
    except:
        return ""