from flask import Flask, render_template, request
import itertools
import re

app = Flask(__name__)

def convert_expression(expr):
    py_expr = expr

    # Replace GeneTech-style logic with Python logic
    py_expr = py_expr.replace(".", " and ")
    py_expr = py_expr.replace("+", " or ")

    # Convert A' to not A
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
        except Exception as e:
            return f"Expression error:\n{e}\n\nConverted expression:\n{py_expr}"

        row = " | ".join(str(v) for v in values) + f" | {output}"
        lines.append(row)

    return "\n".join(lines)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/draw", methods=["POST"])
def draw():
    expression = request.form.get("expression", "")
    max_gates = request.form.get("max_gates", "10")
    max_delay = request.form.get("max_delay", "100.00 s")
    num_circuits = request.form.get("num_circuits", "10")
    order_by = request.form.get("order_by", "delay")

    truth_table = generate_truth_table(expression)

    circuits = (
        "Circuit 1 Logic\n"
        "Circuit 1 SBOL Visual\n\n"
        f"Expression:\n{expression}\n\n"
        f"Max gates: {max_gates}\n"
        f"Max delay: {max_delay}\n"
        f"No. circuits: {num_circuits}\n"
        f"Ordered by: {order_by}\n\n"
        "Status: basic web logic generated successfully."
    )

    return render_template(
        "index.html",
        expression=expression,
        max_gates=max_gates,
        max_delay=max_delay,
        num_circuits=num_circuits,
        order_by=order_by,
        truth_table=truth_table,
        circuits=circuits
    )

@app.route("/natural-language", methods=["POST"])
def natural_language():
    expression = request.form.get("expression", "")

    result = (
        "Natural Language mode selected.\n\n"
        "Next step: connect this button to nlp_groq.py or nlp_local.py.\n\n"
        f"Input:\n{expression}"
    )

    return render_template(
        "index.html",
        expression=expression,
        truth_table=result,
        circuits="NLP output will be converted into a Boolean expression here."
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)