# app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "GeneTechAI is running"

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    user_input = data.get("input", "")

    # TEMP: replace this with your real function
    result = f"You sent: {user_input}"

    return jsonify({"result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
