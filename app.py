from flask import Flask, request, render_template, jsonify # ADDED render_template
# The output is no longer guaranteed to be clean text, so we'll adjust the import 
# to just pull the necessary components
from gemini_market_agent import GeminiAgent, SYSTEM_PROMPT, GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_CX 
import os

app = Flask(__name__)

# Initialize the agent (keep this block the same)
try:
    AGENT = GeminiAgent(GEMINI_API_KEY, SYSTEM_PROMPT)
except ValueError as e:
    AGENT = None
    print(f"Agent initialization failed: {e}")

# Change the output to HTML
@app.route('/analyze', methods=['GET'])
def analyze():
    if not AGENT:
        # If agent failed initialization, still return an error, possibly in JSON or simple HTML
        return f"<h1>Error: Agent not initialized. Check server environment variables.</h1>", 500
        
    query = request.args.get('q', 'Ghost Kitchen Market US Strategy') # Use a default query
    # The JSON output you were getting contained the full analysis string.
    
    # We must ensure all string formatting that was handled by jsonify 
    # is manually done so the HTML template can parse it.
    
    # If using the simplified prompt (TL;DR, Key Facts, Sources), the analysis
    # is returned as a single, multi-line string.
    
    analysis_output = AGENT.ask_market(query, use_search=True) # Always search, or use logic from prompt

    # Pass the variables to the HTML template
    return render_template(
        'analyze.html',
        query=query,
        search_used=True, # Update based on your actual logic
        analysis=analysis_output
    )

if __name__ == '__main__':
    # You can now run this locally with 'flask run' or 'python app.py'
    # and visit http://127.0.0.1:5000/analyze
    app.run(debug=True)