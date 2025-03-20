import os
import uuid
import time
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, jsonify, session
from graphviz import Source
from RegexAlgorithm import ExpressionParser
from diagramGenerator import generate_svg_from_regex

# Create logs folder if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging with rotation (rotate at midnight, keep 7 backups)
handler = TimedRotatingFileHandler("logs/app.log", when="midnight", interval=1, backupCount=7)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
handler.setFormatter(formatter)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(handler)

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(32)

OUTPUT_DIR = "static/diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def cleanup_diagrams(max_age_days=1):
    """
    Delete diagram files in the static/diagrams folder that are older than max_age_days.
    """
    diagrams_folder = os.path.join(os.getcwd(), "static", "diagrams")
    now = time.time()
    max_age_seconds = max_age_days * 86400  # seconds in a day
    for filename in os.listdir(diagrams_folder):
        file_path = os.path.join(diagrams_folder, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    logging.info("Removed old diagram: %s", file_path)
                except Exception as e:
                    logging.error("Error removing file %s: %s", file_path, e)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/generate-regex', methods=['POST'])
def generate_regex():
    """
    Accepts {"diagram_data": "..."}.
    Generates the diagram, creates the parser, and saves the processed initial state (with dots)
    in the session so that each user has their own isolated state.
    Also cleans up old diagram files.
    """
    try:
        data = request.json.get('diagram_data', '')
        if not data:
            return jsonify({"error": "No diagram data provided"}), 400

        # Cleanup old diagram files (older than 1 day)
        cleanup_diagrams(max_age_days=1)

        filename = f"diagram_{uuid.uuid4().hex}.svg"
        output_file = os.path.join(OUTPUT_DIR, filename)
        # generate_svg_from_regex may raise an exception with a detailed error message
        id_list = generate_svg_from_regex(data, output_file=output_file)

        parser = ExpressionParser(data, id_list)
        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()
        available_symbols = list(parser.unique_chars_after_dot())

        # Save initial state and transitions in session
        session["initial_expression"] = current_expression
        session["initial_id_list"] = id_list
        session["transitions_history"] = []

        return jsonify({
            "diagram_url": f"/static/diagrams/{filename}",
            "highlight_ids": needed_ids,
            "available_symbols": available_symbols,
            "initial_regex": current_expression
        })
    except Exception as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 500

@app.route('/generate-transition', methods=['POST'])
def generate_transition():
    """
    Accepts {"transition": "symbol"}.
    Applies a new transition using the session's stored state, updates it, and returns the new state.
    """
    try:
        symbol = request.json.get('transition', '')
        if not symbol:
            return jsonify({"error": "No transition provided"}), 400

        # Retrieve state from session
        initial_expression = session.get("initial_expression")
        initial_id_list = session.get("initial_id_list")
        transitions_history = session.get("transitions_history", [])

        if initial_expression is None or initial_id_list is None:
            return jsonify({"error": "Session state not found."}), 400

        # Recreate the parser from the initial state and apply previous transitions
        parser = ExpressionParser(initial_expression, initial_id_list)
        for t in transitions_history:
            parser.do_cycle(t)
        # Apply the new transition
        transitions_history.append(symbol)
        parser.do_cycle(symbol)

        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()
        available_symbols = list(parser.unique_chars_after_dot())

        # Update session state
        session["transitions_history"] = transitions_history

        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols
        })
    except Exception as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 500

@app.route('/replay', methods=['POST'])
def replay():
    """
    Accepts {"path": [list of transitions]}.
    Recreates the parser from the initial state using the given path,
    updates the session state, and returns the new state.
    """
    try:
        path = request.json.get('path', [])
        initial_expression = session.get("initial_expression")
        initial_id_list = session.get("initial_id_list")

        if initial_expression is None or initial_id_list is None:
            return jsonify({"error": "Session state not found."}), 400

        parser = ExpressionParser(initial_expression, initial_id_list)
        transitions_history = []
        for sym in path:
            transitions_history.append(sym)
            parser.do_cycle(sym)

        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()
        available_symbols = list(parser.unique_chars_after_dot())

        # Update session state
        session["transitions_history"] = transitions_history

        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols
        })
    except Exception as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 500

@app.route('/render-graph', methods=['POST'])
def render_graph():
    """
    Accepts {"dot": "DOT description"}.
    Renders the GraphViz graph as an SVG and returns the SVG content.
    """
    try:
        dot = request.json.get("dot", "")
        if not dot:
            return jsonify({"error": "No DOT provided"}), 400
        src = Source(dot, format="svg")
        svg = src.pipe().decode("utf-8")
        return jsonify({"svg": svg})
    except Exception as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
