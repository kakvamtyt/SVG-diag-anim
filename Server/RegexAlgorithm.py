class ExpressionParser:
    """
    A parser for modifying and normalizing regular expressions by adding dots ('.')
    and handling specific constructs like brackets, alternatives, and scopes.
    """

    def __init__(self, expression, list_id):
        """
        Initialize the ExpressionParser with a given expression.
        """
        self.expression = expression
        self.list_id = list_id
        self.add_dot()
        self.update_comas()

    def add_dot(self):
        """
        Add a dot ('.') between certain characters in the expression.
        """
        modified_expression = "."
        in_brackets = 0
        i = 0
        while i < len(self.expression):
            current_char = self.expression[i]
            modified_expression += current_char
            if current_char in "([{":
                in_brackets += 1
            elif current_char in ")]}":
                in_brackets -= 1
            elif current_char == '|' and in_brackets == 0:
                modified_expression += '.'
            i += 1
        self.expression = modified_expression

    def move_all(self, char):
        """
        Move all instances of a specified character to the front.
        """
        result_expression = ""
        i = 0
        while i < len(self.expression):
            current_char = self.expression[i]
            if current_char == '.':
                if i < len(self.expression) - 1 and self.expression[i + 1] == char:
                    result_expression += char + '.'
                    i += 2
                else:
                    i += 1
            else:
                result_expression += current_char
                i += 1
        self.expression = result_expression

    def update_comas(self):
        """
        Update the expression by repeatedly processing it so that dots ('.')
        are correctly placed.
        """
        expression1 = self._update_comas_extra()
        while expression1 != self.expression:
            self.expression = expression1
            expression1 = self._update_comas_extra()

    def _parse_alternative(self, result_expression, i):
        """
        Handle alternative constructs (e.g., '|') in the expression.
        """
        ever = False
        i += 1
        brackets = 0
        while i < len(self.expression):
            if self.expression[i] in "([{":
                brackets += 1
            if self.expression[i] in ")]}":
                if brackets == 0:
                    if self.expression[i] == "}":
                        while self.expression[i + 1] == "}":
                            result_expression += self.expression[i]
                            i += 1
                            result_expression = self._back_coma_to_start(result_expression, i - 1)
                    result_expression += self.expression[i] + '.'
                    ever = True
                    if self.expression[i] == '}':
                        result_expression = self._back_coma_to_start(result_expression, i - 1)
                    i += 1
                    brackets -= 100
                else:
                    result_expression += self.expression[i]
                    i += 1
                    brackets -= 1
            else:
                result_expression += self.expression[i]
                i += 1
        if not ever:
            result_expression += '.'
        return result_expression

    def _back_coma_to_start(self, result_expression, i):
        """
        Add a dot ('.') before a construct starting with '{'.
        """
        i -= 1
        brackets = 0
        while i > 0:
            if result_expression[i] == '}':
                brackets += 1
            if result_expression[i] == '{':
                if brackets == 0:
                    break
                else:
                    brackets -= 1
            i -= 1
        left_part = result_expression[:i]
        right_part = result_expression[i:]
        result_expression = left_part + '.' + right_part
        return result_expression

    def _remove_duplicate_dots(self, expression):
        """
        Remove consecutive dots ('.') from the expression.
        """
        result = ""
        i = 0
        while i < len(expression):
            if expression[i] == '.' and i + 1 < len(expression) and expression[i + 1] == '.':
                i += 1
            else:
                result += expression[i]
                i += 1
        return result

    def _update_comas_extra(self):
        """
        Process self.expression to ensure proper placement of dots ('.')
        and handle constructs like brackets and alternatives.
        """
        self.in_brackets = 0
        result_expression = ""
        dot_after_scope = 0
        i = 0
        while i < len(self.expression):
            if self.expression[i] == '.':
                if i + 1 >= len(self.expression):
                    result_expression += self.expression[i]
                    i += 1
                    continue
                if self.expression[i + 1] in "])}":
                    self.in_brackets -= 1
                    if self.expression[i + 1] in "])":
                        result_expression += self.expression[i + 1] + self.expression[i]
                        i += 2
                        continue
                    else:
                        result_expression = self._back_coma_to_start(result_expression, i)
                        i += 1
                        while i < len(self.expression) and self.expression[i] == '}':
                            result_expression += self.expression[i]
                            i += 1
                        result_expression += '.'
                        continue
                if self.expression[i] == '.' and self.expression[i + 1] == '|':
                    result_expression = self._parse_alternative(result_expression, i)
                    i = 0
                    self.expression = result_expression
                    result_expression = ""
                    continue
                if self.expression[i + 1] in "([{":
                    self.in_brackets += 1
                    char_start = self.expression[i + 1]
                    char_end = ']' if char_start == '[' else (')' if char_start == '(' else '}')
                    if char_end in "]}":
                        dot_after_scope += 1
                    add_dot = True
                    i += 1
                    in_brackets = -1
                    while i < len(self.expression):
                        result_expression += self.expression[i]
                        if add_dot:
                            result_expression += '.'
                            add_dot = False
                        if self.expression[i] in "([{":
                            in_brackets += 1
                        elif self.expression[i] in ")]}":
                            in_brackets -= 1
                        elif self.expression[i] == '|' and in_brackets == 0:
                            result_expression += '.'
                        if (i + 1 < len(self.expression) and self.expression[i + 1] == char_end) and in_brackets == 0:
                            i += 1
                            break
                        i += 1
                    continue
                else:
                    result_expression += self.expression[i]
                    i += 1
            elif self.expression[i] in ")]}":
                if dot_after_scope > 0:
                    result_expression += self.expression[i] + '.'
                    dot_after_scope -= 1
                else:
                    result_expression += self.expression[i]
                i += 1
            else:
                result_expression += self.expression[i]
                i += 1

        return self._remove_duplicate_dots(result_expression)

    def unique_chars_after_dot(self):
        unique_chars = set()
        for i in range(len(self.expression) - 1):
            if self.expression[i] == '.':
                unique_chars.add(self.expression[i + 1])
        return unique_chars

    def get_expression(self):
        """
        Retrieve the current state of the expression.
        """
        return self.expression

    def get_ids(self):
        needed_ids = []
        i = 0
        y = 0
        while i < len(self.expression):
            if self.expression[i] in "{[(|)]}":
                i += 1
                continue
            if self.expression[i] == '.' and i != len(self.expression) - 1:
                needed_ids.append(self.list_id[y])
                i += 2
                y += 1
            elif self.expression[i] == '.' and i == len(self.expression) - 1:
                needed_ids.append(100)
                i += 1
            else:
                i += 1
                y += 1
        return needed_ids

    def do_cycle(self, symbol):
        """Move dots after symbol and updates their placement. Returns symbol id if its after dot"""

        self.move_all(symbol)
        self.update_comas()
        return self.get_ids()


if __name__ == '__main__':
    parser = ExpressionParser("abc",
                              [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38])
