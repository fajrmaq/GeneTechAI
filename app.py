import itertools
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="matplotlib-"))
os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="xdg-cache-"))

from flask import Flask, render_template, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
CIRCUITS_FILE = BASE_DIR / "circuits.txt"
USER_FILES_DIR = BASE_DIR / "user_files"
app = Flask(__name__)


def convert_expression(expr):
    py_expr = expr
    py_expr = py_expr.replace(".", " and ")
    py_expr = py_expr.replace("+", " or ")
    py_expr = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)'", r"(not \1)", py_expr)
    return py_expr


def get_variables(expr):
    variables = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    ignore = {"and", "or", "not"}
    return sorted(set(v for v in variables if v not in ignore))


def generate_truth_table(expr):
    variables = get_variables(expr)
    py_expr = convert_expression(expr)

    lines = []
    header = " | ".join(variables + ["Output"])
    lines.append(header)
    lines.append("-" * len(header))

    for values in itertools.product([0, 1], repeat=len(variables)):
        env = dict(zip(variables, [bool(v) for v in values]))

        try:
            output = eval(py_expr, {"__builtins__": {}}, env)
            output = int(bool(output))
        except Exception as exc:
            return f"Expression error:\n{exc}\n\nConverted expression:\n{py_expr}"

        row = " | ".join(str(v) for v in values) + f" | {output}"
        lines.append(row)

    return "\n".join(lines)


def canonicalize_expression(expr):
    expr = expr or ""
    replacements = {
        "’": "'",
        "‘": "'",
        "”": '"',
        "“": '"',
        "`": "'",
        "′": "'",
        "‛": "'",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)

    expr = re.sub(r"(?i)\biptg\b", "IPTG", expr)
    expr = re.sub(r"(?i)\batc\b", "aTc", expr)
    expr = re.sub(r"(?i)\barabinose\b", "Arabinose", expr)
    expr = re.sub(r"(?i)\bnot\b", "!", expr)
    expr = re.sub(r"(?i)\band\b", ".", expr)
    expr = re.sub(r"(?i)\bor\b", "+", expr)
    expr = expr.replace("&", ".").replace("*", ".")
    expr = expr.replace("|", "+")
    expr = re.sub(r'([!~])\s*(IPTG|aTc|Arabinose|a|b|c)\b', r"\2'", expr)
    expr = re.sub(r"\s+", "", expr)
    expr = expr.replace('"', "")

    previous = None
    while previous != expr:
        previous = expr
        expr = re.sub(r"\(([^()+]+)\)", r"\1", expr)

    expr = expr.replace("..", ".")
    expr = expr.replace("++", "+")
    return expr.strip(".+")


def normalize_expression_variables(expr):
    variable_map = {
        "a": "IPTG",
        "b": "aTc",
        "c": "Arabinose",
    }

    def replace_token(match):
        return variable_map.get(match.group(0), match.group(0))

    normalized = re.sub(r"(?<![A-Za-z])(a|b|c)(?![A-Za-z])", replace_token, expr)
    simplified_terms = []

    for raw_term in normalized.split("+"):
        if not raw_term:
            continue

        seen_literals = {}
        ordered_literals = []
        contradictory_term = False

        for literal in raw_term.split("."):
            literal = literal.strip()
            if not literal:
                continue

            base_literal = literal[:-1] if literal.endswith("'") else literal
            polarity = literal.endswith("'")

            if base_literal in seen_literals:
                if seen_literals[base_literal] != polarity:
                    contradictory_term = True
                    break
                continue

            seen_literals[base_literal] = polarity
            ordered_literals.append(literal)

        if not contradictory_term and ordered_literals:
            simplified_terms.append(".".join(ordered_literals))

    return "+".join(simplified_terms)


def expression_candidates(expr):
    candidates = []
    for candidate in [expr, canonicalize_expression(expr)]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    normalized_candidates = []
    for candidate in candidates:
        normalized = normalize_expression_variables(candidate)
        if normalized and normalized not in candidates and normalized not in normalized_candidates:
            normalized_candidates.append(normalized)

    candidates.extend(normalized_candidates)
    return candidates


def parse_max_delay(raw_delay):
    delay_text = (raw_delay or "").strip()
    match = re.search(r"\d+(?:\.\d+)?", delay_text)
    return float(match.group(0)) if match else 100.0


def read_circuits():
    circuits = []
    if not CIRCUITS_FILE.exists():
        return circuits

    content = CIRCUITS_FILE.read_text()
    blocks = content.split("*******************")
    for block in blocks:
        if not block.strip():
            continue

        lines = []
        for line in block.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("*") and "Genetic Circuit" not in line:
                lines.append(line)

        if lines:
            circuits.append(lines)

    return circuits


def summarize_circuits(circuits, expression, used_expression, max_gates, max_delay, num_circuits, order_by):
    lines = [
        f"Expression submitted: {expression}",
        f"Expression used: {used_expression}",
        f"Max gates: {max_gates}",
        f"Max delay: {max_delay}",
        f"No. circuits: {num_circuits}",
        f"Ordered by: {order_by}",
        "",
        f"Generated circuits: {len(circuits)}",
        "",
    ]

    for index, circuit in enumerate(circuits, start=1):
        lines.append(f"Genetic Circuit {index}")
        lines.extend(circuit)
        lines.append("")

    return "\n".join(lines).strip()


def build_generated_links():
    xml_files = sorted(
        USER_FILES_DIR.glob("SBOL File *.xml"),
        key=lambda path: int(re.search(r"(\d+)", path.stem).group(1)) if re.search(r"(\d+)", path.stem) else 0,
    )
    logic_images = sorted(USER_FILES_DIR.glob("Circuit * Logic.png"))
    sbol_images = sorted(USER_FILES_DIR.glob("Circuit * SBOL Visual.png"))

    return {
        "xml_files": [path.name for path in xml_files],
        "logic_images": [path.name for path in logic_images],
        "sbol_images": [path.name for path in sbol_images],
    }


def run_genetech_pipeline(expression, max_gates, max_delay, num_circuits, order_by):
    import Logical_Representation as logic
    import SBOL_File as sbol
    import SBOL_visual as visual
    from main import process

    option = 0 if order_by == "delay" else 1
    attempted = []
    circuits = []
    used_expression = None

    for candidate in expression_candidates(expression):
        if not candidate or candidate in attempted:
            continue
        attempted.append(candidate)
        process(candidate)
        circuits = read_circuits()
        if circuits:
            used_expression = candidate
            break

    if not circuits:
        tried = ", ".join(attempted) if attempted else expression
        raise ValueError(
            "No valid circuits could be generated from that expression. "
            f"Tried: {tried}. "
            "This usually means the current gate library cannot map that Boolean function into available circuits."
        )

    USER_FILES_DIR.mkdir(exist_ok=True)
    sbol.SBOL_File(max_gates, max_delay, option, num_circuits)
    logic.Logical_Representation(max_gates, max_delay, option, num_circuits)
    visual.SBOLv(max_gates, max_delay, option, num_circuits)

    return {
        "used_expression": used_expression,
        "circuits": circuits,
        "truth_table": generate_truth_table(used_expression),
        "circuits_text": summarize_circuits(
            circuits, expression, used_expression, max_gates, max_delay, num_circuits, order_by
        ),
        "generated": build_generated_links(),
    }


def template_context(**overrides):
    context = {
        "expression": "",
        "max_gates": "10",
        "max_delay": "100.00 s",
        "num_circuits": "10",
        "order_by": "delay",
        "truth_table": "",
        "circuits": "",
        "error": "",
        "status": "Ready",
        "xml_files": [],
        "logic_images": [],
        "sbol_images": [],
    }
    context.update(overrides)
    return context


@app.route("/")
def home():
    return render_template("index.html", **template_context())


@app.route("/draw", methods=["POST"])
def draw():
    expression = request.form.get("expression", "")
    max_gates = request.form.get("max_gates", "10")
    max_delay = request.form.get("max_delay", "100.00 s")
    num_circuits = request.form.get("num_circuits", "10")
    order_by = request.form.get("order_by", "delay")

    try:
        result = run_genetech_pipeline(
            expression=expression,
            max_gates=int(max_gates or 10),
            max_delay=parse_max_delay(max_delay),
            num_circuits=int(num_circuits or 10),
            order_by=order_by,
        )
        return render_template(
            "index.html",
            **template_context(
                expression=expression,
                max_gates=max_gates,
                max_delay=max_delay,
                num_circuits=num_circuits,
                order_by=order_by,
                truth_table=result["truth_table"],
                circuits=result["circuits_text"],
                xml_files=result["generated"]["xml_files"],
                logic_images=result["generated"]["logic_images"],
                sbol_images=result["generated"]["sbol_images"],
                status=f"Generated {len(result['circuits'])} circuit(s) using {result['used_expression']}",
            ),
        )
    except Exception as exc:
        return render_template(
            "index.html",
            **template_context(
                expression=expression,
                max_gates=max_gates,
                max_delay=max_delay,
                num_circuits=num_circuits,
                order_by=order_by,
                truth_table=generate_truth_table(canonicalize_expression(expression)) if expression else "",
                circuits="Circuit generation failed.",
                error=str(exc),
                status="Circuit generation failed",
            ),
        )


@app.route("/natural-language", methods=["POST"])
def natural_language():
    expression = request.form.get("expression", "")

    result = (
        "Natural Language mode selected.\n\n"
        "This web app route still needs to be connected to nlp_groq.py or nlp_local.py.\n\n"
        f"Input:\n{expression}"
    )

    return render_template(
        "index.html",
        **template_context(
            expression=expression,
            truth_table=result,
            circuits="NLP output will be converted into a Boolean expression here.",
            status="Natural language route is not connected yet",
        ),
    )


@app.route("/generated/<path:filename>")
def generated_file(filename):
    return send_from_directory(USER_FILES_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
