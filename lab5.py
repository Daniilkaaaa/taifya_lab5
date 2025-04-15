import csv
import sys


class AutomatonExporter:
    @staticmethod
    def save_to_csv(automaton_data, output_path, initial_state):
        input_symbols = AutomatonExporter._collect_input_symbols(automaton_data)

        states_order = [initial_state] + [s for s in automaton_data if s != initial_state]

        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            csv_writer = csv.writer(file, delimiter=';')

            # Write output row
            outputs = [''] + [automaton_data[s]['output'] for s in states_order]
            csv_writer.writerow(outputs)

            # Write header row
            headers = [''] + states_order
            csv_writer.writerow(headers)

            # Write transition rows
            for symbol in sorted(input_symbols):
                row = [symbol]
                for state in states_order:
                    transitions = [
                        t['nextPos']
                        for t in automaton_data[state]['transitions']
                        if t['inputSym'] == symbol
                    ]
                    row.append(','.join(transitions) if transitions else '')
                csv_writer.writerow(row)

        print(f"Automaton data saved to {output_path}")

    @staticmethod
    def _collect_input_symbols(automaton_data):
        symbols = set()
        for state in automaton_data.values():
            for transition in state['transitions']:
                symbols.add(transition['inputSym'])
        return symbols


class RegexParser:
    def __init__(self):
        self.state_id = 1

    def process_pattern(self, pattern):
        return self._parse_alternatives(pattern)

    def _parse_alternatives(self, expression):
        components = []
        current = []
        nesting_level = 0

        for char in expression:
            if char == "(":
                nesting_level += 1
            elif char == ")":
                nesting_level -= 1
            elif char == "|" and nesting_level == 0:
                components.append("".join(current))
                current = []
                continue
            current.append(char)

        components.append("".join(current))

        if len(components) > 1:
            return {
                "type": "OR",
                "first": self._parse_sequence(components[0]),
                "second": self._parse_alternatives("|".join(components[1:]))
            }
        return self._parse_sequence(expression)

    def _parse_sequence(self, expression):
        elements = []
        position = 0

        while position < len(expression):
            if expression[position] == "(":
                end_pos = self._find_matching_parenthesis(expression, position)
                sub_expr = expression[position + 1:end_pos]
                elements.append(
                    self._parse_alternatives(sub_expr) if sub_expr else
                    {"type": "LITERAL", "value": "ε"}
                )
                position = end_pos + 1
            elif expression[position] in "*+":
                if not elements:
                    raise ValueError(f"Invalid operator at position {position}")
                op_type = "STAR" if expression[position] == "*" else "PLUS"
                elements[-1] = {"type": op_type, "child": elements[-1]}
                position += 1
            else:
                elements.append({"type": "LITERAL", "value": expression[position]})
                position += 1

        return self._build_sequence_tree(elements) if len(elements) > 1 else elements[0]

    def _build_sequence_tree(self, elements):
        if len(elements) == 1:
            return elements[0]
        return {
            "type": "CONCAT",
            "first": elements[0],
            "second": self._build_sequence_tree(elements[1:])
        }

    def _find_matching_parenthesis(self, expr, start):
        depth = 1
        for i in range(start + 1, len(expr)):
            if expr[i] == "(":
                depth += 1
            elif expr[i] == ")":
                depth -= 1
                if depth == 0:
                    return i
        raise ValueError("Parentheses mismatch")


class NFABuilder:
    def __init__(self):
        self.state_counter = 1
        self.automaton = {}

    def create_state(self):
        state_id = f"s{self.state_counter}"
        self.state_counter += 1
        return {
            "state": state_id,
            "output": '',
            "transitions": []
        }

    def add_epsilon_transition(self, from_state, to_state):
        self.automaton[from_state]['transitions'].append({
            'inputSym': 'ε',
            'nextPos': to_state
        })

    def construct_from_regex(self, regex_tree):
        start_state = self.create_state()
        final_state = self.create_state()

        self.automaton[start_state['state']] = start_state
        self.automaton[final_state['state']] = final_state

        nfa_data = self._build_nfa(regex_tree, start_state['state'], final_state['state'])

        return nfa_data, start_state['state'], final_state['state']

    def _build_nfa(self, node, entry_point, exit_point):
        if node['type'] == 'LITERAL':
            temp_start = self.create_state()
            temp_end = self.create_state()

            self.automaton[temp_start['state']] = temp_start
            self.automaton[temp_end['state']] = temp_end

            temp_start['transitions'].append({
                'inputSym': node['value'],
                'nextPos': temp_end['state']
            })

            self.add_epsilon_transition(entry_point, temp_start['state'])
            self.add_epsilon_transition(temp_end['state'], exit_point)

            return self.automaton

        elif node['type'] == 'CONCAT':
            middle_state = self.create_state()
            self.automaton[middle_state['state']] = middle_state

            self._build_nfa(node['first'], entry_point, middle_state['state'])
            self._build_nfa(node['second'], middle_state['state'], exit_point)

            return self.automaton

        elif node['type'] == 'OR':
            left_entry = self.create_state()
            left_exit = self.create_state()
            right_entry = self.create_state()
            right_exit = self.create_state()

            self.automaton.update({
                left_entry['state']: left_entry,
                left_exit['state']: left_exit,
                right_entry['state']: right_entry,
                right_exit['state']: right_exit
            })

            self.add_epsilon_transition(entry_point, left_entry['state'])
            self.add_epsilon_transition(entry_point, right_entry['state'])

            self._build_nfa(node['first'], left_entry['state'], left_exit['state'])
            self._build_nfa(node['second'], right_entry['state'], right_exit['state'])

            self.add_epsilon_transition(left_exit['state'], exit_point)
            self.add_epsilon_transition(right_exit['state'], exit_point)

            return self.automaton

        elif node['type'] == 'STAR':
            loop_entry = self.create_state()
            loop_exit = self.create_state()

            self.automaton.update({
                loop_entry['state']: loop_entry,
                loop_exit['state']: loop_exit
            })

            self.add_epsilon_transition(entry_point, loop_entry['state'])
            self.add_epsilon_transition(entry_point, exit_point)

            self._build_nfa(node['child'], loop_entry['state'], loop_exit['state'])

            self.add_epsilon_transition(loop_exit['state'], loop_entry['state'])
            self.add_epsilon_transition(loop_exit['state'], exit_point)

            return self.automaton

        elif node['type'] == 'PLUS':
            loop_entry = self.create_state()
            loop_exit = self.create_state()

            self.automaton.update({
                loop_entry['state']: loop_entry,
                loop_exit['state']: loop_exit
            })

            self.add_epsilon_transition(entry_point, loop_entry['state'])

            self._build_nfa(node['child'], loop_entry['state'], loop_exit['state'])

            self.add_epsilon_transition(loop_exit['state'], loop_entry['state'])
            self.add_epsilon_transition(loop_exit['state'], exit_point)

            return self.automaton


def execute():
    if len(sys.argv) != 3:
        print('Usage: python script.py <output.csv> "<regular_expression>"')
        sys.exit(1)

    output_path = sys.argv[1]
    regex_pattern = sys.argv[2]

    # Parse regular expression
    parser = RegexParser()
    syntax_tree = parser.process_pattern(regex_pattern)

    # Build NFA
    builder = NFABuilder()
    nfa_data, start_state, final_state = builder.construct_from_regex(syntax_tree)

    # Mark final state
    nfa_data[final_state]['output'] = "F"

    # Export to CSV
    AutomatonExporter.save_to_csv(nfa_data, output_path, start_state)


if __name__ == "__main__":
    execute()