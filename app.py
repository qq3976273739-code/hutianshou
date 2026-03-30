from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import uuid
import time
from functools import wraps

app = Flask(__name__)
app.secret_key = "hutianshou_very_niu_666666"

# ====================== 后台账号 ======================
ADMIN_USER = "admin"
ADMIN_PWD = "hutianshou888"

# ====================== 价格配置 ======================
GOODS_PRICE = {
    "normal": 5,
    "premium": 15
}

# ====================== 全局数据 ======================
orders = {}
card_pool = []

# ====================== 防爬虫：请求频率限制 ======================
ip_request_time = {}  # 记录IP最后请求时间
RATE_LIMIT_SECONDS = 1  # 每秒最多1次请求

def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        last = ip_request_time.get(ip, 0)
        if now - last < RATE_LIMIT_SECONDS:
            return jsonify({"code": 429, "msg": "请求过快！疑似爬虫"}), 429
        ip_request_time[ip] = now
        return f(*args, **kwargs)
    return wrapper

# ====================== 防刷：同一订单只能请求1次 ======================
order_requested = set()

def order_once(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        oid = request.json.get("order_id")
        if not oid:
            return jsonify({"code": 400, "msg": "参数错误"}), 400
        if oid in order_requested:
            return jsonify({"code": 403, "msg": "禁止重复请求"}), 403
        order_requested.add(oid)
        return f(*args, **kwargs)
    return wrapper

# ====================== 后台登录校验 ======================
def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("admin_login"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return wrap

# ====================== 前端页面 ======================
INDEX_HTML = """
<!DOCTYPE html>
<meta charset="utf-8">
<title>虎天寿自动发卡网</title>
<style>
    body{background:#111;color:#fff;font-family:Arial;padding:30px}
    .box{max-width:500px;margin:0 auto;background:#222;padding:25px;border-radius:12px}
    .item{margin:15px 0}
    button{padding:10px 20px;background:#0099ff;color:white;border:none;border-radius:6px;cursor:pointer}
    button:disabled{background:#444}
    .pay{margin-top:20px;padding:15px;background:#1a1a1a;border-radius:8px}
    .result{padding:12px;margin-top:10px;border-radius:6px}
</style>

<div class="box">
    <h2>虎天寿发卡网</h2>
    <div class="item">
        <h3>普通卡密 · 5 元</h3>
        <button onclick="buy('normal')">立即购买</button>
    </div>
    <div class="item">
        <h3>高级卡密 · 15 元</h3>
        <button onclick="buy('premium')">立即购买</button>
    </div>

    <div id="payBox" class="pay" style="display:none">
        <h3>应付：<span id="needPrice"></span> 元</h3>
        <p>请足额支付，少付不发卡</p>
        <button id="getBtn" disabled onclick="getCard()">已支付，获取卡密</button>
        <div id="result" style="display:none" class="result"></div>
    </div>
</div>

<script>
let currentOrder = null
async function buy(type) {
    let res = await fetch("/create_order", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({type})
    })
    let d = await res.json()
    currentOrder = d.order_id
    document.getElementById("needPrice").innerText = d.price
    document.getElementById("payBox").style.display = "block"
    setTimeout(()=>{
        document.getElementById("getBtn").disabled = false
    }, 2000)
}

async function getCard() {
    let res = await fetch("/get_card", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({order_id:currentOrder})
    })
    let d = await res.json()
    let r = document.getElementById("result")
    r.style.display = "block"
    r.innerText = d.msg || ("卡密：" + d.card)
    r.style.background = d.code ? "#330000" : "#002200"
}
</script>
"""

# ====================== 后台页面 ======================
ADMIN_HTML = """
<!DOCTYPE html>
<meta charset="utf-8">
<title>后台管理 - 虎天寿发卡</title>
<style>
    body{background:#111;color:#fff;padding:30px;font-family:Arial}
    .box{max-width:700px;margin:0 auto;background:#222;padding:20px;border-radius:10px}
    textarea{width:100%;height:120px;background:#111;color:#fff;padding:10px;border-radius:6px}
    button{padding:8px 16px;background:#00aaff;color:white;border:none;border-radius:6px;margin-top:10px}
    .card-item{padding:8px;background:#1a1a1a;margin:4px 0;border-radius:4px}
</style>

<div class="box">
    <h2>发卡后台管理</h2>
    <h4>批量添加卡密（一行一个）</h4>
    <form method="POST" action="/admin/add_cards">
        <textarea name="cards" placeholder="一行一个卡密"></textarea><br>
        <button>添加卡密</button>
    </form>

    <h4 style="margin-top:30px">当前库存：{{ cards|length }} 张</h4>
    {% for c in cards %}
    <div class="card-item">{{ c }}</div>
    {% endfor %}
</div>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<meta charset="utf-8">
<title>后台登录</title>
<style>
    body{background:#111;color:#fff;padding:50px;font-family:Arial}
    .box{max-width:400px;margin:0 auto;background:#222;padding:20px;border-radius:10px}
    input{width:100%;padding:10px;margin:8px 0;background:#111;color:#fff;border:1px solid #444;border-radius:6px}
    button{padding:10px 20px;background:#00aaff;color:white;border:none;border-radius:6px}
</style>
<div class="box">
    <h2>管理员登录</h2>
    <form method="POST" action="/admin/login">
        <input name="user" placeholder="账号">
        <input name="pwd" type="password" placeholder="密码">
        <button>登录</button>
    </form>
</div>
"""

# ====================== 前台接口 ======================
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/create_order", methods=["POST"])
@rate_limit  # 防爬虫频率限制
def create_order():
    typ = request.json["type"]
    price = GOODS_PRICE[typ]
    oid = str(uuid.uuid4())
    orders[oid] = {"price": price, "paid": False, "card": None}
    return {"order_id": oid, "price": price}

@app.route("/get_card", methods=["POST"])
@rate_limit
@order_once  # 一个订单只能拿一次卡密
def get_card():
    oid = request.json["order_id"]
    order = orders.get(oid)
    if not order:
        return {"code": 404, "msg": "订单不存在"}
    if not order["paid"]:
        return {"code": 403, "msg": "未支付或金额不足，无法发卡"}
    if not card_pool:
        return {"code": 500, "msg": "卡密已售罄"}
    card = card_pool.pop(0)
    order["card"] = card
    return {"card": card}

# ====================== 支付回调 ======================
@app.route("/pay_callback", methods=["POST"])
def pay_callback():
    oid = request.json.get("order_id")
    pay = request.json.get("pay_price", 0)
    order = orders.get(oid)
    if not order:
        return {"code": 404}
    if pay < order["price"]:
        return {"code": 400, "msg": "金额不足"}
    order["paid"] = True
    return {"code": 0, "msg": "支付成功"}

# ====================== 后台 ======================
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template_string(LOGIN_HTML)
    user = request.form.get("user")
    pwd = request.form.get("pwd")
    if user == ADMIN_USER and pwd == ADMIN_PWD:
        session["admin_login"] = True
        return redirect("/admin")
    return "账号或密码错误"

@app.route("/admin")
@admin_required
def admin():
    return render_template_string(ADMIN_HTML, cards=card_pool)

@app.route("/admin/add_cards", methods=["POST"])
@admin_required
def add_cards():
    txt = request.form.get("cards", "")
    for line in txt.strip().splitlines():
        line = line.strip()
        if line and line not in card_pool:
            card_pool.append(line)
    return redirect("/admin")

# ====================== 启动 ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7660)
