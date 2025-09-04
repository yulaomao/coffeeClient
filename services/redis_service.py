import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config

logger = logging.getLogger(__name__)

class RedisService:
    """Redis数据服务类"""
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        
    def connect(self):
        """连接Redis服务器"""
        try:
            self.redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis连接成功: {config.REDIS_HOST}:{config.REDIS_PORT}")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    def ping(self):
        """检查Redis连接"""
        if not self.redis_client:
            raise Exception("Redis未连接")
        return self.redis_client.ping()
    
    def get_pubsub(self):
        """获取PubSub对象"""
        if not self.pubsub:
            self.pubsub = self.redis_client.pubsub()
        return self.pubsub
    
    def publish_event(self, event_type: str, data: Dict[str, Any]):
        """发布事件到Redis"""
        event_data = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'device_id': config.DEVICE_ID,
            **data
        }
        
        self.redis_client.publish('dv:events', json.dumps(event_data))
        logger.debug(f"发布事件: {event_type}, 数据: {data}")
    
    # 设备相关方法
    def get_device_key(self, suffix: str = '') -> str:
        """生成设备键名"""
        base_key = f"cm:dev:{config.DEVICE_ID}"
        return f"{base_key}:{suffix}" if suffix else base_key
    
    def set_device_info(self, device_data: Dict[str, Any]):
        """设置设备信息"""
        key = self.get_device_key()
        self.redis_client.hset(key, mapping=device_data)
        logger.debug(f"设置设备信息: {device_data}")
    
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        key = self.get_device_key()
        return self.redis_client.hgetall(key)
    
    def update_heartbeat(self):
        """更新设备心跳"""
        now_ts = int(datetime.now().timestamp())
        key = self.get_device_key()
        
        self.redis_client.hset(key, mapping={
            'last_seen_ts': now_ts,
            'status': 'online'
        })
        
        # 更新索引
        self.redis_client.zadd('cm:idx:device:last_seen', {config.DEVICE_ID: now_ts})
        self.redis_client.sadd('cm:idx:device:status:online', config.DEVICE_ID)
        self.redis_client.srem('cm:idx:device:status:offline', config.DEVICE_ID)
    
    # 料盒相关方法  
    def get_bins_key(self) -> str:
        """获取料盒集合键名"""
        return self.get_device_key('bins')
    
    def get_bin_key(self, bin_index: int) -> str:
        """获取单个料盒键名"""
        return self.get_device_key(f'bin:{bin_index}')
    
    def get_low_bins_key(self) -> str:
        """获取低量料盒键名"""
        return self.get_device_key('bins:low')
    
    def set_bin_info(self, bin_index: int, bin_data: Dict[str, Any]):
        """设置料盒信息"""
        bin_key = self.get_bin_key(bin_index)
        bins_key = self.get_bins_key()
        
        # 设置料盒详细信息
        self.redis_client.hset(bin_key, mapping=bin_data)
        
        # 添加到料盒集合
        self.redis_client.sadd(bins_key, str(bin_index))
        
        # 检查是否低量
        remaining = float(bin_data.get('remaining', 0))
        capacity = float(bin_data.get('capacity', 100))
        threshold = float(bin_data.get('threshold_low_pct', 20))
        
        low_bins_key = self.get_low_bins_key()
        if capacity > 0 and (remaining / capacity * 100) < threshold:
            self.redis_client.sadd(low_bins_key, str(bin_index))
        else:
            self.redis_client.srem(low_bins_key, str(bin_index))
    
    def get_bin_info(self, bin_index: int) -> Dict[str, Any]:
        """获取料盒信息"""
        key = self.get_bin_key(bin_index)
        return self.redis_client.hgetall(key)
    
    def get_all_bins(self) -> Dict[int, Dict[str, Any]]:
        """获取所有料盒信息"""
        bins_key = self.get_bins_key()
        bin_indices = self.redis_client.smembers(bins_key)
        
        bins = {}
        for bin_index_str in bin_indices:
            bin_index = int(bin_index_str)
            bins[bin_index] = self.get_bin_info(bin_index)
        
        return bins
    
    def get_low_bins(self) -> List[int]:
        """获取低量料盒列表"""
        key = self.get_low_bins_key()
        low_bin_indices = self.redis_client.smembers(key)
        return [int(idx) for idx in low_bin_indices]
    
    # 订单相关方法
    def get_order_key(self, order_id: str) -> str:
        """获取订单键名"""
        return self.get_device_key(f'order:{order_id}')
    
    def get_orders_index_key(self) -> str:
        """获取订单时间索引键名"""
        return self.get_device_key('orders:by_ts')
    
    def create_order(self, order_data: Dict[str, Any]):
        """创建订单"""
        order_id = order_data['order_id']
        order_key = self.get_order_key(order_id)
        index_key = self.get_orders_index_key()
        
        # 设置订单数据
        order_data['created_ts'] = int(datetime.now().timestamp())
        # 将非标量（dict/list 等）转换成 JSON 再写入 Redis，避免 WRONGTYPE/Invalid input 错误
        clean_mapping: Dict[str, Any] = {}
        for k, v in order_data.items():
            if isinstance(v, (dict, list)):
                clean_mapping[k] = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, (str, int, float, bytes)) or v is None:
                clean_mapping[k] = v if v is not None else ''
            else:
                clean_mapping[k] = str(v)
        self.redis_client.hset(order_key, mapping=clean_mapping)
        
        # 添加到时间索引
        self.redis_client.zadd(index_key, {order_id: order_data['created_ts']})
        
        logger.info(f"创建订单: {order_id}")
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """获取订单信息"""
        key = self.get_order_key(order_id)
        return self.redis_client.hgetall(key)
    
    def update_order_status(self, order_id: str, status: str, **kwargs):
        """更新订单状态"""
        key = self.get_order_key(order_id)
        update_data = {'status': status, 'updated_ts': int(datetime.now().timestamp())}
        update_data.update(kwargs)
        
        self.redis_client.hset(key, mapping=update_data)
        
        # 发布订单状态更新事件
        self.publish_event('order_update', {
            'order_id': order_id,
            'status': status,
            **kwargs
        })
    
    # 命令相关方法
    def get_command_key(self, command_id: str) -> str:
        """获取命令键名"""
        return self.get_device_key(f'command:{command_id}')
    
    def get_command_queue_key(self) -> str:
        """获取命令队列键名"""
        return self.get_device_key('commands:queue')
    
    def claim_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """认领命令"""
        command_key = self.get_command_key(command_id)
        queue_key = self.get_command_queue_key()
        
        # 检查命令是否存在
        command_data = self.redis_client.hgetall(command_key)
        if not command_data:
            return None
        
        # 检查状态
        if command_data.get('status') != 'pending':
            return None
        
        # 更新为已认领
        self.redis_client.hset(command_key, mapping={
            'status': 'claimed',
            'claimed_ts': int(datetime.now().timestamp()),
            'claimed_by': config.DEVICE_ID
        })
        
        # 从队列移除
        self.redis_client.lrem(queue_key, 0, command_id)
        
        return self.redis_client.hgetall(command_key)
    
    def complete_command(self, command_id: str, success: bool, result: Optional[str] = None, error: Optional[str] = None):
        """完成命令"""
        command_key = self.get_command_key(command_id)
        
        update_data = {
            'status': 'success' if success else 'failed',
            'completed_ts': int(datetime.now().timestamp())
        }
        
        if result:
            update_data['result'] = result
        if error:
            update_data['error'] = error
        
        self.redis_client.hset(command_key, mapping=update_data)
        
        # 发布命令完成事件
        self.publish_event('command_done', {
            'command_id': command_id,
            'status': update_data['status'],
            'result': result,
            'error': error
        })
    
    # 全局字典方法
    def ensure_global_dict(self):
        """确保全局字典存在"""
        # 材料字典
        materials = {
            'BEAN_A': {'name': '咖啡豆A', 'unit': 'g', 'type': 'bean'},
            'MILK_POWDER': {'name': '奶粉', 'unit': 'g', 'type': 'powder'},
            'SUGAR': {'name': '糖', 'unit': 'g', 'type': 'powder'},
            'WATER': {'name': '水', 'unit': 'ml', 'type': 'liquid'}
        }
        
        for material_code, material_data in materials.items():
            key = f"cm:dict:material:{material_code}"
            if not self.redis_client.exists(key):
                self.redis_client.hset(key, mapping=material_data)
        
        # 配方字典
        recipes = {
            '201': {
                'name': '美式咖啡',
                'price_cents': 1500,
                'materials_json': json.dumps({
                    'BEAN_A': 15,
                    'WATER': 200
                })
            },
            '202': {
                'name': '拿铁',
                'price_cents': 2000,
                'materials_json': json.dumps({
                    'BEAN_A': 15,
                    'MILK_POWDER': 10,
                    'WATER': 180
                })
            },
            '203': {
                'name': '摩卡',
                'price_cents': 2500,
                'materials_json': json.dumps({
                    'BEAN_A': 15,
                    'MILK_POWDER': 10,
                    'SUGAR': 5,
                    'WATER': 180
                })
            }
        }
        
        for recipe_id, recipe_data in recipes.items():
            key = f"cm:dict:recipe:{recipe_id}"
            if not self.redis_client.exists(key):
                self.redis_client.hset(key, mapping=recipe_data)
        
        # 包字典
        package_data = {
            'manifest_json': json.dumps({
                'version': '1.0.0',
                'recipes': ['201', '202', '203']
            })
        }
        
        key = "cm:dict:package:pkg-001"
        if not self.redis_client.exists(key):
            self.redis_client.hset(key, mapping=package_data)
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """获取配方信息"""
        key = f"cm:dict:recipe:{recipe_id}"
        recipe_data = self.redis_client.hgetall(key)
        
        if recipe_data and 'materials_json' in recipe_data:
            recipe_data['materials'] = json.loads(recipe_data['materials_json'])
        
        return recipe_data if recipe_data else None
    
    def get_all_recipes(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配方"""
        recipes: Dict[str, Dict[str, Any]] = {}
        # 使用 SCAN 避免阻塞，并且仅处理哈希类型键，防止 WRONGTYPE
        try:
            for key in self.redis_client.scan_iter(match="cm:dict:recipe:*"):
                try:
                    if self.redis_client.type(key) != 'hash':
                        continue
                    recipe_id = key.split(':')[-1]
                    recipe_data = self.get_recipe(recipe_id)
                    if recipe_data:
                        recipes[recipe_id] = recipe_data
                except Exception as inner_e:
                    logger.warning(f"跳过非法配方键 {key}: {inner_e}")
        except Exception as e:
            logger.error(f"扫描配方键失败: {e}")
        return recipes
    
    # 审计日志方法
    def add_audit_log(self, event_type: str, data: Dict[str, Any]):
        """添加审计日志"""
        stream_key = self.get_device_key('stream:audit')
        
        log_data = {
            'event': event_type,
            'timestamp': datetime.now().isoformat(),
            'device_id': config.DEVICE_ID,
            **data
        }
        
        self.redis_client.xadd(stream_key, log_data)
        logger.debug(f"添加审计日志: {event_type}")

# 创建全局实例
redis_service = RedisService()
