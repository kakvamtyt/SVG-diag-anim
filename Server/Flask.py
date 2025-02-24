from flask import Flask, request, jsonify
import os
import uuid

# Ваши импорты из "actual_version" и "Algorithm":
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
    Эндпоинт: принимает JSON {"diagram_data": "регулярка"}.
    Генерирует .svg ОДИН РАЗ и возвращает:
      - diagram_url: ссылка на этот .svg
      - highlight_ids: какие терминалы нужно отметить
    """
    try:
        data = request.json.get('diagram_data')
        if not data:
            return jsonify({"error": "No diagram data provided"}), 400

        global parser, current_expression, needed_ids

        # Генерация .svg (единственный раз)
        filename = f"diagram_{uuid.uuid4().hex}.svg"
        output_file = os.path.join(OUTPUT_DIR, filename)
        # Это ваша функция, которая строит диаграмму и сохраняет её в файл,
        # при этом возвращая список ВСЕХ ID терминалов:
        id_list = generate_svg_from_regex(data, output_file=output_file)

        # Создаём парсер, чтобы выяснить, какие ID надо отметить:
        parser = ExpressionParser(data, id_list)
        current_expression = parser.get_expression()
        needed_ids = parser.get_ids()

        return jsonify({
            "diagram_url": f"/static/diagrams/{filename}",
            "highlight_ids": needed_ids
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to generate diagram"}), 500


@app.route('/generate-transition', methods=['POST'])
def generate_transition():
    """
    Эндпоинт для пошаговых переходов:
    Меняем состояние парсера и ВОЗВРАЩАЕМ новый список needed_ids.
    Не перегенерируем .svg!
    """
    try:
        symbol = request.json.get('transition', '')
        if not symbol:
            return jsonify({"error": "No transition provided"}), 400

        global parser, current_expression, needed_ids
        # Меняем состояние
        needed_ids = parser.do_cycle(symbol=symbol)
        current_expression = parser.get_expression()

        # Возвращаем ТОЛЬКО новые ID + текущее выражение
        return jsonify({
            "highlight_ids": needed_ids,
            "updated_regex": current_expression
        })
    except Exception as e:
        print("Ошибка:", e)
        return jsonify({"error": "Failed to update transition"}), 500


if __name__ == '__main__':
    app.run(debug=True)
