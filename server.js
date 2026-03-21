/**
 * 西瓜猪开放平台 - 实时数据观测系统
 * 主服务器 - 支持实时数据轮询和WebSocket推送
 */

const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const path = require('path');
const CONFIG = require('./config');
const { buildSignedParams, generateSign } = require('./utils/signature');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// 存储所有连接的WebSocket客户端
const clients = new Set();

// 数据存储
let latestData = {
  timestamp: null,
  data: null,
  error: null,
  history: []
};

// 初始化历史记录（保留最近100条）
const MAX_HISTORY = 100;

// API调用函数
async function fetchDataFromAPI(endpoint, params) {
  const url = `${CONFIG.API.BASE_URL}${endpoint}`;
  const signedParams = buildSignedParams(params, CONFIG.API.APP_SECRET);
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'appKey': CONFIG.API.APP_KEY
      },
      body: JSON.stringify(signedParams)
    });
    
    const result = await response.json();
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// 轮询数据
async function pollData() {
  console.log(`[${new Date().toISOString()}] 正在获取数据...`);
  
  // 示例: 获取会员数据 - 请根据实际API修改
  const params = {
    memberId: CONFIG.API.MEMBER_ID
  };
  
  const result = await fetchDataFromAPI('/member/info', params);
  
  const dataEntry = {
    timestamp: new Date().toISOString(),
    ...result
  };
  
  // 更新最新数据
  latestData.timestamp = dataEntry.timestamp;
  latestData.data = result.success ? result.data : null;
  latestData.error = result.success ? null : result.error;
  
  // 添加到历史记录
  latestData.history.push(dataEntry);
  if (latestData.history.length > MAX_HISTORY) {
    latestData.history.shift();
  }
  
  // 广播给所有WebSocket客户端
  broadcastToClients({
    type: 'data_update',
    payload: latestData
  });
  
  console.log(`[${new Date().toISOString()}] 数据更新完成`);
}

// 广播消息给所有WebSocket客户端
function broadcastToClients(message) {
  const messageStr = JSON.stringify(message);
  clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(messageStr);
    }
  });
}

// WebSocket连接处理
wss.on('connection', (ws) => {
  console.log('新的WebSocket连接已建立');
  clients.add(ws);
  
  // 发送当前最新数据
  ws.send(JSON.stringify({
    type: 'initial_data',
    payload: latestData
  }));
  
  ws.on('close', () => {
    console.log('WebSocket连接已关闭');
    clients.delete(ws);
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket错误:', error);
    clients.delete(ws);
  });
});

// REST API 端点
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 获取当前数据
app.get('/api/data', (req, res) => {
  res.json(latestData);
});

// 获取历史数据
app.get('/api/history', (req, res) => {
  res.json(latestData.history || []);
});

// 手动触发数据刷新
app.post('/api/refresh', async (req, res) => {
  await pollData();
  res.json({ success: true, message: '数据已刷新' });
});

// 获取配置信息（脱敏）
app.get('/api/config', (req, res) => {
  res.json({
    memberId: CONFIG.API.MEMBER_ID,
    pollInterval: CONFIG.POLL.INTERVAL,
    lastUpdate: latestData.timestamp
  });
});

// API代理 - 用于转发API请求
app.post('/api/proxy', async (req, res) => {
  const { endpoint, params } = req.body;
  
  if (!endpoint) {
    return res.status(400).json({ error: '缺少endpoint参数' });
  }
  
  const result = await fetchDataFromAPI(endpoint, params || {});
  res.json(result);
});

// 启动服务器
server.listen(CONFIG.SERVER.PORT, CONFIG.SERVER.HOST, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║     西瓜猪开放平台 - 实时数据观测系统 正式启动！              ║
╠═══════════════════════════════════════════════════════════╣
║  Web界面:  http://${CONFIG.SERVER.HOST}:${CONFIG.SERVER.PORT}                    ║
║  会员ID:   ${CONFIG.API.MEMBER_ID}                                  ║
║  轮询间隔: ${CONFIG.POLL.INTERVAL / 1000}秒                                       ║
╚═══════════════════════════════════════════════════════════╝
  `);
  
  // 启动轮询
  if (CONFIG.POLL.ENABLED) {
    pollData(); // 立即执行一次
    setInterval(pollData, CONFIG.POLL.INTERVAL);
  }
});
