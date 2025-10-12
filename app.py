# simple_app.py - максимально простой вариант
from flask import Flask, request, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import random

app = Flask(__name__)
CORS(app)

def translate_prompt(text):
    """Простой перевод через DeepSeek"""
    try:
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'user', 'content': f'Translate to English: "{text}"'}
                ],
                'temperature': 0.1
            },
            timeout=20
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip('"')
    except:
        pass
    return text

@app.route('/generate', methods=['POST'])
def generate():
    try:
        prompt = request.form.get('prompt', '')
        edit_mode = request.form.get('edit_mode') == 'true'
        image_file = request.files.get('image')
        
        if edit_mode and image_file:
            # Для img2img добавляем контекст в промпт
            prompt = f"based on uploaded image: {prompt}"
        
        translated = translate_prompt(prompt)
        encoded = urllib.parse.quote(translated)
        
        # Всегда используем Pollinations - самый надежный бесплатный вариант
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&seed={random.randint(1, 1000000)}"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            return {"error": "Generation failed"}, 500
            
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
