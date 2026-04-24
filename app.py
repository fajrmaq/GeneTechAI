from flask import Flask, render_template, request

app = Flask(__name__)

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

    truth_table = f"Input expression:\n{expression}\n\nMax gates: {max_gates}\nMax delay: {max_delay}\nNo. circuits: {num_circuits}"
    circuits = f"Circuit mapping output will appear here.\nOrdered by: {order_by}"

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
    result = f"Natural language processing output will appear here.\nInput:\n{expression}"
    return render_template("index.html", expression=expression, truth_table=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)