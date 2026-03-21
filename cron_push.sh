#!/bin/bash
cd ~/.qclaw/workspace/xiguazhu-monitor

# 获取订单数据并推送
python3 << 'PYEOF'
import json, time, hashlib, os, urllib.request
from datetime import datetime, timedelta

with open('config.json', 'r') as f:
    CONFIG = json.load(f)

BASE_URL = CONFIG['api']['baseUrl']
APP_KEY = CONFIG['api']['appKey']
APP_SECRET = CONFIG['api']['appSecret']
MEMBER_ID = CONFIG['api']['memberId']

def generate_sign(params):
    sign_fields = CONFIG['endpoints']['signFields']
    sorted_items = [(k, params[k]) for k in sign_fields if k in params]
    sorted_items.sort(key=lambda x: x[0])
    s = ''.join(k+str(v) for k,v in sorted_items)
    return hashlib.md5((APP_SECRET+s+APP_SECRET).encode()).hexdigest()

timestamp = int(time.time())
end_time = datetime.now()
start_time = end_time - timedelta(days=7)

sign_params = {
    'endTime': end_time.strftime('%Y-%m-%d %H:%M:%S'),
    'offset': 0, 'pageSize': 20, 'queryType': 1,
    'startTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
    'timestamp': timestamp
}
params = {**sign_params, 'memberId': MEMBER_ID, 'sign': generate_sign(sign_params)}

url = f"{BASE_URL}/cps/cpsOrder/list?appKey={APP_KEY}"
req = urllib.request.Request(url, data=json.dumps(params).encode(),
    headers={'Content-Type':'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f"Error: {e}")
    exit(1)

if data.get('code') != 0:
    print(f"API Error: {data.get('message')}")
    exit(1)

orders = data.get('data', [])
total = len(orders)
now = datetime.now()

lines = [f"🍉 **西瓜猪订单日报**", f"📅 {now.strftime('%Y-%m-%d %H:%M')}", "", f"📊 **统计**: 共 {total} 笔订单", "", "📋 **最近订单**:"]

for i, o in enumerate(orders[:5], 1):
    order_sn = o.get('orderSn', 'N/A')
    pay_price = o.get('payPrice', 0)
    status = o.get('statusDesc', '未知')
    order_time = o.get('orderTime', '')  # 订单时间
    modified_time = o.get('modifiedTime', '')  # 修改时间
    
    lines.extend(["", f"**{i}. {order_sn}**",
        f"   💰 ¥{pay_price} | 📌 {status}",
        f"   🕐 下单: {order_time}"])

if total > 5:
    lines.extend(["", f"_... 还有 {total-5} 笔_"])

msg = "\n".join(lines)

# 推送到飞书
push_file = os.path.expanduser('~/.openclaw/push_queue.json')
os.makedirs(os.path.dirname(push_file), exist_ok=True)
push_data = {'channel': 'feishu', 'target': 'ou_273ba0b3d0626a9972aabad570f9ad5a', 'message': msg, 'timestamp': now.isoformat()}

queue = []
if os.path.exists(push_file):
    try:
        with open(push_file, 'r') as f:
            queue = json.load(f)
    except:
        queue = []
queue.append(push_data)
with open(push_file, 'w') as f:
    json.dump(queue, f, ensure_ascii=False, indent=2)

print(f"Push queued: {now}")
PYEOF
