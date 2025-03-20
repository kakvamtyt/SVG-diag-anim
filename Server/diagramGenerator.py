import re
from railroadBib import Diagram, Choice, Sequence, Optional, ZeroOrMore, Terminal, get_terminal_ids


class Token:
    GROUP_START = 'GROUP_START'
    GROUP_END = 'GROUP_END'
    OPTIONAL_START = 'OPTIONAL_START'
    OPTIONAL_END = 'OPTIONAL_END'
    REPETITION_START = 'REPETITION_START'
    REPETITION_END = 'REPETITION_END'
    ALTERNATION = 'ALTERNATION'
    SYMBOL = 'SYMBOL'


def validate_regex_input(regex):
    """
    Validates the input regex:
      - Only allows English letters, digits, and these symbols: ()[]{}|
      - Ensures that every opening bracket has a corresponding closing bracket.
      - Ensures that empty brackets ((), [], {}) are not allowed.
    """
    # Only allow English letters (A-Z, a-z), digits (0-9), and these symbols: ()[]{}|
    if not re.fullmatch(r'[A-Za-z0-9\(\)\[\]\{\}\|]+', regex):
        raise ValueError(
            "Invalid characters in regex. Only English letters, digits, and the symbols ()[]{}| are allowed.")

    # Check for empty brackets: (), [] or {}
    if re.search(r'\(\)', regex):
        raise ValueError("Empty parentheses '()' are not allowed.")
    if re.search(r'\[\]', regex):
        raise ValueError("Empty square brackets '[]' are not allowed.")
    if re.search(r'\{\}', regex):
        raise ValueError("Empty curly braces '{}' are not allowed.")

    # Check for balanced brackets using a simple stack approach
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    for char in regex:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack:
                raise ValueError("Unbalanced brackets: found a closing bracket without a matching opening bracket.")
            last = stack.pop()
            if pairs[last] != char:
                raise ValueError("Unbalanced brackets: mismatched bracket found.")
    if stack:
        raise ValueError("Unbalanced brackets: not all opening brackets are closed.")


def tokenize(regex):
    """Tokenizes the regular expression into tokens."""
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
    """Parses tokens to create diagram components."""
    stack = []
    current = []
    choices = []
    mode_stack = []  # Stack to track the current mode (GROUP, OPTIONAL, REPETITION)

    i = 0
    while i < len(tokens):
        token, value = tokens[i]

        if token == Token.GROUP_START:
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["GROUP"]
        elif token == Token.GROUP_END:
            group = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(group)
                group = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(group)
        elif token == Token.OPTIONAL_START:
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["OPTIONAL"]
        elif token == Token.OPTIONAL_END:
            optional = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(optional)
                optional = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(Optional(optional))
        elif token == Token.REPETITION_START:
            stack.append((current, choices, mode_stack))
            current = []
            choices = []
            mode_stack = ["REPETITION"]
        elif token == Token.REPETITION_END:
            zero_or_more = Sequence(*current) if len(current) > 1 else current[0]
            if choices:
                choices.append(zero_or_more)
                zero_or_more = Choice(0, *choices)
            current, choices, mode_stack = stack.pop()
            current.append(ZeroOrMore(zero_or_more))
        elif token == Token.ALTERNATION:
            if current:
                choices.append(Sequence(*current) if len(current) > 1 else current[0])
            current = []
        elif token == Token.SYMBOL:
            current.append(Terminal(value))

        i += 1

    if current:
        if choices:
            choices.append(Sequence(*current) if len(current) > 1 else current[0])
            return Choice(0, *choices)
        else:
            return Sequence(*current)


def generate_svg_from_regex(regex, output_file="static/diagrams/diagram.svg"):
    validate_regex_input(regex)
    tokens = tokenize(regex)
    diagram = Diagram(parse_tokens(tokens))
    with open(output_file, "w") as f:
        diagram.writeStandalone(f.write)
    return get_terminal_ids(diagram)


if __name__ == '__main__':
    regex = "[a[a|bcg]]ac"
    try:
        ids = generate_svg_from_regex(regex)
        print(ids)
    except Exception as e:
        print("Error:", e)
