# 智能自助咖啡机 - 设备端系统

基于 Flask + Redis 的智能咖啡机设备端系统，采用设备为中心的架构设计，支持触控界面、实时状态监控、支付集成和远程运维管理。

## 系统特性

### 核心功能
- **设备中心化架构**: 基于 Redis 的 `cm:dev:{device_id}:*` 键模式
- **触控优化界面**: 44px 最小触摸目标，适配各种屏幕尺寸
- **实时事件系统**: 基于 SSE 的实时状态更新
- **幂等操作设计**: 支持重复请求的安全处理
- **支付系统集成**: 微信支付/支付宝模拟
- **物料智能管理**: 自动监控、低量警报、补充提醒
- **制作流程控制**: 完整的咖啡制作工艺流程
- **运维管理系统**: PIN 码保护的维护界面

### 技术栈
- **后端**: Flask 2.3.3, Python 3.8+
- **数据存储**: Redis 4.6.0 (数据 + 发布订阅)
- **前端**: Bootstrap 5.3.0 + 自定义 CSS/JS
- **实时通信**: Server-Sent Events (SSE)
- **模板引擎**: Jinja2

## 项目结构

```
client/
├── app.py              # Flask 应用入口
├── config.py           # 配置管理
├── requirements.txt    # Python 依赖
├── services/           # 业务服务层
│   ├── __init__.py
│   ├── redis_service.py    # Redis 数据服务
│   ├── sync_service.py     # 云端同步服务
│   ├── payment_service.py  # 支付服务
│   └── brewing_service.py  # 制作服务
├── routes/             # 路由控制器
│   ├── __init__.py
│   ├── customer.py         # 客户界面路由
│   ├── maintenance.py      # 运维界面路由
│   └── api.py             # API 接口路由
├── models/             # 数据模型
│   ├── __init__.py
│   └── device.py          # 设备模型
├── utils/              # 工具模块
│   ├── __init__.py
│   ├── constants.py       # 常量定义
│   └── validators.py      # 数据验证
├── templates/          # Jinja2 模板
│   ├── base.html          # 基础模板
│   ├── customer/          # 客户界面模板
│   │   ├── idle.html
│   │   ├── menu.html
│   │   └── out_of_service.html
│   └── maintenance/       # 运维界面模板
│       ├── pin_entry.html
│       ├── home.html
│       ├── quick_ops.html
│       ├── bins.html
│       ├── status.html
│       ├── logs.html
│       └── settings.html
└── static/             # 静态资源
    ├── css/
    │   └── main.css       # 主样式文件
    └── js/
        └── main.js        # 主脚本文件
```

## 数据架构

### Redis 键命名规范
- `cm:dev:{device_id}:info` - 设备基本信息
- `cm:dev:{device_id}:health` - 设备健康状态
- `cm:dev:{device_id}:bins` - 物料容器状态
- `cm:dev:{device_id}:orders:{order_id}` - 订单信息
- `cm:dev:{device_id}:stats:daily:{date}` - 每日统计
- `cm:dev:{device_id}:settings:{group}` - 设备配置

### 发布订阅频道
- `cm:dev:{device_id}:events` - 设备事件通道
- `cm:dev:{device_id}:commands` - 远程命令通道

## 快速开始

### 环境要求
- Python 3.8+
- Redis Server 4.0+

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
```bash
# 复制并编辑配置文件
cp .env.example .env

# 主要配置项
FLASK_ENV=development
REDIS_HOST=localhost
REDIS_PORT=6379
DEVICE_ID=CM001
SECRET_KEY=your-secret-key
```

### 启动应用
```bash
python app.py
```

### 访问界面
- 客户界面: http://localhost:5000/
- 运维界面: http://localhost:5000/maintenance/pin-entry

## API 接口

### 设备状态
```
GET /api/device/status
GET /api/device/health
```

### 物料管理
```
GET /api/device/bins
PUT /api/device/bins/{bin_index}
POST /api/device/bins/{bin_index}/refill
```

### 订单处理
```
POST /api/orders
GET /api/orders/{order_id}
```

### 实时事件
```
GET /events (Server-Sent Events)
```

## 主要功能模块

### 1. 客户界面
- **空闲页面**: 欢迎界面，显示设备状态
- **菜单浏览**: 产品展示，价格查看
- **支付流程**: 支付方式选择，二维码展示
- **制作监控**: 实时制作进度，剩余时间
- **完成提醒**: 取餐提示，满意度调查

### 2. 运维管理
- **PIN 码验证**: 6 位数字密码保护
- **设备监控**: 实时状态，资源使用情况
- **快速操作**: 一键执行常用维护任务
- **物料管理**: 料盒状态，补充记录
- **日志查看**: 系统日志，错误追踪
- **系统设置**: 设备配置，参数调整

### 3. 支付系统
- **多种支付方式**: 微信支付、支付宝
- **二维码生成**: 动态支付码
- **支付状态监控**: 实时支付反馈
- **超时处理**: 自动取消，资源释放

### 4. 制作系统
- **工艺流程控制**: 研磨、冲泡、出品
- **实时进度反馈**: 进度百分比，剩余时间
- **异常处理**: 故障检测，自动恢复
- **质量控制**: 温度监控，压力调节

## 设计亮点

### 触控优化
- 44px 最小触摸目标
- 大按钮设计，易于操作
- 触摸反馈动画
- 响应式布局适配

### 实时性
- SSE 事件推送
- 无刷新状态更新
- 即时错误反馈
- 实时进度显示

### 可维护性
- 模块化架构设计
- 清晰的代码组织
- 完整的错误处理
- 详细的操作日志

### 可扩展性
- 插件化服务设计
- 配置驱动的业务逻辑
- 标准化 API 接口
- 云端集成支持

## 开发指南

### 添加新的设备类型
1. 在 `models/device.py` 中扩展设备模型
2. 在 `services/` 中实现对应的业务逻辑
3. 在 `templates/` 中添加界面模板
4. 在 `routes/` 中注册路由

### 集成新的支付方式
1. 在 `services/payment_service.py` 中添加支付处理器
2. 在 `templates/customer/` 中添加支付界面
3. 在前端 JS 中处理支付回调

### 扩展 API 功能
1. 在 `routes/api.py` 中定义新接口
2. 在 `utils/validators.py` 中添加数据验证
3. 更新 API 文档

## 注意事项

### 安全考虑
- 运维界面 PIN 码保护
- API 接口权限控制
- 敏感信息加密存储
- 操作日志完整记录

### 性能优化
- Redis 连接池复用
- 静态资源缓存
- 数据库查询优化
- 前端资源压缩

### 错误处理
- 全局异常捕获
- 用户友好错误提示
- 详细错误日志记录
- 自动故障恢复

## 许可证

MIT License

## 贡献指南

1. Fork 本项目
2. 创建功能分支
3. 提交改动
4. 推送到分支
5. 创建 Pull Request

---

**项目状态**: 开发完成，已包含所有核心功能模块和界面模板。
- **实时通信**: SSE事件推送，实时状态更新
- **设备监控**: 心跳检测，状态同步，远程命令执行
- **运维界面**: 门禁保护的运维管理功能

## 快速开始

### 环境要求

- Python 3.8+
- Redis 6.0+
- 触控显示设备

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 启动服务

```bash
python app.py
```

访问 `http://localhost:5000` 查看触控界面。

## 项目结构

```
/
├── app.py                 # Flask应用主入口
├── config.py              # 配置管理
├── requirements.txt       # Python依赖
├── .env.example          # 环境配置示例
├── models/               # 数据模型
│   ├── device.py         # 设备模型
│   ├── order.py          # 订单模型
│   ├── material.py       # 物料模型
│   └── command.py        # 命令模型
├── services/             # 业务服务
│   ├── redis_service.py  # Redis服务
│   ├── payment_service.py# 支付服务
│   ├── brewing_service.py# 制作服务
│   └── sync_service.py   # 同步服务
├── routes/               # 路由控制器
│   ├── customer.py       # 顾客界面路由
│   ├── maintenance.py    # 运维界面路由
│   └── api.py           # API接口
├── templates/            # 前端模板
│   ├── base.html        # 基础模板
│   ├── customer/        # 顾客界面模板
│   └── maintenance/     # 运维界面模板
├── static/              # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
└── utils/               # 工具函数
    ├── validators.py    # 验证器
    ├── formatters.py    # 格式化工具
    └── constants.py     # 常量定义
```

## Redis数据结构

### 设备信息
```
cm:dev:{id}                    # 设备基础信息
cm:dev:{id}:loc               # 设备位置信息
cm:dev:{id}:bins              # 料盒集合
cm:dev:{id}:bin:{i}           # 单个料盒信息
cm:dev:{id}:bins:low          # 低量料盒集合
```

### 订单与命令
```
cm:dev:{id}:order:{order_id}  # 订单详情
cm:dev:{id}:orders:by_ts      # 订单时间索引
cm:dev:{id}:command:{cmd_id}  # 命令详情
cm:dev:{id}:commands:queue    # 命令队列
```

### 全局字典
```
cm:dict:material:*            # 物料字典
cm:dict:recipe:*              # 配方字典
cm:dict:package:*             # 包字典
```

## 开发指南

### Redis同步契约

所有数据操作必须遵循设备为中心原则：
- 启动时自检并修复数据结构
- 所有写操作保证幂等性
- 通过PubSub推送实时事件

### UI设计原则

- 触控友好：最小44px触控目标
- 实时反馈：通过SSE更新状态
- 容错设计：网络断开时优雅降级
- 可访问性：支持大字模式和高对比度

### 安全考虑

- 运维界面需PIN码保护
- 危险操作需二次确认
- 所有操作记录审计日志

## 许可证

MIT License
