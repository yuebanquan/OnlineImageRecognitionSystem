import os
from flask import Flask, request

import torch
import cv2

app = Flask(__name__)

# 加载 YOLOv7 模型
model = torch.hub.load('ultralytics/yolov5', 'yolov5m', pretrained=True)

# 加载模型类别名称列表
class_names = model.module.names if hasattr(model, 'module') else model.names

@app.route('/analyze_file', methods=['POST'])
def analyze_file():
    # 获取上传的文件
    img = request.files.get("image")
    img.save("./uploads/target.jpg")
    # 加载图片
    img = cv2.imread("./uploads/target.jpg")
    # 将图片转为 RGB 格式
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 使用 YOLOv7 模型进行目标检测
    results = model(img)

    # 解析结果
    objects = []
    for result in results.pandas().xyxy[0].values:
        label = int(result[5])
        score = result[4]
        object_name = class_names[label]
        objects.append((object_name, score))

    # 删除本地保存的文件
    os.remove(os.path.join('./uploads', 'target.jpg'))

    # 返回识别结果
    return {'objects': objects}


if __name__ == "__main__":
    app.run(port=5002, debug=True)
