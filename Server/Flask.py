from flask import Flask, request, jsonify
import os
import uuid

# Ваши модули:
from actual_version import generate_svg_from_regex
from Algorithm import ExpressionParser

app = Flask(__name__, static_folder='static')

# Папка для хранения диаграмм
OUTPUT_DIR = "static/diagrams"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Глобальные переменные
current_expression = ""
parser = None
needed_ids = []

@app.route('/')
def index():
    """Отдаём HTML-файл (static/index.html)."""
    return app.send_static_file('index.html')


@app.route('/generate-regex', methods=['POST'])
def generate_regex():
    """
    1) Принимает JSON {"diagram_data": "регулярка"}
    2) Генерирует .svg (один раз) и сохраняет в папку static/diagrams
    3) Создаёт парсер ExpressionParser, извлекает:
       - needed_ids (для кружков)
       - available_symbols = unique_chars_after_dot() (для заполнения dropdown)
    4) Возвращает JSON:
       {
         diagram_url: "/static/diagrams/....svg"
         highlight_ids: [...],
         available_symbols: [...]
       }
    """
    try:
        data = request.json.get('diagram_data')
        if not data:
            return jsonify({"error": "No diagram data provided"}), 400

        global parser, current_expression, needed_ids

        # Генерируем один раз SVG
        filename = f"diagram_{uuid.uuid4().hex}.svg"
        output_file = os.path.join(OUTPUT_DIR, filename)
        id_list = generate_svg_from_regex(data, output_file=output_file)

        # Создаём парсер для отслеживания состояния
        parser = ExpressionParser(data, id_list)
        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()

        # Список допустимых символов (чтобы пользователь не вводил неверных)
        available_symbols = list(parser.unique_chars_after_dot())

        return jsonify({
            "diagram_url": f"/static/diagrams/{filename}",
            "highlight_ids": needed_ids,
            "available_symbols": available_symbols
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to generate diagram"}), 500


@app.route('/generate-transition', methods=['POST'])
def generate_transition():
    """
    1) Принимает {"transition": "символ"}
    2) Двигает parser по этому символу,
       - needed_ids = parser.do_cycle(symbol)
       - current_expression = parser.get_expression()
    3) Получает новые available_symbols = unique_chars_after_dot()
    4) Возвращает JSON:
       {
         highlight_ids: [...],
         updated_regex: "...",
         available_symbols: [...]
       }
    """
    try:
        symbol = request.json.get('transition', '')
        if not symbol:
            return jsonify({"error": "No transition provided"}), 400

        global parser, current_expression, needed_ids
        # Делаем шаг
        needed_ids = parser.do_cycle(symbol=symbol)
        current_expression = parser.get_expression()

        # Новый набор доступных символов
        available_symbols = list(parser.unique_chars_after_dot())

        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression,
            "available_symbols": available_symbols
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to update transition"}), 500


if __name__ == '__main__':
    app.run(debug=True)
