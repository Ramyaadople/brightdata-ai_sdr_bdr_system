🤖 AI BDR/SDR Agent System

An autonomous Business Development Representative (BDR) Agent that automates the entire outbound sales lifecycle. It finds companies, identifies verified decision-makers, detects buying signals, and writes personalized cold emails using a multi-agent architecture.

🌟 Key Features

1. Intelligent Company Discovery

Targeted Search: Uses site:linkedin.com/company to find specific entities, avoiding "Top 10" listicles or directories.

Smart Filtering: Automatically filters out Non-Profits, Foundations, and Associations using keyword heuristics.

Real Domain Resolution: Performs secondary searches to find the actual company website (e.g., m2pfintech.com) instead of just the LinkedIn URL.

2. Deep Contact Research (The "Hunter" Engine)

Smart Role Matching: If "CTO" isn't found, it automatically searches for synonyms like "VP Engineering", "Head of Technology", or "Technical Director".

Strict Name Validation: Uses spaCy (NLP) and Regex to ensure names are human (e.g., "Ravi Pratap") and rejects business words (e.g., prevents "Dear Payment Services").

Current Role Verification: specific logic to reject profiles labeled "Former", "Past", or "Ex-".

3. Trigger-Based Personalization

Event Detection: Scans news for Hiring Spikes, Funding Rounds, and Leadership changes.

Contextual Messaging: GPT-4 writes emails referencing the specific trigger found (e.g., "Saw you are hiring for 9 engineering roles...").

4. Data Validation & Export

404 Checks: Automatically pings LinkedIn URLs to ensure they are live before exporting.

Clean CSV: Exports a structured CSV with columns for Company, Website, Contact Name, Role, Email, and Draft Message.

🛠️ Tech Stack

UI: Streamlit

Orchestration: CrewAI

Web Search / Scraping: Bright Data (MCP Protocol)

Intelligence: OpenAI (GPT-4o-mini)

NLP/NER: spaCy (for name entity recognition)

Data Processing: Pandas

🚀 Installation

1. Setup Folder

Create a new folder and save all the .py files provided in the chat (app.py, contact_research.py, etc.) into it.

2. Create Virtual Environment

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


3. Install Dependencies

pip install -r requirements.txt


4. Install NLP Models (Crucial)

This system uses spaCy for name cleaning. You must download the language model:

python -m spacy download en_core_web_sm


⚙️ Configuration

Create a .env file in the root directory and add your API keys:

# Required for Web Search
BRIGHT_DATA_API_TOKEN=your_bright_data_token

# Required for Intelligence & Message Writing
OPENAI_API_KEY=sk-your_openai_key

# Optional: For CRM Export
HUBSPOT_API_KEY=your_hubspot_key


🏃‍♂️ How to Run

Start the application:

streamlit run app.py


Open your browser to the local URL (usually http://localhost:8501).

Sidebar Settings:

Select Industry (e.g., FinTech).

Select Size (e.g., Medium).

Select Target Roles (e.g., CTO, CEO).

Click "Start Multi-Agent Prospecting".

Once finished, scroll down to download the Validated CSV.

📂 Project Structure

Ensure your folder has these files:

File

Purpose

app.py

The main Streamlit dashboard and orchestration logic.

company_discovery.py

Agent that finds companies and filters out junk/non-profits.

contact_research.py

Agent that finds people, handles role synonyms, and cleans names.

trigger_detection.py

Agent that finds news (Funding/Hiring) to use as hooks.

message_generation.py

Agent that uses GPT-4 to write the actual email copy.

pipeline_manager.py

Agent that scores leads (A/B/C) and handles CRM export.

mcp_client.py

The client handling connection to Bright Data.

utils.py

Shared utilities for URL parsing and API safety.

requirements.txt

List of python libraries needed.

.env

Your API keys (Bright Data, OpenAI).