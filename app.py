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
    
    # NEW: The root path now serves the input form
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Change the output to HTML
@app.route('/analyze', methods=['GET'])
def analyze():
    if not AGENT:
        return f"<h1>Error: Agent not initialized. Check server environment variables.</h1>", 500
        
    query = request.args.get('q', 'Ghost Kitchen Market US Strategy')
    # Use the 'no-search' parameter to correctly determine if search was used
    search_used = request.args.get('no-search', 'false').lower() not in ('true', 't', '1') 
    
    analysis_output = AGENT.ask_market(query, use_search=search_used) 

    # --- NEW: String Cleaning for HTML Safety ---
    # 1. Remove all double asterisks (markdown bold) to prevent rendering issues.
    #    The HTML styling will be handled by the template's CSS/structure.
    analysis_output = analysis_output.replace('**', '')
    
    # 2. Add an extra newline after each section header to aid visual parsing in Jinja
    analysis_output = analysis_output.replace('1) Executive Summary', '1) Executive Summary\n')
    analysis_output = analysis_output.replace('2) Key Facts', '2) Key Facts\n')
    analysis_output = analysis_output.replace('3) SWOT', '3) SWOT\n')
    analysis_output = analysis_output.replace('4) Top 3 Strategic Recommendations', '4) Top 3 Strategic Recommendations\n')
    analysis_output = analysis_output.replace('5) Sources', '5) Sources\n')
    # -------------------------------------------

    return render_template(
        'analyze.html',
        query=query,
        search_used=search_used, 
        analysis=analysis_output
    )

if __name__ == '__main__':
    # You can now run this locally with 'flask run' or 'python app.py'
    # and visit http://127.0.0.1:5000/analyze
    app.run(debug=True)