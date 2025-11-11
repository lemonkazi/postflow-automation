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
        "2025秋、周りと絶対被らない「モテスウェット」8選",
        "1万円未満で買えちゃう「最強デート服」5選",
        "迷ってそれ着とけば絶対勝てる「大人フーディー」6選",
        "あ、センスあるなと2秒でバレる「最強アウター」7選",
        "女子ウケ確定。「本当に着てほしいニット」はこれ8選",
        "周りと被らない「最強コスパアウター」10選",
        "迷ったらコレで勝てる「シンプルジャケット」5選",
        "1万円以下で「センスある」って思われるスニーカー6選",
        "2025秋、絶対外さない「黒パーカー」最強リスト7",
        "女性が選ぶ「本当に着てほしいスウェット」5選",
        "これ着とけばOK。「無敵の白ロンT」6選",
        "2025秋、ガチで女性ウケする「カーディガン」5選",
        "2秒で“オシャレ”とバレる「最強セットアップ」7選",
        "1万円未満で無双する「高見えアウター」5選",
        "2025秋、女子が二度見する「モテシャツ」8選",
        "迷ったらコレ。女子ウケ確実な「スウェットパンツ」6選",
        "周りと差がつく「最強フーディー」はこの5選",
        "2025秋、絶対勝てる「デートコーデ」7パターン",
        "周りと被らない「最強の黒」アイテム8選",
        "2025秋、最強の「モテスニーカー」6選",
        "1万円以下で揃う「大人の勝負服」5選",
        "あ、清潔感ある。と思われる「白シャツ」最強リスト",
        "周りと被らない「センス最強バッグ」7選",
        "2025秋、女子が好きな「ゆるニット」8選",
        "迷ったらコレ。失敗しない「黒パンツ」5選",
        "ぶっちゃけ、女子は「ロゴ」より「無地」が好き。最強5選",
        "2秒で勝てる「最強の香り（香水）」6選",
        "2025秋、本気でモテる「大人ジャケット」5選",
        "コスパ最強。「高見え」確定のアイテム7選",
        "これが正解。女子ウケ「最強レイヤード」8選",
        "そのパーカー、女子ウケ確定。",
        "結局、女の子は'普通'の白Tが一番好き。",
        "迷ったら、黒の「ちょいゆるスウェット」着とけばOK。",
        "女子は「意外と」シンプルな時計を見てる。",
        "その「とりあえず感」が、逆に最強。",
        "2025秋、そのアウターが正解。",
        "ぶっちゃけ、女子は「細すぎるパンツ」より、ちょいゆる派。",
        "「センスあるな」って思われたいなら、コレ。",
        "そのスニーカー、本気でモテるやつ。",
        "結局、モテる奴は「白」の使い方がうまい。",
        "「なんか雰囲気ある」って思われる人の共通点。",
        "その服、「頼りになりそう」って思われるよ。",
        "ぶっちゃけ、女子は「カバン」で男を判断する。",
        "女子が「守ってあげたい」と思う服装、知ってる？",
        "2025秋、これ着てたら「ガチ勢」確定。",
        "ぶっちゃけ、モテるのに金は要らない。",
        "その「清潔感」、最強の武器になる。",
        "女子は「ギャップ」に弱い。最強フーディーがこれ。",
        "2025秋、これさえあれば無双できる。",
        "そのシンプルさ、2秒で「センスある」ってバレる。"
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
            hooks = _simple_generate(n)
            #hooks = _gemini_generate(n)
                
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