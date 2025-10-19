from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import random
import urllib.parse
import os

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Server is working"})

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        # Получаем промпт
        prompt = request.form.get('prompt', '').strip()
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400
        
        print(f"🎯 Получен промпт: {prompt}")
        
        # Простой перевод (инлайн)
        translated_prompt = prompt
        if any(char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in prompt.lower()):
            try:
                # Простой перевод через Google
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=en&dt=t&q={urllib.parse.quote(prompt)}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    translated_prompt = result[0][0][0]
                    print(f"🌐 Переведено: {translated_prompt}")
            except:
                translated_prompt = prompt
        
        # Генерация через Pollinations
        seed = random.randint(1, 1000000)
        final_prompt = f"{translated_prompt} --seed {seed}"
        encoded_prompt = urllib.parse.quote(final_prompt)
        
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        print(f"🚀 Запрос к: {pollinations_url}")
        
        response = requests.get(pollinations_url, timeout=30)
        
        if response.status_code == 200:
            print("✅ Изображение сгенерировано успешно!")
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            print(f"❌ Ошибка Pollinations: {response.status_code}")
            return jsonify({"error": "Ошибка генерации изображения"}), 500
            
    except Exception as e:
        print(f"💥 Критическая ошибка: {str(e)}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
