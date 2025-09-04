import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config import config
from services.redis_service import redis_service

logger = logging.getLogger(__name__)

class PaymentService:
    """支付服务类"""
    
    def __init__(self):
        self.active_payments = {}  # 临时存储活跃支付会话
    
    def create_payment(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建支付会话"""
        try:
            order_id = order_data.get('order_id') or str(uuid.uuid4())
            amount_cents = order_data['amount_cents']
            payment_method = order_data.get('payment_method', 'wechat')
            
            # 创建支付会话
            payment_session = {
                'order_id': order_id,
                'amount_cents': amount_cents,
                'payment_method': payment_method,
                'status': 'pending',
                'created_ts': int(datetime.now().timestamp()),
                'expire_ts': int((datetime.now() + timedelta(seconds=config.PAYMENT_TIMEOUT)).timestamp()),
                'qr_code': self.generate_qr_code(order_id, amount_cents, payment_method)
            }
            
            # 存储到临时会话
            self.active_payments[order_id] = payment_session
            
            # 发布支付创建事件
            redis_service.publish_event('payment_created', {
                'order_id': order_id,
                'amount_cents': amount_cents,
                'payment_method': payment_method
            })
            
            logger.info(f"创建支付会话: {order_id}, 金额: {amount_cents}分")
            return payment_session
            
        except Exception as e:
            logger.error(f"创建支付会话失败: {e}")
            raise
    
    def generate_qr_code(self, order_id: str, amount_cents: int, payment_method: str) -> str:
        """生成支付二维码"""
        # 这里应该调用实际的支付API生成二维码
        # 目前返回模拟的二维码数据
        
        if payment_method == 'wechat':
            # 微信支付二维码生成逻辑
            qr_data = f"weixin://wxpay/bizpayurl?pr={order_id}_{amount_cents}"
        elif payment_method == 'alipay':
            # 支付宝支付二维码生成逻辑  
            qr_data = f"https://qr.alipay.com/{order_id}_{amount_cents}"
        else:
            raise ValueError(f"不支持的支付方式: {payment_method}")
        
        return qr_data
    
    def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """检查支付状态"""
        try:
            if order_id not in self.active_payments:
                return {'status': 'not_found'}
            
            payment_session = self.active_payments[order_id]
            current_ts = int(datetime.now().timestamp())
            
            # 检查是否超时
            if current_ts > payment_session['expire_ts']:
                payment_session['status'] = 'timeout'
                self.cleanup_payment(order_id)
                return payment_session
            
            # 这里应该调用实际的支付API检查状态
            # 目前返回模拟状态检查
            payment_status = self.simulate_payment_check(order_id, payment_session)
            payment_session['status'] = payment_status
            
            # 如果支付成功或失败，清理会话
            if payment_status in ['paid', 'failed', 'cancelled']:
                if payment_status == 'paid':
                    self.handle_payment_success(order_id, payment_session)
                else:
                    self.handle_payment_failure(order_id, payment_session, payment_status)
                
                self.cleanup_payment(order_id)
            
            return payment_session
            
        except Exception as e:
            logger.error(f"检查支付状态失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def simulate_payment_check(self, order_id: str, payment_session: Dict[str, Any]) -> str:
        """模拟支付状态检查（开发用）"""
        # 在真实环境中，这里会调用微信支付或支付宝的API
        created_ts = payment_session['created_ts']
        current_ts = int(datetime.now().timestamp())
        elapsed = current_ts - created_ts
        
        # 模拟：30秒内随机成功，超过30秒视为超时
        if elapsed < 30:
            # 模拟20%概率支付成功
            import random
            if random.random() < 0.2:
                return 'paid'
            else:
                return 'pending'
        else:
            return 'timeout'
    
    def handle_payment_success(self, order_id: str, payment_session: Dict[str, Any]):
        """处理支付成功"""
        try:
            # 更新支付会话
            payment_session.update({
                'status': 'paid',
                'paid_ts': int(datetime.now().timestamp()),
                'txn_id': f"txn_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            })
            
            # 发布支付成功事件
            redis_service.publish_event('pay_update', {
                'order_id': order_id,
                'status': 'paid',
                'txn_id': payment_session['txn_id'],
                'amount_cents': payment_session['amount_cents']
            })
            
            logger.info(f"支付成功: {order_id}, 交易ID: {payment_session['txn_id']}")
            
        except Exception as e:
            logger.error(f"处理支付成功失败: {e}")
    
    def handle_payment_failure(self, order_id: str, payment_session: Dict[str, Any], reason: str):
        """处理支付失败"""
        try:
            # 更新支付会话
            payment_session.update({
                'status': reason,
                'failed_ts': int(datetime.now().timestamp()),
                'failure_reason': reason
            })
            
            # 发布支付失败事件
            redis_service.publish_event('pay_update', {
                'order_id': order_id,
                'status': reason,
                'reason': reason
            })
            
            logger.info(f"支付失败: {order_id}, 原因: {reason}")
            
        except Exception as e:
            logger.error(f"处理支付失败失败: {e}")
    
    def cancel_payment(self, order_id: str) -> bool:
        """取消支付"""
        try:
            if order_id not in self.active_payments:
                return False
            
            payment_session = self.active_payments[order_id]
            
            if payment_session['status'] != 'pending':
                return False
            
            # 这里应该调用实际的支付API取消订单
            self.handle_payment_failure(order_id, payment_session, 'cancelled')
            self.cleanup_payment(order_id)
            
            logger.info(f"取消支付: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消支付失败: {e}")
            return False
    
    def cleanup_payment(self, order_id: str):
        """清理支付会话"""
        if order_id in self.active_payments:
            del self.active_payments[order_id]
    
    def cleanup_expired_payments(self):
        """清理过期的支付会话"""
        current_ts = int(datetime.now().timestamp())
        expired_orders = []
        
        for order_id, payment_session in self.active_payments.items():
            if current_ts > payment_session['expire_ts'] and payment_session['status'] == 'pending':
                expired_orders.append(order_id)
        
        for order_id in expired_orders:
            self.handle_payment_failure(order_id, self.active_payments[order_id], 'timeout')
            self.cleanup_payment(order_id)
        
        if expired_orders:
            logger.info(f"清理过期支付会话: {len(expired_orders)}个")
    
    def get_payment_methods(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的支付方式"""
        methods = {}
        
        if config.ENABLE_WECHAT_PAY:
            methods['wechat'] = {
                'name': '微信支付',
                'icon': 'wechat-pay.png',
                'available': bool(config.WECHAT_APP_ID),
                'reason': '' if config.WECHAT_APP_ID else '未配置微信支付'
            }
        
        if config.ENABLE_ALIPAY:
            methods['alipay'] = {
                'name': '支付宝',
                'icon': 'alipay.png',
                'available': bool(config.ALIPAY_APP_ID),
                'reason': '' if config.ALIPAY_APP_ID else '未配置支付宝'
            }
        
        return methods
    
    def is_payment_available(self) -> bool:
        """检查是否有可用的支付方式"""
        methods = self.get_payment_methods()
        return any(method['available'] for method in methods.values())

# 创建全局实例
payment_service = PaymentService()
