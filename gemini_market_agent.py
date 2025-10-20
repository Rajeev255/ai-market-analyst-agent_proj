import os
import time
import json
import hashlib
from typing import List, Dict, Optional
import requests
import google.generativeai as genai


# ---------- Config (set env vars or paste direct for prototyping) ----------
# It's recommended to use environment variables for security
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")
SEARCH_RESULTS = 2  # number of search results to fetch

# ---------- Simple file-cache helper to avoid repeated searches during development ----------
CACHE_DIR = ".search_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(q: str) -> str:
    h = hashlib.sha1(q.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")


def cache_get(q: str) -> Optional[Dict]:
    path = _cache_key(q)
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < 3600:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def cache_set(q: str, data: Dict):
    path = _cache_key(q)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- Google Custom Search function ----------
def fetch_search_results(query: str, num: int = SEARCH_RESULTS) -> List[Dict]:
    """
    Uses Google Custom Search JSON API to fetch recent results.
    """
    if not GOOGLE_API_KEY or "PASTE" in GOOGLE_API_KEY or not GOOGLE_CX or "PASTE" in GOOGLE_CX:
        raise ValueError("Please set GOOGLE_API_KEY and GOOGLE_CX. See setup_google_search.md.")

    cached = cache_get(query)
    if cached:
        return cached["items"]

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query, "num": min(num, 10)}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = []
    for it in data.get("items", []):
        items.append({
            "title": it.get("title"), "snippet": it.get("snippet"),
            "link": it.get("link"), "raw": it
        })
    cache_set(query, {"items": items, "fetched_at": time.time()})
    return items


# ---------- Gemini Agent ----------
class GeminiAgent:
    def __init__(self, gemini_api_key: str, system_prompt: str):
        if not gemini_api_key or "PASTE" in gemini_api_key:
            raise ValueError("GEMINI_API_KEY missing. Please add it to the script.")
        genai.configure(api_key=gemini_api_key)
        self.system_prompt = system_prompt
        self.model_name = "gemini-2.5-flash"
        print("Stratosphere initialized.")

    def build_context_from_search(self, search_items: List[Dict]) -> str:
        lines = []
        for i, it in enumerate(search_items, start=1):
            title = (it.get("title") or "")[:200]
            snippet = (it.get("snippet") or "")[:400]
            link = it.get("link") or ""
            lines.append(f"[{i}] {title}\nSnippet: {snippet}\nURL: {link}\n")
        return "\n".join(lines)

    def _call_gemini(self, user_message: str, temperature: float = 0.1, max_tokens: int = 4048) -> str:
        try:
            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(
                [self.system_prompt, user_message],
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            
            if not response.candidates:
                return "(The API returned no candidates. This may be due to a temporary issue.)"
            
            # --- Start FIX area ---
            finish_reason = response.candidates[0].finish_reason
            finish_name = finish_reason.name # Get the name string (e.g., "SAFETY", "RECITATION")
            
            if finish_name == "SAFETY":
                # FinishReason.SAFETY is typically '3'
                return "(Agent response was blocked by safety filters. Try again, or use the '--no-search' flag.)"
            
            if finish_name == "RECITATION":
                # FinishReason.RECITATION is typically '2'
                return "(Agent response was blocked due to potential data recitation. Try modifying your query.)"
                # Handle Max Token Limit 
            if finish_name == "MAX_OUTPUT_TOKENS":
                return "(Generation stopped due to hitting the output token limit. The analysis is incomplete. Consider increasing the max_output_tokens.)"
            # Catch cases where text is empty, such as other policy blocks
            if not response.text:
                return f"(Generation finished with reason: {finish_name}. No text was generated.)"
            # --- End FIX area ---

            # Safely access the text (This line will now be reached only if text exists)
            return response.text.strip()

        except Exception as e:
            return f"(Error calling Gemini API: {e})"

    def ask_market(self, query: str, use_search: bool = True) -> str:
        grounding = ""
        if use_search:
            try:
                print(f"-> Searching for: '{query}'...")
                search_items = fetch_search_results(query)
                if search_items:
                    print(f"-> Found {len(search_items)} sources.")
                    grounding = self.build_context_from_search(search_items)
                else:
                    print("-> WARNING: No search results were found.")
                    grounding = "(No search results found.)"
            except Exception as e:
                print(f"-> ERROR: The search request failed: {e}")
                grounding = f"(Warning: search failed. Analysis will use general knowledge.)"

        user_message = (
            f"User query: {query}\n\n"
            "Use the following RECENT NEWS SNIPPETS as grounding:\n"
            f"{grounding}\n\n"
            "Follow the output format in the system instruction. If sources are insufficient, say so."
        )
        
        print("-> Asking Gemini for analysis...")
        response_text = self._call_gemini(user_message)
        return response_text

# ... (System Prompt remains the same) ...
SYSTEM_PROMPT = """
You are Stratosphere, a world-class, MBA-level Market Analyst assistant.
Your goal is to produce concise, structured, and insightful strategic analyses suitable for executive client briefs.

Primary Directives (Strict Compliance Required):
1.  **Grounding:** Every statement of fact MUST be explicitly drawn from and attributed to the supplied news snippets.
2.  **Safety:** Produce concise analysis. DO NOT engage in financial advice, speculation, or policy-violating content.
3.  **Clarity:** If sources are insufficient to complete a section (e.g., SWOT), state this explicitly, and provide the analysis based on general knowledge, marking the ungrounded insight with **[UNGROUNDED]**.

Output Format (Strict Adherence Required):
1) **Executive Summary** (1-3 lines summarizing the core strategic takeaway.)
2) Key Facts (Bullet list of 3 essential facts, each ending with source index: [1].)
3) SWOT (Strengths / Weaknesses / Opportunities / Threats — 2 strategic, concise bullet point for each category.)
4) Top 3 Strategic Recommendations (Each recommendation must include: Recommendation, Rationale, and Immediate Next Step.)
5) Sources (Numbered list: Title — URL)

Tone: Highly Professional, Concise, and Insightful.
"""

# ---------- CLI ----------
def main_cli():
    # Check for keys at the start
    if any("PASTE" in key for key in [GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_CX]):
        print("ERROR: API keys are not configured. Please paste your keys into the script.")
        return

    agent = GeminiAgent(GEMINI_API_KEY, SYSTEM_PROMPT)

    print("\nEnter a company name to analyze (e.g., 'Apple' or 'NVIDIA stock').")
    print("Add '--no-search' to a query to skip real-time search (e.g., 'Apple --no-search').")
    print("Type 'exit' to quit.")

    while True:
        q_raw = input("\nYou: ").strip()
        if q_raw.lower() in ("exit", "quit"):
            print("Goodbye Take Care!.")
            break
        
        use_search = True
        if "--no-search" in q_raw:
            use_search = False
            q = q_raw.replace("--no-search", "").strip()
        else:
            q = q_raw

        # Basic heuristic: if query short, add "recent news about"
        query_string = f"recent news about {q}" if len(q.split()) <= 4 else q
        
        out = agent.ask_market(query_string, use_search=use_search)
        print("\nAgent response:\n")
        print(out)

if __name__ == "__main__":
    main_cli()

