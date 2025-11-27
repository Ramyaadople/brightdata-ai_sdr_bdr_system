"""
AI BDR/SDR Agent Package

This package contains specialized AI tools and agents for business development:
- Company Discovery: Find potential customers matching ICP criteria
- Contact Research: Identify decision-makers and verified emails
- Message Generation: Create personalized outreach messages
- Pipeline Manager: Score leads and manage CRM integration
- Trigger Detection: Identify buying signals and optimal timing
"""

# Import the specific Tool classes we are using in the main script
from .company_discovery import CompanyDiscoveryTool, create_company_discovery_agent
from .contact_research import ContactResearchTool, create_contact_research_agent
from .message_generation import MessageGenerationTool, create_message_generation_agent
from .pipeline_manager import LeadScoringTool, create_pipeline_manager_agent
from .trigger_detection import TriggerDetectionTool, create_trigger_detection_agent

__all__ = [
    # Tool Classes (Used in integrated_test.py)
    'CompanyDiscoveryTool',
    'ContactResearchTool', 
    'MessageGenerationTool',
    'LeadScoringTool',
    'TriggerDetectionTool',

    # Agent Creators (Optional, for CrewAI flows)
    'create_company_discovery_agent',
    'create_contact_research_agent', 
    'create_message_generation_agent',
    'create_pipeline_manager_agent',
    'create_trigger_detection_agent'
]