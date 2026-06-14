from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # allows the form to talk to this server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

CSV_FILE = "visitors.csv"

# Create the CSV file with headers if it doesn't exist yet
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Time", "Name", "Phone", "Email", "Visit Type"])


@app.route("/register", methods=["POST"])
def register():
    data       = request.json
    name       = data.get("name", "")
    phone      = data.get("phone", "")
    email      = data.get("email", "")
    visit_type = data.get("visit_type", "")
    date       = datetime.now().strftime("%Y-%m-%d")
    time       = datetime.now().strftime("%H:%M")

    # Save to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([date, time, name, phone, email, visit_type])

    print(f"✓ Visitor saved: {name} ({visit_type})")
    return jsonify({"message": "Saved successfully"})


@app.route("/visitors", methods=["GET"])
def get_visitors():
    visitors = []
    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            visitors.append(row)
    return jsonify(visitors)


if __name__ == "__main__":
    app.run(debug=True)
