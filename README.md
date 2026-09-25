# AI Location Intelligence & Business Recommender

An end-to-end Machine Learning and Generative AI pipeline that analyzes geographical infrastructure, scrapes local market data, and autonomously recommends highly viable business models for specific localities.

This project was built to determine the viability of various commercial business types (Restaurants, Gyms, Pharmacies, etc.) across different neighborhoods by combining quantitative geospatial data with qualitative LLM-driven market gap analysis.

## 🚀 Key Features

*   **Machine Learning Prediction:** Uses trained Random Forest models to predict business viability based on infrastructure density (schools, transit, hospitals) and estimated local rent.
*   **Live Market Scraping:** Utilizes a headless `Playwright` scraper to extract real-time competitor density and customer sentiment directly from Google Maps.
*   **Multi-Agent LLM Strategy (Local AI):** Employs a local AI pipeline (via `Ollama`) orchestrating multiple models:
    *   **Agent 1 (Phi-3):** Synthesizes raw scraped DOM data into structured competitor profiles.
    *   **Agent 2 (Qwen 2.5):** Analyzes the synthesized data to identify local market gaps.
    *   **Agent 3 (Llama 3.1):** Acts as the "Chief Strategist" to output a comprehensive, evidence-based business strategy report.
*   **Model Agnostic (Bring Your Own Model):** The system is completely flexible. Users can run it 100% locally and privately using open-source models via Ollama, or they can plug in their own API keys to use cloud models (OpenAI, Gemini, Groq) for the strategy generation.
*   **Interactive Dashboard:** A fully featured Streamlit web application to visualize demographic insights and stream the AI-generated business recommendations live.

## 📁 Repository Structure

*   `app/` - Streamlit dashboards (`dashboard.py` for ML stats, `llm_dashboard.py` for live AI generation).
*   `data/` - Datasets containing localities, OpenStreetMap (OSM) features, and ground-truth validation.
*   `models/` - Pre-trained Random Forest models for fast inference.
*   `scripts/` - Core data ingestion pipelines, the Playwright scraper, and the Multi-Agent LLM logic.
*   `test_pipeline.py` / `auto_tuner.py` - End-to-end testing and autonomous location evaluation scripts.

## 🛠️ Setup & Installation

**1. Install dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```

**3. Choose Your AI Backend**
*   **Option A (100% Local):** Ensure [Ollama](https://ollama.com/) is installed and running, then pull the required models:
    ```bash
    ollama run phi3
    ollama run qwen2.5:3b
    ollama run llama3.1
    ```
*   **Option B (Cloud API Keys):** If you prefer to use OpenAI, Groq, or Gemini instead of running models locally, you can securely enter your API keys directly into the Streamlit UI.

**4. Run the interactive dashboard**
```bash
streamlit run app/dashboard.py
```
*(To run the generative AI dashboard, run `streamlit run app/llm_dashboard.py`)*

---
*Note: The pipeline includes a fallback mode if live API scraping is restricted or unavailable.*
