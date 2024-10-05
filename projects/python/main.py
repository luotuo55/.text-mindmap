#####################
# Welcome to Cursor #
#####################
print("开始导入模块...")
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
import plantuml
import io
import logging
import os
from openai import OpenAI
import json
import re

print("模块导入完成")

app = Flask(__name__)
CORS(app)

print("Flask 应用已创建")

# 使用环境变量获取 API 密钥
client = OpenAI(
    api_key="fffff",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 设置日志
logging.basicConfig(level=logging.DEBUG)

# 创建 PlantUML 实例
plantuml_instance = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')

@app.route('/')
def home():
    return render_template('index.html')

def generate_uml_code(text):
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant that generates PlantUML mindmap code. Always start with @startmindmap and end with @endmindmap. Use proper indentation with asterisks (*) for hierarchy.'},
                {'role': 'user', 'content': f'Generate a PlantUML mindmap code for the following text. Ensure the code is properly formatted and only contains valid PlantUML syntax: {text}'}
            ],
        )
        
        # 解析返回的 JSON 字符串
        response_data = json.loads(completion.model_dump_json())
        
        # 提取生成的 UML 代码
        uml_code = response_data['choices'][0]['message']['content']
        return uml_code
    except Exception as e:
        logging.error(f"Error in generate_uml_code: {str(e)}")
        raise

def extract_uml_code(text):
    # 使用正则表达式提取 @startmindmap 和 @endmindmap 之间的内容
    match = re.search(r'@startmindmap(.*?)@endmindmap', text, re.DOTALL)
    if match:
        return f"@startmindmap{match.group(1)}@endmindmap"
    else:
        # 如果没有找到匹配的内容，返回原始文本
        return text

def validate_and_clean_uml(uml_code):
    # 确保代码以 @startmindmap 开始，以 @endmindmap 结束
    uml_code = uml_code.strip()
    if not uml_code.startswith("@startmindmap"):
        uml_code = "@startmindmap\n" + uml_code
    if not uml_code.endswith("@endmindmap"):
        uml_code = uml_code + "\n@endmindmap"
    
    # 移除任何不属于 PlantUML 语法的行
    valid_lines = []
    for line in uml_code.split('\n'):
        line = line.strip()
        if line.startswith(('*', '**', '***', '****', '+', '-')) or \
           line in ('@startmindmap', '@endmindmap') or \
           line.startswith('skinparam'):
            valid_lines.append(line)
    
    # 重新组合有效的行
    cleaned_uml = "\n".join(valid_lines)
    
    # 确保每一行都以正确的缩进开始
    cleaned_uml = re.sub(r'^([*+\-])', r' \1', cleaned_uml, flags=re.MULTILINE)
    
    return cleaned_uml

@app.route('/generate_mindmap', methods=['POST'])
def generate_mindmap():
    try:
        text = request.json['text']
        logging.debug(f"Received text: {text}")
        
        uml_code = generate_uml_code(text)
        logging.debug(f"Generated UML code: {uml_code}")
        
        # 提取实际的 PlantUML 代码
        extracted_uml = extract_uml_code(uml_code)
        logging.debug(f"Extracted UML code: {extracted_uml}")
        
        # 验证和清理 UML 代码
        cleaned_uml = validate_and_clean_uml(extracted_uml)
        logging.debug(f"Cleaned UML code: {cleaned_uml}")
        
        try:
            # 使用清理后的 UML 代码生成图像
            png_data = plantuml_instance.processes(cleaned_uml)
            logging.debug("Image generated successfully")
            
            # 创建一个 BytesIO 对象来存储图像数据
            image_stream = io.BytesIO(png_data)
            image_stream.seek(0)
            
            return send_file(
                image_stream,
                mimetype='image/png',
                as_attachment=True,
                download_name='mindmap.png'
            )
        except plantuml.PlantUMLHTTPError as e:
            logging.error(f"PlantUML HTTP Error: {str(e)}")
            return f"Error generating image: PlantUML HTTP Error - {str(e)}", 500
        except Exception as e:
            logging.error(f"Error processing PlantUML: {str(e)}")
            return f"Error processing PlantUML: {str(e)}", 500
        
    except Exception as e:
        logging.error(f"Error generating mindmap: {str(e)}")
        return f"Error generating mindmap: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)