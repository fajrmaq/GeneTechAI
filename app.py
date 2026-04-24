from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run():
    user_input = request.form.get("user_input", "")

    # TEMP for now — later we connect your real GeneTechAI function here
    result = f"GeneTechAI received: {user_input}"

    return render_template("index.html", user_input=user_input, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)