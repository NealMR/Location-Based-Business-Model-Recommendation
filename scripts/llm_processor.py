import os

try:
    import ollama
except ImportError:
    ollama = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def stream_gemini(prompt, api_key, model_name="gemini-1.5-flash"):
    if genai is None:
        yield "\n\n**API Error:** Google Generative AI SDK is not installed or failed to import."
        return
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, stream=True)
        yield "> **[Neural Synthesis Log: Gemini API]**  \n> Processing request in cloud  \n"
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"\n\n**API Error:** {str(e)}"

def stream_openai_compatible(prompt, api_key, model_name, base_url=None):
    if OpenAI is None:
        yield "\n\n**API Error:** OpenAI SDK is not installed or failed to import."
        return
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        yield f"> **Neural Synthesis Log ({model_name})**  \n> Processing request in cloud...  \n"
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n\n**API Error:** {str(e)}"
def generate_business_strategy_stream(location_name, infrastructure_data, competitor_data, review_data, property_details="", model_name='phi3', api_keys=None):
    api_keys = api_keys or {}
    """
    Standard single-model inference stream.
    """
    prompt = f"""
You are an elite enterprise Location Intelligence & Business Feasibility AI.
Your core objective is: "Analyze this location and identify unmet, economically plausible customer needs."
Business ideas must be a result of the analysis, not the starting point.
Pipeline: Location → Ecosystem → Customer Segments → Needs → Competition → Gaps → Business Concepts → Economics → Risks → Validation

### ZERO-HALLUCINATION & EVIDENCE POLICY (CRITICAL)
This system is a data-analysis engine, not a creative business-idea generator.
The model MUST distinguish between:
1. Observed facts
2. Deterministic calculations
3. Evidence-based interpretations
4. Hypotheses
Never present a hypothesis or assumption as a fact.

1. SOURCE-BOUND FACTS: Use ONLY information contained in the supplied Market Intelligence dataset. If required information is missing, output "UNKNOWN" or "INSUFFICIENT DATA". Do not guess.
2. MISSING DATA ≠ ABSENCE: Never interpret missing records as proof that something does not exist. Use "not detected in available data" when dataset coverage is incomplete.
3. CALCULATIONS ARE ALLOWED: You may calculate derived metrics ONLY from supplied inputs using transparent formulas (counts, averages, ratios). Do NOT invent the underlying inputs.
4. NO UNSUPPORTED NUMBERS: Never invent room counts, footfall, revenue, margins, or market size unless directly supplied or deterministically calculated.
5. NO FAKE PROBABILITIES: Do not output "86% viability" or "70% opportunity". Use Business Fit Score, Evidence Confidence, and Data Completeness.
6. EVIDENCE TRACEABILITY: Every major recommendation must identify its supporting evidence.
7. CLAIM TYPES: Classify statements as FACT (directly observed), DERIVED (mathematically calculated), INTERPRETATION, or HYPOTHESIS.
8. REVIEW ANALYSIS: Only report customer complaints explicitly supported by review text.
9. COMPETITOR ANALYSIS: "No competitor" does not equal "market gap". A gap requires demand evidence, low competition density, and unmet needs.
10. BUSINESS RECOMMENDATION GATE: Before recommending, verify Customer segment, Demand evidence, Competition evidence, Space compatibility. If critical evidence is missing, state Recommendation Status = INSUFFICIENT DATA.
11. SPECIFICITY: Do not output generic ideas ("Cafe"). Describe target customer, problem, format, revenue streams, differentiator, and risks.
12. WHY THIS BUSINESS: Answer Why this customer? Why this need? Why this location? What evidence supports it?
13. WHY NOT: Identify at least one evidence-based risk or reason the idea may fail.
14. NO ESG FILLER: Do not recommend solar, EV charging, or "smart" features unless supplied data provides a clear business justification.
15. FINANCIAL ANALYSIS: Distinguish between Observed Input, Assumption, and Derived Estimate.
16. UNCERTAINTY: Use High Confidence, Medium Confidence, Low Confidence, or Insufficient Data. Do not use certainty language ("will succeed").
17. COMPLETENESS RULE: You MUST output the ENTIRE Markdown report structure requested below. Do not abort the report. Use the raw POI data to fill out Sections 1, 2, and 3. If you lack sufficient evidence to recommend a business in Sections 4 and 5, output "INSUFFICIENT DATA" for the business name, but still complete the rest of the structural analysis. Do not be overly pessimistic: if {infrastructure_data} shows 5 colleges, that IS factual evidence of student demand.

### 1. User's Constraints (PHYSICS LAYER):
{property_details if property_details.strip() else "No specific property constraints provided. Assume a standard flexible commercial space."}

### 2. Market Intelligence:
Location Query: This analysis is for the user's requested location: {location_name}
Infrastructure: {infrastructure_data}
Competitors: {competitor_data}
Reviews: {review_data}

### CRITICAL INSTRUCTIONS:
1. Start with `<thought>...</thought>` tags. Evaluate the ecosystem, filter ideas through the Recommendation Gate, and derive metrics.
2. After the thought block, output the final report STRICTLY matching the structure and Markdown formatting below. Use Markdown tables, clean headings, and bullet points. DO NOT USE ANY EMOJIS OR ASCII ART IN YOUR OUTPUT.

# MARKET INTELLIGENCE REPORT

**LOCATION**  
[Analyze coordinates/data to determine Area]

**AREA PROFILE**  
[e.g., Medical + Education + Residential]

---
## 1. LOCAL DEMAND

| Customer Segment | Demand Intensity | Rationale |
| :--- | :--- | :--- |
| [Segment 1] | **HIGH** | [Brief reason] |
| [Segment 2] | **MEDIUM** | [Brief reason] |
| [Segment 3] | **LOW** | [Brief reason] |

**Primary customer groups:**
* [Group 1]
* [Group 2]
* [Group 3]

---
## 2. DETECTED NEEDS

**Critical Market Gaps:**
* [Need 1]
* [Need 2]

**Secondary Market Gaps:**
* [Need 3]

---
## 3. COMPETITIVE LANDSCAPE

| Business Category | Saturation Level | Key Players |
| :--- | :--- | :--- |
| [Category 1] | **HIGH** | [Names] |
| [Category 2] | **MEDIUM** | [Names] |
| [Category 3] | **LOW** | [Names] |

* **Direct competitors:** [X]
* **Indirect competitors:** [Y]
* **Local complaints:** [List top 2-3 themes from reviews, or "Insufficient review evidence"]

---
## 4. OPPORTUNITY & EVIDENCE CHAIN

### [Opportunity Name]
*Recommendation Status: [SUPPORTED / INSUFFICIENT DATA]*

> **Evidence Chain:**
> * **[FACT]:** [Observed fact from data]
> * **[DERIVED]:** [Calculation or density based on data]
> * **[INTERPRETATION]:** [Reasonable interpretation]
> * **[HYPOTHESIS]:** [Possible opportunity requiring validation]

---
## 5. BUSINESS OPTIONS

### #1 [BUSINESS NAME]

- **Business Fit:** [X]/100
- **Evidence Confidence:** [HIGH/MEDIUM/LOW]
- **Capital Intensity:** [HIGH/MEDIUM/LOW]

**Customers:** [Target customers]
**Revenue Streams:** [Stream 1, Stream 2, etc.]

**Why this business?**
[Evidence-based justification]

**Why it may fail (Risks):**
- [Risk 1]
- [Risk 2]

*(Repeat for #2 and #3 if Supported)*

---
## 6. ECONOMIC SNAPSHOT

- **Estimated setup:** [Range]
- **Capital intensity:** [HIGH/MEDIUM/LOW]
- **Budget compatibility:** [HIGH/MEDIUM/LOW or UNKNOWN]

> ⚠ *Preliminary — depends on rent, property and local pricing data.*

---
## 7. WHY NOT OTHER OPTIONS?

- **[Rejected Idea 1]:** [Reason it was rejected based on data]
- **[Rejected Idea 2]:** [Reason it was rejected based on data]

---
## 8. VALIDATION PLAN

**Before investing:**
1. [Specific action]
2. [Specific action]

---
## FINAL INSIGHT

> [One sentence summarizing the most logical path based strictly on evidence]

**Overall Evidence confidence:** [HIGH/MEDIUM/LOW]
"""

    yield f"Initializing connection to {model_name}...\n"
    yield f"Ingesting location context and infrastructure data...\n"
    yield f"Generating strategy blueprint...\n"
    
    if model_name.startswith("gemini"):
        yield from stream_gemini(prompt, api_keys.get('gemini'), model_name)
    elif model_name.startswith("groq-"):
        groq_model = model_name.replace("groq-", "")
        yield from stream_openai_compatible(prompt, api_keys.get('groq'), groq_model, base_url="https://api.groq.com/openai/v1")
    elif model_name.startswith("gpt-"):
        yield from stream_openai_compatible(prompt, api_keys.get('openai'), model_name)
    else:
        # Fallback to local Ollama
        if ollama is None:
            yield "\n\n**API Error:** Ollama SDK is not installed or failed to import."
            return
        response = ollama.chat(
            model=model_name, 
            messages=[{'role': 'user', 'content': prompt}], 
            stream=True
        )
        for chunk in response:
            yield chunk['message']['content']


def headless_web_search(query):
    import urllib.request, urllib.parse
    from html.parser import HTMLParser
    
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.in_snippet = False
                self.current = ""
            def handle_starttag(self, tag, attrs):
                if tag == 'a' and ('class', 'result__snippet') in attrs:
                    self.in_snippet = True
            def handle_endtag(self, tag):
                if tag == 'a' and self.in_snippet:
                    self.in_snippet = False
                    self.results.append(self.current.strip())
                    self.current = ""
            def handle_data(self, data):
                if self.in_snippet:
                    self.current += data + " "
        parser = DDGParser()
        parser.feed(html)
        return "\n- ".join(parser.results[:5])
    except Exception as e:
        return f"Search failed: {str(e)}"

def chat_with_report(report_text, user_message, chat_history, model_name, api_keys):
    api_keys = api_keys or {}
    
    sys_prompt = "You are a strategic AI assistant helping the user analyze this specific market intelligence report. Use the report below as your primary context to answer questions. If the user asks something outside the scope of the report, use your general business knowledge.\n\nREPORT CONTEXT:\n" + report_text
    
    # Agentic web search trigger
    trigger_words = ["search", "scrape", "look up", "find online", "google", "live", "current rent"]
    if any(kw in user_message.lower() for kw in trigger_words):
        yield "> **Agentic Action Triggered**  \n> Spawning web crawler to search live data for your query...  \n"
        search_results = headless_web_search(user_message)
        if search_results and "Search failed" not in search_results:
            yield "> **Web Results Retrieved successfully.** Synthesizing with report context...  \n\n"
            sys_prompt += f"\n\nLIVE WEB DATA RETRIEVED JUST NOW FOR THE USER'S QUERY:\n- {search_results}\n\nINSTRUCTION: Use this live data to formulate your answer if relevant."
        else:
            yield "> **Web Search Failed.** Proceeding with internal knowledge...  \n\n"
    
    prompt = f"{sys_prompt}\n\n"
    for msg in chat_history:
        prompt += f"{msg['role'].upper()}: {msg['content']}\n\n"
    prompt += f"USER: {user_message}\n\nASSISTANT: "
    
    if model_name.startswith("gemini"):
        yield from stream_gemini(prompt, api_keys.get('gemini'), model_name)
    elif model_name.startswith("groq-"):
        groq_model = model_name.replace("groq-", "")
        yield from stream_openai_compatible(prompt, api_keys.get('groq'), groq_model, base_url="https://api.groq.com/openai/v1")
    elif model_name.startswith("gpt-"):
        yield from stream_openai_compatible(prompt, api_keys.get('openai'), model_name)
    else:
        if ollama is None:
            yield "\n\n**API Error:** Ollama SDK is not installed or failed to import."
            return
        response = ollama.chat(model=model_name, messages=[{'role': 'user', 'content': prompt}], stream=True)
        for chunk in response:
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']


def run_multi_agent_pipeline(location_name, infrastructure_data, competitor_data, review_data, property_details=""):
    """
    Orchestrates all 3 models based on their intelligence strengths.
    Automatically handles VRAM swapping by calling them sequentially.
    """
    
    # ---------------------------------------------------------
    # AGENT 1: The Synthesizer (Phi-3 - Fast, lightweight)
    # ---------------------------------------------------------
    yield "Initializing Data Synthesizer (Agent 1)...\n"
    phi_prompt = f"You are a Data Synthesizer. Convert the messy raw scraped data into a clean, highly structured JSON array of competitor objects (with 'name', 'type', and 'context'). Output ONLY valid JSON, do not include markdown formatting or explanations. RAW TEXT: {competitor_data}"
    phi_res = ollama.chat(model='phi3', messages=[{'role': 'user', 'content': phi_prompt}], stream=True)
    
    yield "> **?? Neural Synthesis Log (Agent 1)**  \n> Synthesizing raw DOM scraped data  \n"
    clean_competitors = ""
    for chunk in phi_res:
        content = chunk['message']['content']
        clean_competitors += content
        yield f"THOUGHT_STREAM:{content}"
    yield "THOUGHT_END:"

    # ---------------------------------------------------------
    # AGENT 2: The Analyst (Qwen 2.5 3B - Analytical, logical)
    # ---------------------------------------------------------
    yield "Initializing Market Analyst (Agent 2)...\n"
    qwen_prompt = f"""
    You are a Market Analyst. Based on this infrastructure ({infrastructure_data}) and these existing competitors:
    {clean_competitors}
    
    Identify 3 major market gaps or weaknesses in this area. Do not write a full report, just output the 3 gaps.
    """
    qwen_res = ollama.chat(model='qwen2.5:3b', messages=[{'role': 'user', 'content': qwen_prompt}], stream=True)
    
    yield "> **?? Neural Synthesis Log (Agent 2)**  \n> Performing demographic & market gap analysis  \n"
    market_gaps = ""
    for chunk in qwen_res:
        content = chunk['message']['content']
        market_gaps += content
        yield f"THOUGHT_STREAM:{content}"
    yield "THOUGHT_END:"

    # ---------------------------------------------------------
    # AGENT 3: The Chief Strategist (Llama 3.1 - Deep Reasoning)
    # ---------------------------------------------------------
    yield "Initializing Chief Strategist (Agent 3)...\n"
    
    llama_prompt = f"""
You are the Chief Strategist (Llama 3), an elite enterprise Location Intelligence & Business Feasibility AI.
You are receiving the extracted POI data from Agent 1 (Phi-3) and the theoretical Market Gaps from Agent 2 (Qwen 2.5).

Your core objective is: "Analyze this location and identify unmet, economically plausible customer needs."
Business ideas must be a result of the analysis, not the starting point.
Pipeline: Location → Ecosystem → Customer Segments → Needs → Competition → Gaps → Business Concepts → Economics → Risks → Validation

### ZERO-HALLUCINATION & EVIDENCE POLICY (CRITICAL)
This system is a data-analysis engine, not a creative business-idea generator.
The model MUST distinguish between:
1. Observed facts
2. Deterministic calculations
3. Evidence-based interpretations
4. Hypotheses
Never present a hypothesis or assumption as a fact.

1. SOURCE-BOUND FACTS: Use ONLY information contained in the supplied Market Intelligence dataset. If required information is missing, output "UNKNOWN" or "INSUFFICIENT DATA". Do not guess.
2. MISSING DATA ≠ ABSENCE: Never interpret missing records as proof that something does not exist. Use "not detected in available data" when dataset coverage is incomplete.
3. CALCULATIONS ARE ALLOWED: You may calculate derived metrics ONLY from supplied inputs using transparent formulas (counts, averages, ratios). Do NOT invent the underlying inputs.
4. NO UNSUPPORTED NUMBERS: Never invent room counts, footfall, revenue, margins, or market size unless directly supplied or deterministically calculated.
5. NO FAKE PROBABILITIES: Do not output "86% viability" or "70% opportunity". Use Business Fit Score, Evidence Confidence, and Data Completeness.
6. EVIDENCE TRACEABILITY: Every major recommendation must identify its supporting evidence.
7. CLAIM TYPES: Classify statements as FACT (directly observed), DERIVED (mathematically calculated), INTERPRETATION, or HYPOTHESIS.
8. REVIEW ANALYSIS: Only report customer complaints explicitly supported by review text.
9. COMPETITOR ANALYSIS: "No competitor" does not equal "market gap". A gap requires demand evidence, low competition density, and unmet needs.
10. BUSINESS RECOMMENDATION GATE: Before recommending, verify Customer segment, Demand evidence, Competition evidence, Space compatibility. If critical evidence is missing, state Recommendation Status = INSUFFICIENT DATA.
11. SPECIFICITY: Do not output generic ideas ("Cafe"). Describe target customer, problem, format, revenue streams, differentiator, and risks.
12. WHY THIS BUSINESS: Answer Why this customer? Why this need? Why this location? What evidence supports it?
13. WHY NOT: Identify at least one evidence-based risk or reason the idea may fail.
14. NO ESG FILLER: Do not recommend solar, EV charging, or "smart" features unless supplied data provides a clear business justification.
15. FINANCIAL ANALYSIS: Distinguish between Observed Input, Assumption, and Derived Estimate.
16. UNCERTAINTY: Use High Confidence, Medium Confidence, Low Confidence, or Insufficient Data. Do not use certainty language ("will succeed").
17. COMPLETENESS RULE: You MUST output the ENTIRE Markdown report structure requested below. Do not abort the report. Use the raw POI data to fill out Sections 1, 2, and 3. If you lack sufficient evidence to recommend a business in Sections 4 and 5, output "INSUFFICIENT DATA" for the business name, but still complete the rest of the structural analysis. Do not be overly pessimistic: if the data shows 5 colleges, that IS factual evidence of student demand.

### 1. User's Physical Constraints (PHYSICS LAYER):
{property_details if property_details.strip() else "No specific property constraints provided. Assume a flexible commercial space."}

### 2. Market Intelligence:
Location Query: This analysis is for the user's requested location: {location_name}
Infrastructure: {infrastructure_data}
Competitor Summary (from Agent 1): {clean_competitors}
Market Gaps (from Agent 2): {market_gaps}

### CRITICAL INSTRUCTIONS:
1. Start with `<thought>...</thought>` tags. Evaluate the ecosystem, filter ideas through the Recommendation Gate, and derive metrics.
2. After the thought block, output the final report STRICTLY matching the structure and Markdown formatting below. You MUST use triple backticks for the ASCII bars to preserve spacing.

# MARKET INTELLIGENCE REPORT

**📍 LOCATION**
[Analyze coordinates/data to determine Area]

**AREA PROFILE**
[e.g., Medical + Education + Residential]

---
## 1. LOCAL DEMAND

```text
[Segment 1]          ████████████████  HIGH
[Segment 2]          ████████          MEDIUM
[Segment 3]          ████              LOW
```

**Primary customer groups:**
[Group 1] • [Group 2] • [Group 3]

---
## 2. DETECTED NEEDS

**HIGH**
- [Need 1]
- [Need 2]

**MEDIUM**
- [Need 3]

---
## 3. COMPETITIVE LANDSCAPE

```text
[Category 1]         HIGH competition
[Category 2]         MEDIUM
[Category 3]         LOW
[Category 4]         UNKNOWN
```

- **Direct competitors:** [X]
- **Indirect competitors:** [Y]
- **Local complaints:** [List top 2-3 themes from reviews, or "Insufficient review evidence"]

---
## 4. OPPORTUNITY & EVIDENCE CHAIN

**HIGH-DEMAND + LOW-COMPETITION**
**[Opportunity Name]**
*Recommendation Status: [SUPPORTED / INSUFFICIENT DATA]*

**Why:**
- **[FACT]:** [Observed fact from data]
- **[DERIVED]:** [Calculation or density based on data]
- **[INTERPRETATION]:** [Reasonable interpretation]
- **[HYPOTHESIS]:** [Possible opportunity requiring validation]

---
## 5. BUSINESS OPTIONS

### #1 [BUSINESS NAME]

- **Business Fit:** [X]/100
- **Evidence Confidence:** [HIGH/MEDIUM/LOW]
- **Capital Intensity:** [HIGH/MEDIUM/LOW]

**Customers:** [Target customers]
**Revenue Streams:** [Stream 1, Stream 2, etc.]

**Why this business?**
[Evidence-based justification]

**Why it may fail (Risks):**
- [Risk 1]
- [Risk 2]

*(Repeat for #2 and #3 if Supported)*

---
## 6. ECONOMIC SNAPSHOT

- **Estimated setup:** [Range]
- **Capital intensity:** [HIGH/MEDIUM/LOW]
- **Budget compatibility:** [HIGH/MEDIUM/LOW or UNKNOWN]

> ⚠ *Preliminary — depends on rent, property and local pricing data.*

---
## 7. WHY NOT OTHER OPTIONS?

- **[Rejected Idea 1]:** [Reason it was rejected based on data]
- **[Rejected Idea 2]:** [Reason it was rejected based on data]

---
## 8. VALIDATION PLAN

**Before investing:**
1. [Specific action]
2. [Specific action]

---
## FINAL INSIGHT

> [One sentence summarizing the most logical path based strictly on evidence]

**Overall Evidence confidence:** [HIGH/MEDIUM/LOW]
"""

    # Stream the final output from the smartest available local model directly to the UI
    response = ollama.chat(
        model='llama3.1', 
        messages=[{'role': 'user', 'content': llama_prompt}], 
        stream=True
    )
    
    for chunk in response:
        yield chunk['message']['content']
