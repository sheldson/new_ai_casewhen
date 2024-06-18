from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
def parse_input(input_data, skip_header=False):
    logging.debug(f"Parsing input data: {input_data}")
    mappings = {}
    if isinstance(input_data, list):
        if skip_header:
            input_data = input_data[1:]  # 跳过表头
        for row in input_data:
            if len(row) == 2:
                key, value = row
                if key and value:
                    mappings[str(key).strip()] = str(value).strip()
    else:
        input_data = re.split(r'[，,]', input_data)
        for item in input_data:
            if re.search(r'[:：\s]', item):
                key, value = re.split(r'[:：\s]', item, 1)
                if key and value:
                    mappings[key.strip()] = value.strip()
            else:
                logging.error(f"Line does not contain expected delimiter: {item}")
    logging.debug(f"Parsed mappings: {mappings}")
    return mappings


def generate_case_when_stream(mappings):
    prompt = "Generate a SQL CASE WHEN statement for the following mappings:\n"
    for key, value in mappings.items():
        prompt += f"{key}: {value}\n"
    logging.debug(f"Generated prompt for OpenAI: {prompt}")

    def generate():
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            stream=True,
        )
        try:
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                logging.debug(f"Streamed content: {content}")
                yield content
        except Exception as e:
            logging.error(f"Error generating CASE WHEN statement: {e}")
            yield f"Error generating CASE WHEN statement: {e}"

    return generate()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-case-when', methods=['POST'])
def generate_case_when_endpoint():
    input_data = request.json.get('input')
    input_type = request.json.get('type')
    logging.debug(f"Received input data: {input_data}")
    try:
        skip_header = (input_type == 'upload')  # 仅在上传文件时跳过表头
        mappings = parse_input(input_data, skip_header)
        return Response(generate_case_when_stream(mappings), content_type='text/plain')
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
