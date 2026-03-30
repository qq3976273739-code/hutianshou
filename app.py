from flask import Flask, request, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])

# 这里是配置区，不要写任何注释！！！
MY_CONFIG = {
    "bg_url": "https://i.imgur.com/23C9uNm.jpeg",
    "center_text": "四叶草",
    "qrcode_url": "https://i.imgur.com/E6WlpW2.png",
    "admin_pwd": "wangyiming87"
}

@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /", {"Content-Type":"text/plain"}

@app.route("/")
@limiter.limit("10 per minute")
def index():
    return f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>发卡网</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
    width:100vw;
    height:100vh;
    background:url("{MY_CONFIG['bg_url']}") center/cover no-repeat fixed;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    color:#fff;
    font-family:Microsoft YaHei,sans-serif;
    text-shadow:0 0 10px #000;
}}
.title{{
    font-size:36px;
    margin-bottom:30px;
}}
.qrcode{{
    width:220px;
    height:220px;
    border-radius:12px;
    border:4px solid #fff;
}}
</style>
</head>
<body>
<div class="title">{MY_CONFIG['center_text']}</div>
< img class="qrcode" src="{MY_CONFIG['qrcode_url']}">
</body>
</html>
'''

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "GET":
        return f'''
<h1>修改网站内容</h1>
<form method=post>
    密码：<input name=pwd type=password><br><br>
    壁纸链接：<input name=bg size=60 value="{MY_CONFIG['bg_url']}"><br><br>
    中间文字：<input name=text size=40 value="{MY_CONFIG['center_text']}"><br><br>
    收款码链接：<input name=qr size=60 value="{MY_CONFIG['qrcode_url']}"><br><br>
    <button type=submit>保存</button>
</form>
'''
    if request.form.get("pwd") != MY_CONFIG["admin_pwd"]:
        return "密码错误"
    MY_CONFIG["bg_url"] = request.form.get("bg")
    MY_CONFIG["center_text"] = request.form.get("text")
    MY_CONFIG["qrcode_url"] = request.form.get("qr")
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

# 导出实例
application = app
