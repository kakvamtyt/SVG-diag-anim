import os
import uuid

from flask import Flask, request, jsonify

from Algorithm import ExpressionParser
from actual_version import generate_svg_from_regex

app = Flask(__name__, static_folder='static')

OUTPUT_DIR = "static/diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Глобальные переменные
parser = None
current_expression = ""
needed_ids = []

# Исходные данные (нужны для «отката»)
initial_expression = ""
initial_id_list = []
transitions_history = []  # хранит символы: ['a', 'b', ...]


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/generate-regex', methods=['POST'])
def generate_regex():
    """
    Принимает {"diagram_data": "..."}
    Генерирует SVG, создаёт парсер и возвращает:
      - diagram_url
      - highlight_ids
      - available_symbols
      - history (пустой массив, т.к. нет переходов)
    """
    try:
        data = request.json.get('diagram_data')
        if not data:
            return jsonify({"error": "No diagram data provided"}), 400

        global parser, current_expression, needed_ids
        global initial_expression, initial_id_list, transitions_history

        # Генерируем SVG
        filename = f"diagram_{uuid.uuid4().hex}.svg"
        output_file = os.path.join(OUTPUT_DIR, filename)
        id_list = generate_svg_from_regex(data, output_file=output_file)

        # Создаём парсер
        parser = ExpressionParser(data, id_list)
        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()

        # Сохраняем «исходное» состояние
        initial_expression = data
        initial_id_list = id_list
        transitions_history = []

        # Символы для перехода
        available_symbols = list(parser.unique_chars_after_dot())

        return jsonify({
            "diagram_url": f"/static/diagrams/{filename}",
            "highlight_ids": needed_ids,
            "available_symbols": available_symbols,
            "history": transitions_history
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to generate diagram"}), 500


@app.route('/generate-transition', methods=['POST'])
def generate_transition():
    """
    Принимает {"transition": "символ"}
    Добавляет символ в историю, двигает парсер, возвращает новое состояние.
    """
    try:
        symbol = request.json.get('transition', '')
        if not symbol:
            return jsonify({"error": "No transition provided"}), 400

        global parser, current_expression, needed_ids, transitions_history

        # Запоминаем переход
        transitions_history.append(symbol)

        needed_ids = parser.do_cycle(symbol)
        current_expression = parser.get_expression()

        available_symbols = list(parser.unique_chars_after_dot())

        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols,
            "history": transitions_history
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to update transition"}), 500


@app.route('/go-back', methods=['POST'])
def go_back():
    """
    Удаляем последний переход из history (если есть),
    пересоздаём парсер, «проигрываем» оставшиеся переходы.
    Возвращаем новое состояние.
    """
    try:
        global parser, current_expression, needed_ids, transitions_history
        global initial_expression, initial_id_list

        if not transitions_history:
            return jsonify({"error": "No previous state to go back to"}), 400

        # Удаляем последний переход
        transitions_history.pop()

        # Пересоздаём
        parser = ExpressionParser(initial_expression, initial_id_list)
        for sym in transitions_history:
            parser.do_cycle(sym)

        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()
        available_symbols = list(parser.unique_chars_after_dot())

        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols,
            "history": transitions_history
        })
    except Exception as e:
        print("Ошибка при возврате:", e)
        return jsonify({"error": "Failed to go back"}), 500


if __name__ == '__main__':
    app.run(debug=True)
