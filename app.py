from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'pollinations')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"🎨 Генерируем: {prompt}")
        print(f"🔧 Провайдер: Pollinations.ai")
        
        # Кодируем промпт для URL
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Pollinations.ai API
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        
        response = requests.get(pollinations_url, timeout=60)
        
        print(f"🔹 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ УСПЕХ: Изображение сгенерировано через Pollinations.ai!")
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            return jsonify({"error": f"Ошибка Pollinations.ai: {response.status_code}"}), 500
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
