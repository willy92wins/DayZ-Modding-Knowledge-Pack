import re


PARAMS_READ_CONTEXT_PARAM_RE = re.compile(r"^\s*ParamsReadContext\s+(?P<name>\w+)\b")


METHOD_SIGNATURE_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?:override\s+|static\s+|protected\s+|private\s+)*"
    r"(?P<return_type>\w[\w\s]*?)\s+"
    r"(?P<name>\w+)"
    r"\s*\((?P<params>[^)]*)\)"
    r"\s*(?P<brace>\{)?.*$"
)


def count_braces(line):
    return line.count("{") - line.count("}")


def collect_method_signature(lines, start_index):
    signature = lines[start_index]
    end_index = start_index
    open_parens = signature.count("(")
    close_parens = signature.count(")")

    while open_parens > close_parens and end_index + 1 < len(lines):
        end_index += 1
        next_line = lines[end_index].strip()
        signature = signature + " " + next_line
        open_parens += next_line.count("(")
        close_parens += next_line.count(")")

    return signature, end_index


def find_block_end_line(lines, brace_line_index, max_line_index=None):
    if max_line_index is None:
        max_line_index = len(lines) - 1

    balance = 0
    seen_open = False
    for index in range(brace_line_index, max_line_index + 1):
        line = lines[index]
        if "{" in line:
            seen_open = True
        balance += count_braces(line)
        if seen_open and balance <= 0:
            return index + 1

    return max_line_index + 1


def find_signature_brace_line(lines, signature_index, signature_end_index, match):
    if match.group("brace"):
        for index in range(signature_index, signature_end_index + 1):
            if "{" in lines[index]:
                return index
        return signature_end_index

    for index in range(signature_end_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "":
            continue
        if stripped.startswith("{"):
            return index
        return None

    return None


def find_method_regions(stripped_source):
    lines = stripped_source.split("\n")
    methods = []
    index = 0

    while index < len(lines):
        signature, signature_end_index = collect_method_signature(lines, index)
        match = METHOD_SIGNATURE_RE.match(signature)
        if not match:
            index += 1
            continue

        brace_line_index = find_signature_brace_line(
            lines, index, signature_end_index, match
        )
        if brace_line_index is None:
            index += 1
            continue

        end_line = find_block_end_line(lines, brace_line_index)
        methods.append(
            {
                "start_line": index + 1,
                "end_line": end_line,
                "brace_line": brace_line_index + 1,
                "return_type": " ".join(match.group("return_type").split()),
                "name": match.group("name"),
                "params": match.group("params"),
            }
        )
        index = end_line

    return methods


def find_method_for_line(methods, line_number):
    containing = [
        method
        for method in methods
        if method["start_line"] <= line_number <= method["end_line"]
    ]
    if not containing:
        return None
    return max(containing, key=lambda method: method["start_line"])


def find_params_read_context_param_name(method):
    if method is None:
        return None
    for param in method["params"].split(","):
        match = PARAMS_READ_CONTEXT_PARAM_RE.match(param.strip())
        if match:
            return match.group("name")
    return None


def first_param_is_params_read_context(method):
    if method is None:
        return False
    first_param = method["params"].split(",", 1)[0].strip()
    return PARAMS_READ_CONTEXT_PARAM_RE.match(first_param) is not None


def method_is_onstoreload(method):
    if method is None:
        return False
    if method["name"] != "OnStoreLoad":
        return False
    if method["return_type"] != "bool":
        return False
    return first_param_is_params_read_context(method)


def method_is_onrpc(method):
    if method is None:
        return False
    return method["name"] == "OnRPC" and method["return_type"] == "void"


def find_next_nonblank_line(lines, start_index, max_index):
    for index in range(start_index, max_index + 1):
        if lines[index].strip() != "":
            return index
    return None


def find_if_body_range(lines, if_line_index, method_end_index):
    line = lines[if_line_index]
    if "{" in line:
        return if_line_index + 1, find_block_end_line(
            lines, if_line_index, method_end_index
        )

    close_paren = line.rfind(")")
    if close_paren != -1 and line[close_paren + 1 :].strip() != "":
        return if_line_index + 1, if_line_index + 1

    next_index = find_next_nonblank_line(lines, if_line_index + 1, method_end_index)
    if next_index is None:
        return if_line_index + 1, if_line_index + 1

    if "{" in lines[next_index]:
        return if_line_index + 1, find_block_end_line(
            lines, next_index, method_end_index
        )

    return next_index + 1, next_index + 1


def find_inline_pattern_line(pattern, lines, line_index):
    if pattern.search(lines[line_index]):
        return line_index
    if line_index == 0:
        return None
    combined = lines[line_index - 1] + " " + lines[line_index]
    if pattern.search(combined):
        return line_index - 1
    return None
