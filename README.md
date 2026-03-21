# 西瓜猪开放平台 - 实时数据观测系统

## 简介

基于西瓜猪开放平台API的实时数据监控系统，支持订单数据实时轮询、历史记录查看。

## 项目结构

```
xiguazhu-monitor/
├── app.py           # 主程序
├── config.json      # 配置文件
├── public/
│   └── index.html   # 前端页面
└── README.md        # 说明文档
```

## 配置说明

编辑 `config.json` 修改配置：

```json
{
  "api": {
    "baseUrl": "https://openapi.xgzcdn.com",  // API地址
    "appKey": "你的AppKey",
    "appSecret": "你的AppSecret",
    "memberId": "你的会员ID"
  },
  "server": {
    "port": 3000,      // 服务端口
    "host": "0.0.0.0"   // 监听地址
  },
  "poll": {
    "interval": 30,     // 刷新间隔（秒）
    "daysRange": 7      // 查询时间范围（天）
  }
}
```

## 启动

```bash
cd ~/.qclaw/workspace/xiguazhu-monitor
python3 app.py
```

## 访问

- 本机：http://localhost:3000
- 局域网：http://你的IP:3000

## 接口信息

- **API地址**: https://openapi.xgzcdn.com
- **接口**: /cps/cpsOrder/list
- **会员ID**: 38011
- **签名字段**: endTime, offset, pageSize, queryType, startTime, timestamp
