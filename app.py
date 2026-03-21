#!/usr/bin/env python3
"""西瓜猪开放平台 - 实时数据观测系统"""

import json, time, hashlib, threading, os
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

# 推送配置
PUSH_ENABLED = True
PUSH_INTERVAL_HOURS = 6  # 每6小时推送一次
last_push_time = None

# 加载配置
CONFIG_PATH = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

BASE_URL = CONFIG['api']['baseUrl']
APP_KEY = CONFIG['api']['appKey']
APP_SECRET = CONFIG['api']['appSecret']
MEMBER_ID = CONFIG['api']['memberId']
PORT = CONFIG['server']['port']
INTERVAL = CONFIG['poll']['interval']

# 数据存储
result_data = {'timestamp': None, 'data': None, 'error': None, 'history': []}

def generate_sign(params):
    """生成签名"""
    sign_fields = CONFIG['endpoints']['signFields']
    sorted_items = [(k, params[k]) for k in sign_fields if k in params]
    sorted_items.sort(key=lambda x: x[0])
    s = ''.join(k+str(v) for k,v in sorted_items)
    return hashlib.md5((APP_SECRET+s+APP_SECRET).encode()).hexdigest()

def fetch_data():
    """获取CPS订单数据"""
    timestamp = int(time.time())
    end_time = datetime.now()
    start_time = end_time - timedelta(days=CONFIG['poll']['daysRange'])
    
    sign_params = {
        'endTime': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'offset': CONFIG['params']['offset'],
        'pageSize': CONFIG['params']['pageSize'],
        'queryType': CONFIG['params']['queryType'],
        'startTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': timestamp
    }
    
    params = {**sign_params, 'memberId': MEMBER_ID, 'sign': generate_sign(sign_params)}
    
    try:
        url = f"{BASE_URL}{CONFIG['endpoints']['cpsOrderList']}?appKey={APP_KEY}"
        req = urllib.request.Request(url,
            data=json.dumps(params).encode(),
            headers={'Content-Type':'application/json'},
            method='POST')
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'code': 1, 'message': str(e)}

def push_to_feishu(data):
    """推送订单数据到飞书"""
    global last_push_time
    
    if not PUSH_ENABLED:
        return
    
    # 检查是否到达推送时间
    now = datetime.now()
    if last_push_time:
        hours_passed = (now - last_push_time).total_seconds() / 3600
        if hours_passed < PUSH_INTERVAL_HOURS:
            return
    
    if data.get('code') != 0:
        print(f"[{now.strftime('%H:%M:%S')}] 数据异常，跳过推送")
        return
    
    # data可能是list或dict
    data_body = data.get('data', {})
    if isinstance(data_body, list):
        order_list = data_body
        total = len(data_body)
    else:
        order_list = data_body.get('list', [])
        total = data_body.get('total', 0)
    
    if not order_list:
        print(f"[{now.strftime('%H:%M:%S')}] 无订单数据，跳过推送")
        return
    
    # 构建推送消息
    msg_lines = [
        f"🍉 **西瓜猪订单日报** ({now.strftime('%Y-%m-%d %H:%M')})",
        f"",
        f"📊 **订单统计**：共 {total} 笔订单",
        f"",
        f"📋 **最近订单**："
    ]
    
    for i, order in enumerate(order_list[:5], 1):
        order_id = order.get('orderId', 'N/A')
        amount = order.get('orderAmount', 0)
        commission = order.get('commission', 0)
        status_text = order.get('statusDesc', '未知')
        create_time = order.get('createTime', '')
        
        msg_lines.append(f"{i}. 订单号: `{order_id}`")
        msg_lines.append(f"   金额: ¥{amount} | 佣金: ¥{commission}")
        msg_lines.append(f"   状态: {status_text} | {create_time}")
    
    if total > 5:
        msg_lines.append(f"... 还有 {total - 5} 笔订单")
    
    msg_lines.append("")
    msg_lines.append("📈 数据来源: 西瓜猪开放平台")
    
    message = "\n".join(msg_lines)
    
    # 调用 OpenClaw 的推送接口
    try:
        # 写入推送队列文件，由 OpenClaw heartbeat 处理
        push_file = os.path.expanduser('~/.qclaw/push_queue.json')
        push_data = {
            'channel': 'feishu',
            'message': message,
            'timestamp': now.isoformat()
        }
        
        # 读取现有队列
        queue = []
        if os.path.exists(push_file):
            try:
                with open(push_file, 'r') as f:
                    queue = json.load(f)
            except:
                queue = []
        
        queue.append(push_data)
        
        with open(push_file, 'w') as f:
            json.dump(queue, f, ensure_ascii=False)
        
        last_push_time = now
        print(f"[{now.strftime('%H:%M:%S')}] 📤 已加入推送队列")
        
    except Exception as e:
        print(f"[{now.strftime('%H:%M:%S')}] 推送失败: {e}")

def poll():
    """轮询数据"""
    global result_data
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取数据...")
    
    data = fetch_data()
    entry = {
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'error': None if data.get('code') == 0 else data.get('message'),
        'success': data.get('code') == 0
    }
    
    result_data = entry.copy()
    result_data['history'] = [entry] + result_data.get('history', [])[:99]
    
    status = '✓ 成功' if entry['success'] else f"✗ {entry.get('error', '失败')}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")
    
    # 检查是否需要推送
    push_to_feishu(data)

def polling_loop():
    """轮询循环"""
    poll()
    while True:
        time.sleep(INTERVAL)
        poll()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            self.send_json(result_data)
        elif self.path == '/api/config':
            self.send_json({'memberId': MEMBER_ID, 'port': PORT, 'interval': INTERVAL})
        elif self.path == '/':
            self.serve_html()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/api/refresh':
            poll()
            self.send_json({'ok': True})
    
    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def serve_html(self):
        html_path = os.path.dirname(os.path.abspath(__file__)) + '/public/index.html'
        with open(html_path, 'r') as f:
            html = f.read()
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, fmt, *args): pass

def main():
    t = threading.Thread(target=polling_loop, daemon=True)
    t.start()
    
    print(f'''
╔═══════════════════════════════════════════════════════════╗
║     🍉 西瓜猪开放平台 - 实时数据观测系统                   ║
╠═══════════════════════════════════════════════════════════╣
║  访问地址:  http://localhost:{PORT}                           ║
║  会员ID:   {MEMBER_ID}                                        ║
║  刷新间隔: {INTERVAL}秒                                          ║
╚═══════════════════════════════════════════════════════════╝
    ''')
    
    HTTPServer(('', PORT), Handler).serve_forever()

if __name__ == '__main__':
    main()
