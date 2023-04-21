from flask import Flask, request, render_template
import requests
import json
import redis
import mysql.connector
import os
import time
from PIL import Image
from datetime import datetime

# 初始化 Flask 应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'  # 上传文件保存的路径

# 初始化 Redis 数据库
redis_client = redis.Redis(host='localhost', port=6379, db=0)
# 设置 Redis 数据库数据过期时间为 1 小时
redis_client.config_set('maxmemory', '1gb')
redis_client.config_set('maxmemory-policy', 'allkeys-lru')
redis_client.config_set('maxmemory-samples', '10')
redis_client.config_set('timeout', '3600')

# 建立一个MySQL数据库连接
mysql_connection = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="root",
    database="ImageOnlineRecognitionSystem"
)


# 定义路由
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/analyze-image', methods=['POST'])
def analyze_image(model_url='http://localhost:5002/analyze_file'):
    # 获取上传的文件
    file = request.files['image']
    # 生成时间戳字符串
    timestamp = str(int(time.time()))
    filename = timestamp + '_' + file.filename
    # 保存上传的文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # 判断是否有同名图片
    if not os.path.exists(file_path):
        file.save(file_path)

    # 加载图片
    files = {'image': open(file_path, "rb")}
    # 把图片传给识别模型
    response = requests.post(model_url, files=files)

    # 解析识别模型反馈的结果
    result = json.loads(response.content)
    insert_log_to_mysql(filename, result['objects'][0][0])  # 将结果日志插入mysql数据库
    return {'result': result['objects'][0][0]}


def insert_log_to_mysql(filename, results):
    # 插入数据
    cursor = mysql_connection.cursor()
    sql = "INSERT INTO logs (filename, results) VALUES (%s, %s)"
    values = (filename, results)
    cursor.execute(sql, values)
    mysql_connection.commit()

    # 查询数据
    cursor.execute("SELECT * FROM logs")
    logs = cursor.fetchall()
    print(logs)

    # 关闭连接
    cursor.close()
    # mysql_connection.close()


@app.route('/query')
def logs():
    # 从 Redis 中查询日志
    logs = []
    for key in redis_client.scan_iter("log:*"):
        log = redis_client.hgetall(key)

    # 从 MySQL 中查询日志
    mysql_cursor = mysql_connection.cursor(dictionary=True)
    mysql_cursor.execute("SELECT * FROM logs")
    mysql_logs = mysql_cursor.fetchall()
    mysql_cursor.close()

    # 更新 Redis 数据库，将 MySQL 中存在但 Redis 中不存在的日志加入 Redis
    for log in mysql_logs:
        key = f"log:{log['filename']}"
        if not redis_client.exists(key):
            # log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')    # 将 datetime 类型转换为字符串
            redis_client.hmset(key, log)

    # 将 Redis 和 MySQL 中的日志合并
    logs += mysql_logs
    # logs = {"data": logs}
    # print(logs)

    # 返回渲染后的 HTML 页面
    return render_template('query.html', logs=logs)


@app.route('/logs/<filename>', methods=['DELETE'])
def delete_log(filename):
    # 删除 MySQL 中的日志
    cursor = mysql_connection.cursor()
    # print(filename)
    # print(type(filename))
    cursor.execute('DELETE FROM logs WHERE filename = "' + filename + '"')
    mysql_connection.commit()
    cursor.close()

    # 如果 Redis 中存在该日志，则删除
    key = f'log:{filename}'
    if redis_client.exists(key):
        redis_client.delete(key)

    return {'message': f'日志 {filename} 删除成功'}


if __name__ == '__main__':
    app.run(debug=True)
    redis_client.close()
    mysql_connection.close()
