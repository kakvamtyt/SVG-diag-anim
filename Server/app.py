import os
import uuid
import logging

from flask import Flask, request, jsonify, session
from Algorithm import ExpressionParser
from actual_version import generate_svg_from_regex

app = Flask(__name__, static_folder='static')
# Secret key for signing session cookies
app.secret_key = os.urandom(24)

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Logging configuration: output to console and file "logs/app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = "static/diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Storage for session state for each session
session_data = {}

@app.before_request
def before_request():
    session.permanent = True
    if 'session_id' not in session:
        session['session_id'] = uuid.uuid4().hex
        logger.info(f"New session created: {session['session_id']}")
    if session['session_id'] not in session_data:
        session_data[session['session_id']] = {}

@app.route('/')
def index():
    logger.info(f"Homepage requested by session: {session.get('session_id')}")
    return app.send_static_file('index.html')

@app.route('/generate-regex', methods=['POST'])
def generate_regex():
    """
    Receives {"diagram_data": "..."}.
    Generates an SVG, creates a parser, and returns:
      - diagram_url
      - highlight_ids
      - available_symbols
      - history (empty array, as there are no transitions yet)
    """
    try:
        data = request.json.get('diagram_data')
        if not data:
            logger.error("No diagram data provided")
            return jsonify({"error": "No diagram data provided"}), 400

        session_id = session.get('session_id')
        logger.info(f"Generating regex for session {session_id} with data: {data}")

        # Generate SVG
        filename = f"diagram_{uuid.uuid4().hex}.svg"
        output_file = os.path.join(OUTPUT_DIR, filename)
        id_list = generate_svg_from_regex(data, output_file=output_file)

        # Create parser
        parser = ExpressionParser(data, id_list)
        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()

        # Save state in session_data
        session_data[session_id] = {
            'parser': parser,
            'current_expression': current_expression,
            'needed_ids': needed_ids,
            'initial_expression': data,
            'initial_id_list': id_list,
            'transitions_history': []
        }

        # Symbols for transitions
        available_symbols = list(parser.unique_chars_after_dot())

        logger.info(f"Regex successfully generated for session {session_id}")
        return jsonify({
            "diagram_url": f"/static/diagrams/{filename}",
            "highlight_ids": needed_ids,
            "available_symbols": available_symbols,
            "history": []
        })
    except Exception as e:
        logger.exception("Error generating diagram")
        return jsonify({"error": "Failed to generate diagram"}), 500

@app.route('/generate-transition', methods=['POST'])
def generate_transition():
    """
    Receives {"transition": "symbol"}.
    Adds a symbol to the history, updates the parser state, and returns the new state.
    """
    try:
        symbol = request.json.get('transition', '')
        if not symbol:
            logger.error("No transition provided")
            return jsonify({"error": "No transition provided"}), 400

        session_id = session.get('session_id')
        state = session_data.get(session_id)
        if not state:
            logger.error("Session state not found")
            return jsonify({"error": "Session state not found"}), 400

        logger.info(f"Processing transition '{symbol}' for session {session_id}")

        parser = state['parser']
        transitions_history = state['transitions_history']

        # Record the transition
        transitions_history.append(symbol)
        needed_ids = parser.do_cycle(symbol)
        current_expression = parser.get_expression()
        available_symbols = list(parser.unique_chars_after_dot())

        # Update state
        state['current_expression'] = current_expression
        state['needed_ids'] = needed_ids
        state['transitions_history'] = transitions_history

        logger.info(f"Transition processed successfully for session {session_id}")
        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols,
            "history": transitions_history
        })
    except Exception as e:
        logger.exception("Error updating transition")
        return jsonify({"error": "Failed to update transition"}), 500

@app.route('/go-back', methods=['POST'])
def go_back():
    """
    Removes the last transition from the history (if any), recreates the parser, and replays the remaining transitions.
    Returns the new state.
    """
    try:
        session_id = session.get('session_id')
        state = session_data.get(session_id)
        if not state:
            logger.error("Session state not found")
            return jsonify({"error": "Session state not found"}), 400

        transitions_history = state['transitions_history']
        if not transitions_history:
            logger.error("No previous state to revert to")
            return jsonify({"error": "No previous state to go back to"}), 400

        logger.info(f"Reverting last transition for session {session_id}")
        # Remove the last transition
        transitions_history.pop()

        # Recreate parser
        initial_expression = state['initial_expression']
        initial_id_list = state['initial_id_list']
        parser = ExpressionParser(initial_expression, initial_id_list)
        for sym in transitions_history:
            parser.do_cycle(sym)

        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()
        available_symbols = list(parser.unique_chars_after_dot())

        # Update state
        state['parser'] = parser
        state['current_expression'] = current_expression
        state['needed_ids'] = needed_ids
        state['transitions_history'] = transitions_history

        logger.info(f"Revert successful for session {session_id}")
        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols,
            "history": transitions_history
        })
    except Exception as e:
        logger.exception("Error reverting transition")
        return jsonify({"error": "Failed to go back"}), 500

if __name__ == '__main__':
    app.run(debug=False)
