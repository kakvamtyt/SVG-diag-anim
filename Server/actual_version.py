from railroad import Diagram, Choice, Sequence, Optional, ZeroOrMore, Terminal, get_terminal_ids


class Token:
    GROUP_START = 'GROUP_START'
    GROUP_END = 'GROUP_END'
    OPTIONAL_START = 'OPTIONAL_START'
    OPTIONAL_END = 'OPTIONAL_END'
    REPETITION_START = 'REPETITION_START'
    REPETITION_END = 'REPETITION_END'
    ALTERNATION = 'ALTERNATION'
    SYMBOL = 'SYMBOL'


def tokenize(regex):
    """Разделение регулярного выражения на токены."""
    tokens = []
    i = 0
    while i < len(regex):
        char = regex[i]
        if char == '(':
            tokens.append((Token.GROUP_START, char))
        elif char == ')':
            tokens.append((Token.GROUP_END, char))
        elif char == '[':
            tokens.append((Token.OPTIONAL_START, char))
        elif char == ']':
            tokens.append((Token.OPTIONAL_END, char))
        elif char == '{':
            tokens.append((Token.REPETITION_START, char))
        elif char == '}':
            tokens.append((Token.REPETITION_END, char))
        elif char == '|':
            tokens.append((Token.ALTERNATION, char))
        else:
            tokens.append((Token.SYMBOL, char))
        i += 1
    return tokens


def parse_tokens(tokens):
    """Парсер токенов для создания компонентов диаграммы."""
    stack = []
    current = []
    choices = []
    mode_stack = []  # Стек для отслеживания текущего режима (GROUP, OPTIONAL, REPETITION)

    i = 0
    while i < len(tokens):
        token, value = tokens[i]

        if token == Token.GROUP_START:
            # Начало группировки
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["GROUP"]
        elif token == Token.GROUP_END:
            # Конец группировки
            group = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(group)
                group = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(group)
        elif token == Token.OPTIONAL_START:
            # Начало Optional
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["OPTIONAL"]
        elif token == Token.OPTIONAL_END:
            # Конец Optional
            optional = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(optional)
                optional = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(Optional(optional))
        elif token == Token.REPETITION_START:
            # Начало ZeroOrMore
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["REPETITION"]
        elif token == Token.REPETITION_END:
            # Конец ZeroOrMore
            zero_or_more = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(zero_or_more)
                zero_or_more = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(ZeroOrMore(zero_or_more))
        elif token == Token.ALTERNATION:
            # Альтернация
            if current:
                choices.append(Sequence(*current) if len(current) > 1 else current[0])
            current = []
        elif token == Token.SYMBOL:
            # Обычный символ
            current.append(Terminal(value))

        i += 1

    if current:
        if choices:
            choices.append(Sequence(*current) if len(current) > 1 else current[0])
            return Choice(0, *choices)
        else:
            return Sequence(*current)


def generate_svg_from_regex(regex, output_file="static/diagrams/diagram.svg"):
    """Генерация SVG-файла с railroad diagram на основе регулярного выражения."""
    tokens = tokenize(regex)
    print(parse_tokens(tokens))
    diagram = Diagram(parse_tokens(tokens))
    with open(output_file, "w") as f:
        diagram.writeStandalone(f.write)
    print(f"SVG файл сохранен как {output_file}")
    return get_terminal_ids(diagram)


# Пример использования
# regex = "{a|b{abc|aghl}}abc|ab[abc]"
# ids = generate_svg_from_regex(regex)
# print(ids)
