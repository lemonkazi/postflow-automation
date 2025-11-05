import os
import json
import requests
from datetime import datetime
from kjc_cli import config
from kjc_cli.logger import get_logger
from kjc_cli.utils import save_json


logger = get_logger("hook_generator")

# Try to import Gemini
try:
    import google.generativeai as genai
except Exception:
    genai = None

OUT_JSON = config.HOOKS_DIR / f"hooks_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"

def _simple_generate(n=10):
    hooks = []
    templates = [
        "This new find will change how you {topic} — here's why.",
        "Why {topic} is the next big thing — and how to jump in.",
        "I tried {topic} once and the result surprised me.",
        "Stop scrolling. Here's {topic} that works right now.",
        "Little-known trick to make {topic} look premium."
    ]
    for i in range(n):
        hooks.append(templates[i % len(templates)].format(topic="stylish threads"))
    return hooks


def _gemini_generate(n=10):
    """Generate hooks using Gemini API directly"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
    
    prompt = f"Write {n} short (max 60 characters) marketing hooks that spark curiosity for fashion product posts. Provide ONLY a JSON array of strings, no other text."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean and parse the response
        text = text.strip().replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback parsing
            lines = [line.strip().strip('"').strip("'") for line in text.splitlines() if line.strip()]
            return [line for line in lines if len(line) > 10]
    else:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
def run_generate(n=10):
    logger.info("Generating hooks")
    hooks = []
    
    # Try Gemini first
    if config.GEMINI_API_KEY:
        try:
            #hooks = _simple_generate(n)
            hooks = _gemini_generate(n)
                
        except Exception as e:
            logger.exception("Gemini call failed, falling back to template generator")
            hooks = _simple_generate(n)
    
    # Fallback to OpenAI if Gemini not available
    elif config.OPENAI_API_KEY and openai:
        try:
            openai.api_key = config.OPENAI_API_KEY
            prompt = f"Write {n} short (max 60 chars) marketing hooks that spark curiosity for fashion product posts. Provide as JSON array."
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini" if hasattr(openai, "ChatCompletion") else "gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=400,
                temperature=0.8
            )
            text = resp.choices[0].message.content
            try:
                arr = json.loads(text)
                if isinstance(arr, list):
                    hooks = arr
            except Exception:
                hooks = [l.strip() for l in text.splitlines() if l.strip()]
        except Exception as e:
            logger.exception("OpenAI call failed, falling back to template generator")
            hooks = _simple_generate(n)
    else:
        hooks = _simple_generate(n)
    
    save_json(OUT_JSON, hooks)
    logger.info(f"Saved {len(hooks)} hooks to {OUT_JSON}")
    return hooks