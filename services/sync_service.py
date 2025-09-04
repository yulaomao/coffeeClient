import logging
from datetime import datetime
from typing import Dict, Any
from config import config
from services.redis_service import redis_service

logger = logging.getLogger(__name__)

class SyncService:
    """数据同步服务类"""
    
    def __init__(self):
        pass
    
    def initialize_device(self):
        """设备初始化 - 启动时自检/自建/自修复"""
        try:
            logger.info("开始设备初始化...")
            
            # 1. 确保全局字典
            self.ensure_global_dictionaries()
            
            # 2. 初始化设备基础信息
            self.initialize_device_info()
            
            # 3. 初始化设备位置信息
            self.initialize_location_info()
            
            # 4. 初始化料盒信息
            self.initialize_bins()
            
            # 5. 初始化包和配方
            self.initialize_packages_and_recipes()
            
            # 6. 维护派生索引
            self.maintain_derived_indexes()
            
            # 7. 记录启动审计
            self.log_boot_audit()
            
            logger.info("设备初始化完成")
            
        except Exception as e:
            logger.error(f"设备初始化失败: {e}")
            raise
    
    def ensure_global_dictionaries(self):
        """确保全局字典存在"""
        logger.info("检查全局字典...")
        redis_service.ensure_global_dict()
        logger.info("全局字典检查完成")
    
    def initialize_device_info(self):
        """初始化设备基础信息"""
        logger.info("初始化设备基础信息...")
        
        # 获取现有设备信息
        existing_info = redis_service.get_device_info()
        
        # 基础设备信息
        device_info = {
            'device_id': config.DEVICE_ID,
            'merchant_id': config.MERCHANT_ID,
            'alias': config.DEVICE_ALIAS,
            'model': config.DEVICE_MODEL,
            'fw_version': config.FIRMWARE_VERSION,
            'status': 'online',
            'last_seen_ts': int(datetime.now().timestamp()),
            'created_ts': existing_info.get('created_ts', int(datetime.now().timestamp())),
            'updated_ts': int(datetime.now().timestamp())
        }
        
        # 如果是首次初始化，添加更多信息
        if not existing_info:
            device_info.update({
                'total_orders': 0,
                'total_revenue_cents': 0,
                'boot_count': 1,
                'last_maintenance_ts': int(datetime.now().timestamp())
            })
        else:
            # 保留现有统计信息
            device_info.update({
                'total_orders': existing_info.get('total_orders', 0),
                'total_revenue_cents': existing_info.get('total_revenue_cents', 0),
                'boot_count': int(existing_info.get('boot_count', 0)) + 1,
                'last_maintenance_ts': existing_info.get('last_maintenance_ts')
            })
        
        redis_service.set_device_info(device_info)
        logger.info("设备基础信息初始化完成")
    
    def initialize_location_info(self):
        """初始化设备位置信息"""
        logger.info("初始化设备位置信息...")
        
        loc_key = redis_service.get_device_key('loc')
        existing_loc = redis_service.redis_client.hgetall(loc_key)
        
        # 如果没有位置信息，设置默认值
        if not existing_loc:
            location_info = {
                'name': config.DEVICE_ALIAS,
                'address': '待设置',
                'lat': 0.0,
                'lng': 0.0,
                'scene': 'office',
                'updated_ts': int(datetime.now().timestamp())
            }
            
            redis_service.redis_client.hset(loc_key, mapping=location_info)
        
        logger.info("设备位置信息初始化完成")
    
    def initialize_bins(self):
        """初始化料盒信息"""
        logger.info("初始化料盒信息...")
        
        # 默认料盒配置
        default_bins = [
            {
                'bin_index': 0,
                'material_code': 'BEAN_A',
                'remaining': 100,
                'capacity': 1000,
                'unit': 'g',
                'threshold_low_pct': 20,
                'last_sync_ts': int(datetime.now().timestamp())
            },
            {
                'bin_index': 1,
                'material_code': 'MILK_POWDER',
                'remaining': 200,
                'capacity': 500,
                'unit': 'g',
                'threshold_low_pct': 20,
                'last_sync_ts': int(datetime.now().timestamp())
            },
            {
                'bin_index': 2,
                'material_code': 'SUGAR',
                'remaining': 300,
                'capacity': 300,
                'unit': 'g',
                'threshold_low_pct': 20,
                'last_sync_ts': int(datetime.now().timestamp())
            },
            {
                'bin_index': 3,
                'material_code': 'WATER',
                'remaining': 5000,
                'capacity': 5000,
                'unit': 'ml',
                'threshold_low_pct': 10,
                'last_sync_ts': int(datetime.now().timestamp())
            }
        ]
        
        # 初始化每个料盒
        for bin_config in default_bins:
            bin_index = bin_config['bin_index']
            existing_bin = redis_service.get_bin_info(bin_index)
            
            # 如果料盒不存在，创建默认配置
            if not existing_bin:
                redis_service.set_bin_info(bin_index, bin_config)
            else:
                # 更新时间戳和确保结构完整
                bin_config.update({
                    'remaining': existing_bin.get('remaining', bin_config['remaining']),
                    'last_sync_ts': int(datetime.now().timestamp())
                })
                redis_service.set_bin_info(bin_index, bin_config)
        
        logger.info("料盒信息初始化完成")
    
    def initialize_packages_and_recipes(self):
        """初始化包和激活配方"""
        logger.info("初始化包和配方...")
        
        # 设置已安装的包
        packages_key = redis_service.get_device_key('packages:installed')
        redis_service.redis_client.sadd(packages_key, 'pkg-001')
        
        # 设置包安装信息
        package_key = redis_service.get_device_key('package:pkg-001')
        package_info = {
            'package_id': 'pkg-001',
            'installed_ts': int(datetime.now().timestamp()),
            'version': '1.0.0',
            'status': 'active'
        }
        redis_service.redis_client.hset(package_key, mapping=package_info)
        
        # 设置激活的配方
        recipes_key = redis_service.get_device_key('recipes:active')
        redis_service.redis_client.sadd(recipes_key, '201', '202', '203')
        
        logger.info("包和配方初始化完成")
    
    def maintain_derived_indexes(self):
        """维护派生索引"""
        logger.info("维护派生索引...")
        
        # 设备状态索引
        redis_service.redis_client.sadd('cm:idx:device:status:online', config.DEVICE_ID)
        redis_service.redis_client.srem('cm:idx:device:status:offline', config.DEVICE_ID)
        
        # 商户设备索引
        merchant_devices_key = f"cm:idx:merchant:{config.MERCHANT_ID}:devices"
        redis_service.redis_client.sadd(merchant_devices_key, config.DEVICE_ID)
        
        # 设备最后在线时间索引
        last_seen_ts = int(datetime.now().timestamp())
        redis_service.redis_client.zadd('cm:idx:device:last_seen', {config.DEVICE_ID: last_seen_ts})
        
        logger.info("派生索引维护完成")
    
    def log_boot_audit(self):
        """记录启动审计日志"""
        logger.info("记录启动审计...")
        
        device_info = redis_service.get_device_info()
        boot_count = int(device_info.get('boot_count', 1))
        
        audit_data = {
            'boot_count': boot_count,
            'fw_version': config.FIRMWARE_VERSION,
            'config_hash': self.get_config_hash()
        }
        
        event_type = 'boot_ok' if boot_count > 1 else 'boot_init'
        redis_service.add_audit_log(event_type, audit_data)
        
        logger.info("启动审计记录完成")
    
    def get_config_hash(self) -> str:
        """获取配置哈希值"""
        import hashlib
        
        config_data = {
            'device_id': config.DEVICE_ID,
            'merchant_id': config.MERCHANT_ID,
            'firmware_version': config.FIRMWARE_VERSION,
            'payment_timeout': config.PAYMENT_TIMEOUT,
            'enable_queue': config.ENABLE_QUEUE
        }
        
        config_str = str(sorted(config_data.items()))
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    def update_heartbeat(self):
        """更新心跳"""
        try:
            redis_service.update_heartbeat()
            
            # 发布心跳事件
            redis_service.publish_event('heartbeat', {
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"心跳更新失败: {e}")
    
    def sync_materials(self):
        """同步物料信息"""
        try:
            bins = redis_service.get_all_bins()
            low_bins = redis_service.get_low_bins()
            
            # 发布物料状态事件
            redis_service.publish_event('materials_sync', {
                'bins_count': len(bins),
                'low_bins_count': len(low_bins),
                'low_bins': low_bins
            })
            
            logger.info(f"物料同步完成: {len(bins)}个料盒, {len(low_bins)}个低量")
            
        except Exception as e:
            logger.error(f"物料同步失败: {e}")
    
    def check_device_health(self) -> Dict[str, Any]:
        """检查设备健康状态"""
        try:
            device_info = redis_service.get_device_info()
            bins = redis_service.get_all_bins()
            low_bins = redis_service.get_low_bins()
            
            # 计算在线时长
            last_seen = int(device_info.get('last_seen_ts', 0))
            uptime = int(datetime.now().timestamp()) - last_seen
            
            health_status = {
                'status': 'healthy',
                'uptime_seconds': uptime,
                'bins_count': len(bins),
                'low_bins_count': len(low_bins),
                'total_orders': int(device_info.get('total_orders', 0)),
                'boot_count': int(device_info.get('boot_count', 1)),
                'redis_connected': True
            }
            
            # 检查是否有严重问题
            if len(low_bins) >= len(bins) * 0.5:  # 超过一半料盒低量
                health_status['status'] = 'warning'
                health_status['warnings'] = ['多个料盒物料不足']
            
            return health_status
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'redis_connected': False
            }

# 创建全局实例
sync_service = SyncService()
