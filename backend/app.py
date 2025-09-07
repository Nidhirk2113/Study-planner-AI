# backend/app.py

import os
from flask import Flask, render_template, request, jsonify
from gemini_client import GeminiClient

app = Flask(__name__, template_folder='../templates')
client = GeminiClient()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = payload.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Check if this is a study plan request
        if any(keyword in user_message.lower() for keyword in ['study plan', 'plan for', 'learn', 'study']):
            # Extract topic from the message
            topic = extract_topic(user_message)
            if topic:
                response_text = client.generate_study_plan(topic)
            else:
                response_text = client.generate_response(user_message)
        else:
            response_text = client.generate_response(user_message)
        
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': 'Error generating response'}), 500

def extract_topic(message):
    """Extract topic from user message"""
    message = message.lower()
    
    # Common patterns for topic extraction
    patterns = [
        'study plan for ',
        'plan for ',
        'learn ',
        'study ',
        'create a plan for ',
        'i want to learn ',
        'help me with '
    ]
    
    for pattern in patterns:
        if pattern in message:
            topic = message.split(pattern, 1)[1].strip()
            # Clean up the topic
            topic = topic.replace('please', '').replace('?', '').strip()
            return topic
    
    # If no pattern matches, assume the whole message is the topic
    return message.strip()

if __name__ == '__main__':
    app.run(debug=True)