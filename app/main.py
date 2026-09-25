import os
import sys
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from geopy.geocoders import Nominatim

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from maps_scraper import scrape_google_data
from llm_processor import generate_business_strategy_stream

app = FastAPI(title="AI Market Strategist")
geolocator = Nominatim(user_agent="ai_location_app")

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

import shelve

@app.post("/api/analyze")
async def analyze(request: Request):
    data = await request.json()
    location_name = data.get("location")
    model_name = data.get("model", "phi3")
    radius = data.get("radius", "3")
    api_keys = data.get("apiKeys", {})
    
    prop_size = data.get("propertySize", "")
    prop_type = data.get("propertyType", "")
    prop_budget = data.get("budget", "")
    
    prop_details = ""
    if prop_size or prop_type or prop_budget:
        prop_details = f"- Property Size: {prop_size if prop_size else 'Unknown'}\n- Property Type: {prop_type if prop_type else 'Flexible'}\n- Investment Budget: {prop_budget if prop_budget else 'Flexible'}"
    
    cache_key = f"{location_name}_r{radius}_v2"
    
    def event_stream():
        # Step 1: Scrape
        yield f"data: {json.dumps({'status': 'scraping', 'message': f'Booting headless browser & bypassing bot security ({radius}km radius)...'})}\n\n"
        
        try:
            with shelve.open("scrape_cache.db") as db:
                if cache_key in db:
                    yield f"data: {json.dumps({'status': 'scraping', 'message': 'Disk Cache hit! Loaded data instantly...', 'cache_hit': True})}\n\n"
                    scraped_data = db[cache_key]
                else:
                    scraped_data = scrape_google_data(location_name, radius=radius)
                    db[cache_key] = scraped_data

            infra_dict = scraped_data['infrastructure']
            infra_details = scraped_data.get('infrastructure_details', {})
            
            # Combine quantitative counts and qualitative landmarks
            infra_str = "--- QUANTITATIVE SPREAD ---\n"
            infra_str += ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in infra_dict.items()])
            
            infra_str += "\n\n--- QUALITATIVE CONTEXT (Top Landmarks) ---\n"
            for k, v in infra_details.items():
                if v:
                    infra_str += f"- {k.replace('_', ' ').title()}:\n  * " + "\n  * ".join(v) + "\n"
            
            comp_str = "\n".join(scraped_data.get('competitors', []))
            rev_str = "\n".join(scraped_data.get('reviews', []))
            
            # Step 2: Offload to LLM & Send Visual Data
            if model_name == 'multi-agent':
                yield f"data: {json.dumps({'status': 'processing', 'message': 'Scraping complete. Waking Multi-Agent Swarm...'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'processing', 'message': f'Scraping complete. Rendering visuals & waking local {model_name} model...'})}\n\n"
            
            # Send raw numbers for frontend Chart.js rendering
            comp_count = scraped_data.get('competitor_count', 0)
            yield f"data: {json.dumps({'status': 'visuals', 'infrastructure': infra_dict, 'competitors': comp_count })}\n\n"
            
            # Step 3: Stream Strategy
            if model_name == 'multi-agent':
                from llm_processor import run_multi_agent_pipeline
                stream_generator = run_multi_agent_pipeline(location_name, infra_str, comp_str, rev_str, property_details=prop_details)
            else:
                stream_generator = generate_business_strategy_stream(location_name, infra_str, comp_str, rev_str, property_details=prop_details, model_name=model_name, api_keys=api_keys)
                
            buffer = ""
            is_thinking = False
            
            for chunk in stream_generator:
                if chunk.startswith("STATUS:"):
                    yield f"data: {json.dumps({'status': 'processing', 'message': chunk[8:]})}\n\n"
                    continue
                elif chunk.startswith("THOUGHT_START:"):
                    yield f"data: {json.dumps({'status': 'thought_start', 'message': chunk[14:]})}\n\n"
                    continue
                elif chunk.startswith("THOUGHT_STREAM:"):
                    yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': chunk[15:]})}\n\n"
                    continue
                elif chunk.startswith("THOUGHT_END:"):
                    yield f"data: {json.dumps({'status': 'thought_end'})}\n\n"
                    continue
                
                # Tag Parser for Agent 3 (<thought>...</thought>)
                buffer += chunk
                
                if not is_thinking:
                    if "<thought>" in buffer:
                        parts = buffer.split("<thought>")
                        if parts[0]:
                            yield f"data: {json.dumps({'status': 'streaming', 'chunk': parts[0]})}\n\n"
                        is_thinking = True
                        buffer = parts[1]
                        yield f"data: {json.dumps({'status': 'thought_start', 'message': '[Agent 3] Live Reasoning'})}\n\n"
                        if buffer and not buffer.endswith('<') and not "</" in buffer:
                            yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': buffer})}\n\n"
                            buffer = ""
                    elif "<" in buffer:
                        # Prevent hanging indefinitely on normal math equations
                        if len(buffer) - buffer.rfind("<") > 15:
                            yield f"data: {json.dumps({'status': 'streaming', 'chunk': buffer})}\n\n"
                            buffer = ""
                        else:
                            continue
                    else:
                        yield f"data: {json.dumps({'status': 'streaming', 'chunk': buffer})}\n\n"
                        buffer = ""
                else:
                    if "</thought>" in buffer:
                        parts = buffer.split("</thought>")
                        if parts[0]:
                            yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': parts[0]})}\n\n"
                        is_thinking = False
                        buffer = parts[1]
                        yield f"data: {json.dumps({'status': 'thought_end'})}\n\n"
                        if buffer and not buffer.endswith('<') and not "<thought" in buffer:
                            yield f"data: {json.dumps({'status': 'streaming', 'chunk': buffer})}\n\n"
                            buffer = ""
                    elif "</" in buffer or "<" in buffer:
                        if len(buffer) - buffer.rfind("<") > 15:
                            yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': buffer})}\n\n"
                            buffer = ""
                        else:
                            continue
                    else:
                        yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': buffer})}\n\n"
                        buffer = ""
                        
            if buffer:
                if is_thinking:
                    yield f"data: {json.dumps({'status': 'thought_stream', 'chunk': buffer})}\n\n"
                    # Failsafe: if the stream dies while still "thinking", force it closed
                    yield f"data: {json.dumps({'status': 'thought_end'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'streaming', 'chunk': buffer})}\n\n"
                
            yield f"data: {json.dumps({'status': 'complete', 'message': 'Analysis successfully generated.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Pipeline Error: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
