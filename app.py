from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Server is working"})

@app.route('/generate', methods=['POST'])
def generate_image():
    return jsonify({"error": "Service temporarily unavailable"}), 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
