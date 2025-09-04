from flask import Flask, render_template, request, jsonify, Response
import json
import logging
from datetime import datetime
import threading
import time

from config import config
from services.redis_service import redis_service
from services.sync_service import sync_service
from routes.customer import customer_bp
from routes.maintenance import maintenance_bp
from routes.api import api_bp

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(config)

# 添加模板全局函数
@app.template_global()
def moment(timestamp=None):
    """模拟 moment.js 功能的简单时间格式化"""
    class MomentFormatter:
        def __init__(self, dt):
            self.dt = dt
            
        def format(self, format_str):
            """格式化时间"""
            format_map = {
                'YYYY-MM-DD HH:mm:ss': '%Y-%m-%d %H:%M:%S',
                'YYYY-MM-DD': '%Y-%m-%d',
                'HH:mm:ss': '%H:%M:%S',
                'HH:mm': '%H:%M'
            }
            return self.dt.strftime(format_map.get(format_str, format_str))
            
        def fromNow(self):
            """相对时间格式"""
            now = datetime.now()
            diff = now - self.dt
            
            if diff.days > 0:
                return f"{diff.days}天前"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}小时前"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}分钟前"
            else:
                return "刚刚"
    
    if timestamp is None:
        dt = datetime.now()
    elif isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = timestamp
        
    return MomentFormatter(dt)

# 注册蓝图
app.register_blueprint(customer_bp, url_prefix='/')
app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
app.register_blueprint(api_bp, url_prefix='/api')

# SSE事件流
def event_stream():
    """服务器发送事件流"""
    def event_publisher():
        pubsub = redis_service.get_pubsub()
        pubsub.subscribe('dv:events')
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    yield f"data: {json.dumps(data)}\n\n"
                except Exception as e:
                    logger.error(f"SSE事件处理错误: {e}")
                    continue
    
    return Response(event_publisher(), mimetype='text/event-stream')

@app.route('/events')
def events():
    """SSE事件端点"""
    return event_stream()

@app.route('/')
def index():
    """首页重定向到顾客界面"""
    return render_template('customer/idle.html')

@app.route('/health')
def health():
    """健康检查"""
    try:
        # 检查Redis连接
        redis_service.ping()
        
        # 检查设备状态
        device_status = redis_service.get_device_info()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'device_id': config.DEVICE_ID,
            'redis_connected': True,
            'device_online': device_status.get('status') == 'online'
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def heartbeat_worker():
    """心跳工作线程"""
    while True:
        try:
            sync_service.update_heartbeat()
            logger.debug("心跳更新成功")
        except Exception as e:
            logger.error(f"心跳更新失败: {e}")
        
        time.sleep(30)  # 每30秒更新一次心跳

def startup_checks():
    """启动检查和初始化"""
    try:
        logger.info("开始启动检查...")
        
        # 连接Redis
        redis_service.connect()
        logger.info("Redis连接成功")
        
        # 执行同步初始化
        sync_service.initialize_device()
        logger.info("设备初始化完成")
        
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        logger.info("心跳线程启动成功")
        
        logger.info("启动检查完成")
        
    except Exception as e:
        logger.error(f"启动检查失败: {e}")
        raise

# 应用启动时执行初始化（替代 before_first_request）
def run_startup_checks():
    """执行启动检查"""
    if not hasattr(app, '_startup_done'):
        startup_checks()
        app._startup_done = True

@app.before_request
def before_request():
    """每次请求前检查是否需要初始化"""
    run_startup_checks()

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('error.html', 
                         error_code=404,
                         error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    return render_template('error.html',
                         error_code=500, 
                         error_message='内部服务器错误'), 500

if __name__ == '__main__':
    # 开发环境下的启动检查
    if config.DEBUG:
        startup_checks()
    
    app.run(
        host='0.0.0.0', 
        port=8080, 
        debug=config.DEBUG,
        threaded=True
    )
