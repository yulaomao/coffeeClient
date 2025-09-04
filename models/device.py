"""设备模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from utils.constants import *

@dataclass
class Device:
    """设备模型"""
    device_id: str
    merchant_id: str
    alias: str
    model: str
    fw_version: str
    status: str = DEVICE_STATUS_ONLINE
    last_seen_ts: int = 0
    created_ts: int = 0
    updated_ts: int = 0
    total_orders: int = 0
    total_revenue_cents: int = 0
    boot_count: int = 0
    last_maintenance_ts: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """从字典创建设备对象"""
        return cls(
            device_id=data.get('device_id', ''),
            merchant_id=data.get('merchant_id', ''),
            alias=data.get('alias', ''),
            model=data.get('model', ''),
            fw_version=data.get('fw_version', ''),
            status=data.get('status', DEVICE_STATUS_OFFLINE),
            last_seen_ts=int(data.get('last_seen_ts', 0)),
            created_ts=int(data.get('created_ts', 0)),
            updated_ts=int(data.get('updated_ts', 0)),
            total_orders=int(data.get('total_orders', 0)),
            total_revenue_cents=int(data.get('total_revenue_cents', 0)),
            boot_count=int(data.get('boot_count', 0)),
            last_maintenance_ts=int(data.get('last_maintenance_ts', 0))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'device_id': self.device_id,
            'merchant_id': self.merchant_id,
            'alias': self.alias,
            'model': self.model,
            'fw_version': self.fw_version,
            'status': self.status,
            'last_seen_ts': self.last_seen_ts,
            'created_ts': self.created_ts,
            'updated_ts': self.updated_ts,
            'total_orders': self.total_orders,
            'total_revenue_cents': self.total_revenue_cents,
            'boot_count': self.boot_count,
            'last_maintenance_ts': self.last_maintenance_ts
        }
    
    def is_online(self) -> bool:
        """是否在线"""
        return self.status == DEVICE_STATUS_ONLINE
    
    def is_maintenance_mode(self) -> bool:
        """是否处于维护模式"""
        return self.status == DEVICE_STATUS_MAINTENANCE
    
    def get_uptime_seconds(self) -> int:
        """获取运行时间（秒）"""
        now = int(datetime.now().timestamp())
        return max(0, now - self.last_seen_ts)
    
    def update_heartbeat(self):
        """更新心跳时间"""
        now_ts = int(datetime.now().timestamp())
        self.last_seen_ts = now_ts
        self.updated_ts = now_ts
        self.status = DEVICE_STATUS_ONLINE

@dataclass  
class DeviceLocation:
    """设备位置模型"""
    device_id: str
    name: str
    address: str
    lat: float = 0.0
    lng: float = 0.0
    scene: str = "office"  # office, mall, school, hospital, etc.
    updated_ts: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceLocation':
        """从字典创建位置对象"""
        return cls(
            device_id=data.get('device_id', ''),
            name=data.get('name', ''),
            address=data.get('address', ''),
            lat=float(data.get('lat', 0.0)),
            lng=float(data.get('lng', 0.0)),
            scene=data.get('scene', 'office'),
            updated_ts=int(data.get('updated_ts', 0))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'device_id': self.device_id,
            'name': self.name,
            'address': self.address,
            'lat': self.lat,
            'lng': self.lng,
            'scene': self.scene,
            'updated_ts': self.updated_ts
        }

@dataclass
class DeviceStats:
    """设备统计模型"""
    device_id: str
    date: str  # YYYY-MM-DD format
    orders_count: int = 0
    revenue_cents: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    avg_brewing_time: int = 0  # seconds
    peak_hour: int = 0  # 0-23
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceStats':
        """从字典创建统计对象"""
        return cls(
            device_id=data.get('device_id', ''),
            date=data.get('date', ''),
            orders_count=int(data.get('orders_count', 0)),
            revenue_cents=int(data.get('revenue_cents', 0)),
            successful_orders=int(data.get('successful_orders', 0)),
            failed_orders=int(data.get('failed_orders', 0)),
            avg_brewing_time=int(data.get('avg_brewing_time', 0)),
            peak_hour=int(data.get('peak_hour', 0))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'device_id': self.device_id,
            'date': self.date,
            'orders_count': self.orders_count,
            'revenue_cents': self.revenue_cents,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'avg_brewing_time': self.avg_brewing_time,
            'peak_hour': self.peak_hour
        }
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.orders_count == 0:
            return 0.0
        return self.successful_orders / self.orders_count * 100
    
    def get_avg_order_value(self) -> float:
        """获取平均订单价值（元）"""
        if self.orders_count == 0:
            return 0.0
        return self.revenue_cents / self.orders_count / 100

@dataclass
class DeviceHealth:
    """设备健康状态模型"""
    device_id: str
    status: str = "healthy"  # healthy, warning, critical
    last_check_ts: int = 0
    uptime_seconds: int = 0
    memory_usage_pct: float = 0.0
    cpu_usage_pct: float = 0.0
    disk_usage_pct: float = 0.0
    temperature: float = 0.0
    network_latency_ms: int = 0
    errors_count: int = 0
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceHealth':
        """从字典创建健康状态对象"""
        return cls(
            device_id=data.get('device_id', ''),
            status=data.get('status', 'unknown'),
            last_check_ts=int(data.get('last_check_ts', 0)),
            uptime_seconds=int(data.get('uptime_seconds', 0)),
            memory_usage_pct=float(data.get('memory_usage_pct', 0.0)),
            cpu_usage_pct=float(data.get('cpu_usage_pct', 0.0)),
            disk_usage_pct=float(data.get('disk_usage_pct', 0.0)),
            temperature=float(data.get('temperature', 0.0)),
            network_latency_ms=int(data.get('network_latency_ms', 0)),
            errors_count=int(data.get('errors_count', 0)),
            warnings=data.get('warnings', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'device_id': self.device_id,
            'status': self.status,
            'last_check_ts': self.last_check_ts,
            'uptime_seconds': self.uptime_seconds,
            'memory_usage_pct': self.memory_usage_pct,
            'cpu_usage_pct': self.cpu_usage_pct,
            'disk_usage_pct': self.disk_usage_pct,
            'temperature': self.temperature,
            'network_latency_ms': self.network_latency_ms,
            'errors_count': self.errors_count,
            'warnings': self.warnings
        }
    
    def add_warning(self, warning: str):
        """添加警告"""
        if warning not in self.warnings:
            self.warnings.append(warning)
    
    def clear_warnings(self):
        """清除警告"""
        self.warnings = []
    
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == "healthy"
    
    def update_status(self):
        """根据指标更新状态"""
        if self.errors_count > 10 or self.memory_usage_pct > 90 or self.disk_usage_pct > 90:
            self.status = "critical"
        elif (self.errors_count > 5 or self.memory_usage_pct > 80 or 
              self.cpu_usage_pct > 80 or len(self.warnings) > 0):
            self.status = "warning"
        else:
            self.status = "healthy"
