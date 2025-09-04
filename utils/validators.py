"""验证器工具"""

import re
from typing import Any, Dict, List, Optional, Union
from utils.constants import *

class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)

def validate_device_id(device_id: str) -> bool:
    """验证设备ID"""
    if not device_id:
        return False
    
    if not isinstance(device_id, str):
        return False
    
    if not re.match(REGEX_DEVICE_ID, device_id):
        return False
    
    return True

def validate_order_id(order_id: str) -> bool:
    """验证订单ID"""
    if not order_id:
        return False
    
    if not isinstance(order_id, str):
        return False
    
    if not re.match(REGEX_ORDER_ID, order_id):
        return False
    
    return True

def validate_command_id(command_id: str) -> bool:
    """验证命令ID"""
    if not command_id:
        return False
    
    if not isinstance(command_id, str):
        return False
    
    if not re.match(REGEX_COMMAND_ID, command_id):
        return False
    
    return True

def validate_amount_cents(amount_cents: Union[int, str]) -> bool:
    """验证金额（分）"""
    try:
        amount = int(amount_cents)
        return 0 <= amount <= 999999  # 最大9999.99元
    except (ValueError, TypeError):
        return False

def validate_bin_index(bin_index: Union[int, str]) -> bool:
    """验证料盒索引"""
    try:
        index = int(bin_index)
        return 0 <= index <= 9  # 支持0-9个料盒
    except (ValueError, TypeError):
        return False

def validate_material_code(material_code: str) -> bool:
    """验证物料代码"""
    if not material_code:
        return False
    
    valid_codes = [MATERIAL_BEAN_A, MATERIAL_MILK_POWDER, MATERIAL_SUGAR, MATERIAL_WATER]
    return material_code in valid_codes

def validate_payment_method(payment_method: str) -> bool:
    """验证支付方式"""
    if not payment_method:
        return False
    
    valid_methods = [PAYMENT_METHOD_WECHAT, PAYMENT_METHOD_ALIPAY]
    return payment_method in valid_methods

def validate_recipe_id(recipe_id: str) -> bool:
    """验证配方ID"""
    if not recipe_id:
        return False
    
    if not isinstance(recipe_id, str):
        return False
    
    # 配方ID应该是3位数字
    return re.match(r'^\d{3}$', recipe_id) is not None

def validate_percentage(value: Union[int, float, str]) -> bool:
    """验证百分比值（0-100）"""
    try:
        pct = float(value)
        return 0 <= pct <= 100
    except (ValueError, TypeError):
        return False

def validate_timestamp(timestamp: Union[int, str]) -> bool:
    """验证时间戳"""
    try:
        ts = int(timestamp)
        # 验证时间戳在合理范围内（2020年到2030年）
        return 1577836800 <= ts <= 1893456000
    except (ValueError, TypeError):
        return False

def validate_pin_code(pin: str) -> bool:
    """验证PIN码"""
    if not pin:
        return False
    
    if not isinstance(pin, str):
        return False
    
    # PIN码应该是4位数字
    return re.match(r'^\d{4}$', pin) is not None

def validate_email(email: str) -> bool:
    """验证邮箱地址"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """验证手机号码"""
    if not phone:
        return False
    
    # 中国手机号码格式
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

def validate_order_data(order_data: Dict[str, Any]) -> List[str]:
    """验证订单数据"""
    errors = []
    
    # 必填字段
    required_fields = ['order_id', 'recipe_id', 'amount_cents']
    for field in required_fields:
        if field not in order_data:
            errors.append(f"缺少必填字段: {field}")
    
    # 验证订单ID
    if 'order_id' in order_data and not validate_order_id(order_data['order_id']):
        errors.append("订单ID格式无效")
    
    # 验证配方ID
    if 'recipe_id' in order_data and not validate_recipe_id(order_data['recipe_id']):
        errors.append("配方ID格式无效")
    
    # 验证金额
    if 'amount_cents' in order_data and not validate_amount_cents(order_data['amount_cents']):
        errors.append("金额格式无效")
    
    # 验证支付方式（可选）
    if 'payment_method' in order_data and not validate_payment_method(order_data['payment_method']):
        errors.append("支付方式无效")
    
    return errors

def validate_bin_data(bin_data: Dict[str, Any]) -> List[str]:
    """验证料盒数据"""
    errors = []
    
    # 必填字段
    required_fields = ['material_code', 'remaining', 'capacity']
    for field in required_fields:
        if field not in bin_data:
            errors.append(f"缺少必填字段: {field}")
    
    # 验证物料代码
    if 'material_code' in bin_data and not validate_material_code(bin_data['material_code']):
        errors.append("物料代码无效")
    
    # 验证剩余量
    if 'remaining' in bin_data:
        try:
            remaining = float(bin_data['remaining'])
            if remaining < 0:
                errors.append("剩余量不能为负数")
        except (ValueError, TypeError):
            errors.append("剩余量格式无效")
    
    # 验证容量
    if 'capacity' in bin_data:
        try:
            capacity = float(bin_data['capacity'])
            if capacity <= 0:
                errors.append("容量必须大于0")
        except (ValueError, TypeError):
            errors.append("容量格式无效")
    
    # 验证阈值百分比（可选）
    if 'threshold_low_pct' in bin_data and not validate_percentage(bin_data['threshold_low_pct']):
        errors.append("低量阈值百分比格式无效")
    
    return errors

def validate_command_data(command_data: Dict[str, Any]) -> List[str]:
    """验证命令数据"""
    errors = []
    
    # 必填字段
    required_fields = ['command_id', 'type']
    for field in required_fields:
        if field not in command_data:
            errors.append(f"缺少必填字段: {field}")
    
    # 验证命令ID
    if 'command_id' in command_data and not validate_command_id(command_data['command_id']):
        errors.append("命令ID格式无效")
    
    # 验证命令类型
    if 'type' in command_data:
        valid_types = [COMMAND_TYPE_BREW, COMMAND_TYPE_OPEN_DOOR, COMMAND_TYPE_CLEAN, 
                      COMMAND_TYPE_UPGRADE, COMMAND_TYPE_SYNC]
        if command_data['type'] not in valid_types:
            errors.append("命令类型无效")
    
    return errors

def sanitize_string(value: str, max_length: int = 255) -> str:
    """字符串清理和截断"""
    if not isinstance(value, str):
        return str(value)
    
    # 移除控制字符
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', value)
    
    # 截断长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()

def sanitize_html(value: str) -> str:
    """HTML字符串清理"""
    if not isinstance(value, str):
        return str(value)
    
    # 简单的HTML转义
    html_escape = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    
    result = value
    for char, escape in html_escape.items():
        result = result.replace(char, escape)
    
    return result

class DataValidator:
    """数据验证器类"""
    
    def __init__(self):
        self.errors = []
    
    def add_error(self, field: str, message: str):
        """添加验证错误"""
        self.errors.append({'field': field, 'message': message})
    
    def clear_errors(self):
        """清除错误"""
        self.errors = []
    
    def has_errors(self) -> bool:
        """是否有验证错误"""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[Dict[str, str]]:
        """获取验证错误"""
        return self.errors
    
    def validate_required(self, data: Dict[str, Any], fields: List[str]):
        """验证必填字段"""
        for field in fields:
            if field not in data or data[field] is None or data[field] == '':
                self.add_error(field, f"{field}是必填字段")
    
    def validate_type(self, value: Any, expected_type: type, field: str):
        """验证数据类型"""
        if value is not None and not isinstance(value, expected_type):
            self.add_error(field, f"{field}类型错误，期望{expected_type.__name__}")
    
    def validate_range(self, value: Union[int, float], min_val: Union[int, float], 
                      max_val: Union[int, float], field: str):
        """验证数值范围"""
        if value is not None:
            if value < min_val or value > max_val:
                self.add_error(field, f"{field}超出范围[{min_val}, {max_val}]")
    
    def validate_length(self, value: str, min_len: int, max_len: int, field: str):
        """验证字符串长度"""
        if value is not None:
            length = len(value)
            if length < min_len or length > max_len:
                self.add_error(field, f"{field}长度超出范围[{min_len}, {max_len}]")
    
    def validate_regex(self, value: str, pattern: str, field: str, message: str = None):
        """验证正则表达式"""
        if value is not None:
            if not re.match(pattern, value):
                self.add_error(field, message or f"{field}格式不正确")
    
    def validate_enum(self, value: Any, valid_values: List[Any], field: str):
        """验证枚举值"""
        if value is not None and value not in valid_values:
            self.add_error(field, f"{field}值无效，有效值: {valid_values}")
