# 智能自助咖啡机设备端项目

## 项目概述
基于Flask Web触控界面和Redis的智能自助咖啡机设备端系统，实现完整的用户交互、支付、制作、物料管理等功能。

## 技术栈
- Flask (Web框架)
- Redis (数据存储和实时通信)
- Jinja2 (模板引擎) 
- Bootstrap/Tailwind (UI框架)
- Server-Sent Events (实时通信)
- Python 3.8+

## 核心功能
- 触控Web UI界面
- Redis数据同步契约
- 支付集成
- 物料管理
- 实时事件处理
- 设备状态监控
- 运维管理界面

## 开发规则
- 严格遵循设备为中心的Redis规则 (cm:dev:{device_id}:*)
- 所有操作必须保证幂等性
- 实时事件通过SSE订阅
- 启动时自检/自建/自修复数据

项目已完成结构搭建 ✓
