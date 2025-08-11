import os, sys, re, ast

ISSUE_MESSAGES = {
    "S001": "Too long",
    "S002": "Indentation is not a multiple of four",
    "S003": "Unnecessary semicolon",
    "S004": "At least two spaces required before inline comments",
    "S005": "TODO found",
    "S006": "More than two blank lines used before this line",
    "S007": "Too many spaces after 'class'",
    "S008": "Class name {} should use CamelCase",
    "S009": "Function name {} should use snake_case",
    "S010": "Argument name '{}' should be snake_case",
    "S011": "Variable '{}' in function should be snake_case",
    "S012": "Default argument value is mutable"
}

def check_s001(line, *_):
    return "S001" if len(line) > 79 else None

def check_s002(line, *_):
    spaces = len(line) - len(line.strip(" "))
    if spaces > 0 and spaces % 4 != 0:
        return "S002"
    return None

def check_s003(line, *_):
    idx_hash = line.find('#')
    code = line if idx_hash == -1 else line[:idx_hash]
    if code.rstrip().endswith(';'):
        return "S003"
    return None

def check_s004(line, *_):
    hash_index = line.find("#")
    if hash_index != -1:
        code_part = line[:hash_index]
        if code_part.strip() != "":
            spaces_before = 0
            i = hash_index - 1
            while i >= 0 and line[i] == " ":
                spaces_before += 1
                i -= 1
            if spaces_before < 2:
                return "S004"
    return None

def check_s005(line, *_):
    idx_hash = line.find('#')
    if idx_hash != -1 and "todo" in line[idx_hash+1:].lower():
        return "S005"
    return None

def check_s006(_, blank_count):
    return "S006" if blank_count > 2 else None

def check_s007(line, *_):
    stripped = line.lstrip()
    if re.match(r'^(class|def)\s{2,}', stripped):
        return "S007"
    return None

def check_s008(line, *_):
    if line.lstrip().startswith("class "):
        match = re.match(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', line.lstrip())
        if match:
            class_name = match.group(1)
            if not re.fullmatch(r'[A-Z][a-zA-Z0-9]*', class_name):
                return "S008", class_name
    return None


def check_s009(line, *_):
    if line.lstrip().startswith("def "):
        match = re.match(r'def\s+([A-Za-z_][A-Za-z0-9_]*)', line.lstrip())
        if match:
            func_name = match.group(1)
            if re.fullmatch(r'__\w+__', func_name):
                return None
            if not re.fullmatch(r'_?[a-z0-9]+(_[a-z0-9]+)*_?', func_name):
                return "S009", func_name
    return None

def analyze_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    blank_count = 0
    checks =[check_s001, check_s002, check_s003,
             check_s004, check_s005, check_s006,
             check_s007, check_s008, check_s009]
    all_issues = []

    for line_num, raw in enumerate(lines, start = 1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped == "":
            blank_count += 1
            continue

        issues = []

        s006 = check_s006(line, blank_count)
        if s006:
            issues.append((s006,None))
        blank_count = 0

        for check in checks:
            result = check(line, blank_count)
            if result:
                if isinstance(result, tuple):
                    code, name = result
                    issues.append((code, name))
                else:
                    issues.append((result, None))

        for code, name in sorted(issues):
            if name:
                all_issues.append((line_num, code, name))
            else:
                all_issues.append((line_num, code, None))

    return all_issues

"""
    AST checks(10,11,12)
"""

def is_snake_case(name):
    return re.fullmatch(r'_?[a-z0-9]+(_[a-z0-9]+)*_?', name) is not None

def analyze_ast(file_path):
    with open(file_path, "r") as f:
        code = f.read()
    tree = ast.parse(code)

    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if not is_snake_case(arg.arg):
                    issues.append((node.lineno, "S010", arg.arg))

            mutable_defaults = False
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    mutable_defaults = True
                    break
            if mutable_defaults:
                issues.append((node.lineno, "S012", None))

            found_vars = set()
            for inner_node in ast.walk(node):
                if isinstance(inner_node, ast.Assign):
                    for target in inner_node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if not is_snake_case(var_name) and (inner_node.lineno, var_name) not in found_vars:
                                issues.append((inner_node.lineno, "S011", var_name))
                                found_vars.add((inner_node.lineno, var_name))
    return issues

def process_path(path):
    if os.path.isfile(path) and path.endswith(".py"):
        return [path]
    elif os.path.isdir(path):
        python_files = []

        for root, _ , files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root,file))
        return sorted(python_files)
    return []

def main():
    path = sys.argv[1]
    files = process_path(path)
    if len(files) != 0:
        for file_path in files:
            text_issues = analyze_file(file_path)  # for 1-9 checks

            ast_issues = analyze_ast(file_path)  # for 10-12 checks

            combined = text_issues + ast_issues
            combined.sort(key=lambda x: (x[0], x[1]))

            for line_num, code, name in combined:
                if name:

                    print(f"{file_path}: Line {line_num}: {code} {ISSUE_MESSAGES[code].format(name)}")
                else:
                    print(f"{file_path}: Line {line_num}: {code} {ISSUE_MESSAGES[code]}")

if __name__ == "__main__":
    main()