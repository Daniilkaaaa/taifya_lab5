from collections import deque
from typing import Dict, List, Set, Optional

class NodeForRegex:
    """Узел для представления AST регулярного выражения"""
    def __init__(self, val: str, l_child: Optional['NodeForRegex'] = None, r_child: Optional['NodeForRegex'] = None):
        self.val = val
        self.l_child = l_child
        self.r_child = r_child

    def __repr__(self):
        return f"Node({self.val})"

class ParserForRegex:
    """Парсер регулярных выражений с построением AST"""
    SPECIAL_SYMBOLS = {'+', '*', '(', ')', '|'}

    def __init__(self):
        self.token_queue = deque()

    def parse(self, expr: str) -> NodeForRegex:
        """Основной метод парсинга"""
        self.token_queue = deque(expr)
        return self._parse_expr()

    def _parse_expr(self) -> NodeForRegex:
        """Разбор выражения с учётом оператора ИЛИ"""
        left_node = self._parse_term()
        while self.token_queue and self.token_queue[0] == '|':
            self.token_queue.popleft()
            right_node = self._parse_term()
            left_node = NodeForRegex("OR_OP", left_node, right_node)
        return left_node

    def _parse_term(self) -> NodeForRegex:
        """Разбор последовательности терминов"""
        left_node = self._parse_factor()
        while self.token_queue and (self._is_regular_char(self.token_queue[0]) or self.token_queue[0] == '('):
            right_node = self._parse_factor()
            left_node = NodeForRegex("CONCAT_OP", left_node, right_node)
        return left_node

    def _parse_factor(self) -> NodeForRegex:
        """Разбор элементов с операторами * и +"""
        node = self._parse_primary()
        while self.token_queue and (self.token_queue[0] == '*' or self.token_queue[0] == '+'):
            op = "STAR_OP" if self.token_queue.popleft() == '*' else "PLUS_OP"
            node = NodeForRegex(op, node)
        return node

    def _parse_primary(self) -> NodeForRegex:
        """Разбор атомарных элементов и группировок"""
        if not self.token_queue:
            raise ValueError("Неожиданный конец выражения")

        current_token = self.token_queue.popleft()
        if current_token == '\\':
            if not self.token_queue:
                raise ValueError("Отсутствует экранируемый символ")
            esc_char = self.token_queue.popleft()
            if self._is_regular_char(esc_char):
                self.token_queue.appendleft(esc_char)
            else:
                return NodeForRegex(esc_char)

        if self._is_regular_char(current_token):
            return NodeForRegex(current_token)
        elif current_token == '(':
            inner_node = self._parse_expr()
            if not self.token_queue or self.token_queue.popleft() != ')':
                raise ValueError("Несбалансированные скобки")
            return inner_node

        raise ValueError(f"Недопустимый символ: {current_token}")

    def _is_regular_char(self, char: str) -> bool:
        """Проверка на обычный символ (не оператор)"""
        return char not in self.SPECIAL_SYMBOLS

class AutomataState:
    """Состояние НКА"""
    def __init__(self):
        self.char_transitions: Dict[str, List['AutomataState']] = {}
        self.eps_transitions: List['AutomataState'] = []

    def add_char_transition(self, symbol: str, target: 'AutomataState'):
        """Добавление перехода по символу"""
        if symbol not in self.char_transitions:
            self.char_transitions[symbol] = []
        self.char_transitions[symbol].append(target)

    def add_eps_transition(self, target: 'AutomataState'):
        """Добавление ε-перехода"""
        self.eps_transitions.append(target)

class NFA:
    """Недетерминированный конечный автомат"""
    def __init__(self, init_state: AutomataState, final_state: AutomataState):
        self.init_state = init_state
        self.final_state = final_state

class NFABuilder:
    """Построитель НКА по AST"""
    def construct(self, node: NodeForRegex) -> NFA:
        """Основной метод построения НКА"""
        if node.val == "CONCAT_OP":
            return self._build_concat(self.construct(node.l_child), self.construct(node.r_child))
        elif node.val == "OR_OP":
            return self._build_alternation(self.construct(node.l_child), self.construct(node.r_child))
        elif node.val == "STAR_OP":
            return self._build_star(self.construct(node.l_child))
        elif node.val == "PLUS_OP":
            return self._build_plus(self.construct(node.l_child))
        else:
            return self._build_single_char(node.val)

    def _build_single_char(self, char: str) -> NFA:
        """Построение НКА для одиночного символа"""
        s1 = AutomataState()
        s2 = AutomataState()
        s1.add_char_transition(char, s2)
        return NFA(s1, s2)

    def _build_concat(self, first: NFA, second: NFA) -> NFA:
        """Конкатенация двух НКА"""
        first.final_state.add_eps_transition(second.init_state)
        return NFA(first.init_state, second.final_state)

    def _build_alternation(self, first: NFA, second: NFA) -> NFA:
        """Альтернация (ИЛИ) двух НКА"""
        new_start = AutomataState()
        new_end = AutomataState()
        new_start.add_eps_transition(first.init_state)
        new_start.add_eps_transition(second.init_state)
        first.final_state.add_eps_transition(new_end)
        second.final_state.add_eps_transition(new_end)
        return NFA(new_start, new_end)

    def _build_star(self, nfa: NFA) -> NFA:
        """Операция звезды Клини"""
        new_start = AutomataState()
        new_end = AutomataState()
        new_start.add_eps_transition(nfa.init_state)
        new_start.add_eps_transition(new_end)
        nfa.final_state.add_eps_transition(nfa.init_state)
        nfa.final_state.add_eps_transition(new_end)
        return NFA(new_start, new_end)

    def _build_plus(self, nfa: NFA) -> NFA:
        """Операция плюс (одно или более)"""
        new_start = AutomataState()
        new_end = AutomataState()
        new_start.add_eps_transition(nfa.init_state)
        nfa.final_state.add_eps_transition(nfa.init_state)
        nfa.final_state.add_eps_transition(new_end)
        return NFA(new_start, new_end)

class NFAExporter:
    """Экспорт НКА в файл"""
    @staticmethod
    def _assign_state_ids(start_state: AutomataState) -> Dict[AutomataState, str]:
        """Присвоение идентификаторов состояниям"""
        state_ids = {}
        counter = 0
        stack = [start_state]

        while stack:
            current = stack.pop()
            if current not in state_ids:
                state_ids[current] = f"S{counter}"
                counter += 1
                for targets in current.char_transitions.values():
                    for t in targets:
                        if t not in state_ids:
                            stack.append(t)
                for t in current.eps_transitions:
                    if t not in state_ids:
                        stack.append(t)

        return state_ids

    @staticmethod
    def save_to_file(nfa: NFA, filename: str):
        state_ids = NFAExporter._assign_state_ids(nfa.init_state)
        accepting_state = state_ids[nfa.final_state]

        transitions: Dict[str, Dict[str, Set[str]]] = {}
        for state, id_ in state_ids.items():
            transitions[id_] = {}
            for symbol, targets in state.char_transitions.items():
                transitions[id_][symbol] = {state_ids[t] for t in targets}
            if state.eps_transitions:
                transitions[id_]['ε'] = {state_ids[t] for t in state.eps_transitions}

        symbols = set()
        for trans in transitions.values():
            symbols.update(trans.keys())

        with open(filename, 'w', encoding='utf-8') as f:
            # Запись строки с пометками финальных состояний
            f.write(";" + ";".join("1" if s == accepting_state else "0" for s in state_ids.values()) + "\n")
            # Запись строки с идентификаторами состояний
            f.write(";" + ";".join(state_ids.values()) + "\n")

            # Запись переходов для каждого символа
            for symbol in sorted(symbols):
                row = [symbol]
                for state_id in state_ids.values():
                    targets = transitions[state_id].get(symbol, set())
                    row.append(",".join(sorted(targets)))
                f.write(";".join(row) + "\n")

def process_regex(args: List[str]):
    if len(args) < 2:
        print("Использование: python script.py <выходной_файл> <регулярное_выражение>")
        return

    output_file = args[0]
    regex_pattern = args[1]

    try:
        parser = ParserForRegex()
        syntax_tree = parser.parse(regex_pattern)

        builder = NFABuilder()
        nfa_automaton = builder.construct(syntax_tree)

        NFAExporter.save_to_file(nfa_automaton, output_file)
        print(f"НКА успешно сохранён в {output_file}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    import sys
    process_regex(sys.argv[1:])