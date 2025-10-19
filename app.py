from flask import Flask, request, jsonify
# Import all your classes and functions from your original code file
from gemini_market_agent import GeminiAgent, SYSTEM_PROMPT, GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_CX 
# NOTE: You'll need to move the key vars and the system prompt import to the top 
# or ensure they are accessible.

app = Flask(__name__)

# Initialize the agent once globally
try:
    AGENT = GeminiAgent(GEMINI_API_KEY, SYSTEM_PROMPT)
except ValueError as e:
    # Handle missing keys gracefully if hosting requires them
    AGENT = None
    print(f"Agent initialization failed: {e}")

@app.route('/analyze', methods=['GET'])
def analyze():
    if not AGENT:
        return jsonify({"error": "Agent not initialized. API keys missing on server."}), 500
        
    query = request.args.get('q', 'NVIDIA stock')
    use_search = request.args.get('no-search', 'false').lower() not in ('true', 't', '1')

    # The actual call to your market agent logic
    analysis_output = AGENT.ask_market(query, use_search=use_search)
    
    # Return the analysis as a clean JSON response for easy front-end reading
    return jsonify({
        "query": query,
        "search_used": use_search,
        "analysis": analysis_output
    })

if __name__ == '__main__':
    # Use Gunicorn for production-like local testing
    # You will use Gunicorn command on the hosting platform later
    # For quick local testing:
    # app.run(debug=True)
    
    # For deployment, a Procfile will be used (see Step 2)
    pass