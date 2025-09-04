import logging
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from config import config
from services.redis_service import redis_service

logger = logging.getLogger(__name__)

class BrewingService:
    """咖啡制作服务类"""
    
    def __init__(self):
        self.current_brewing = None
        self.is_busy = False
        self.brewing_lock = threading.Lock()
    
    def can_brew(self) -> Dict[str, Any]:
        """检查是否可以制作"""
        try:
            # 检查是否正在制作
            if self.is_busy:
                return {
                    'can_brew': False,
                    'reason': 'device_busy',
                    'message': '设备正在制作中'
                }
            
            # 检查设备状态
            device_info = redis_service.get_device_info()
            if device_info.get('status') != 'online':
                return {
                    'can_brew': False,
                    'reason': 'device_offline',
                    'message': '设备离线'
                }
            
            # 检查是否在维护模式
            if device_info.get('maintenance_mode'):
                return {
                    'can_brew': False,
                    'reason': 'maintenance_mode',
                    'message': '设备正在维护'
                }
            
            return {
                'can_brew': True,
                'reason': 'ok',
                'message': '可以制作'
            }
            
        except Exception as e:
            logger.error(f"检查制作状态失败: {e}")
            return {
                'can_brew': False,
                'reason': 'error',
                'message': f'检查失败: {str(e)}'
            }
    
    def check_recipe_availability(self, recipe_id: str) -> Dict[str, Any]:
        """检查配方可制作性"""
        try:
            # 获取配方信息
            recipe_data = redis_service.get_recipe(recipe_id)
            if not recipe_data:
                return {
                    'available': False,
                    'reason': 'recipe_not_found',
                    'message': '配方不存在',
                    'missing_materials': []
                }
            
            # 检查配方是否激活（从 cm:dict:recipe 获取）
            def _truthy(v):
                if v is None:
                    return None
                if isinstance(v, bool):
                    return v
                s = str(v).strip().lower()
                if s in ('1', 'true', 'yes', 'on', 'active', 'enabled'):
                    return True
                if s in ('0', 'false', 'no', 'off', 'inactive', 'disabled'):
                    return False
                try:
                    return float(s) != 0.0
                except Exception:
                    return None

            active_flag = recipe_data.get('active')
            status_flag = recipe_data.get('status')
            active = _truthy(active_flag)
            if active is None and status_flag is not None:
                active = str(status_flag).strip().lower() in ('active', 'enabled', 'on', '1', 'true', 'yes')
            if active is False:
                return {
                    'available': False,
                    'reason': 'recipe_inactive',
                    'message': '配方未激活',
                    'missing_materials': []
                }
            
            # 检查物料是否充足
            required_materials = recipe_data.get('materials', {})
            bins = redis_service.get_all_bins()
            missing_materials = []
            
            for material_code, required_amount in required_materials.items():
                # 找到对应的料盒
                material_bin = None
                for bin_index, bin_info in bins.items():
                    if bin_info.get('material_code') == material_code:
                        material_bin = bin_info
                        break
                
                if not material_bin:
                    missing_materials.append({
                        'material_code': material_code,
                        'required': required_amount,
                        'available': 0,
                        'reason': 'bin_not_found'
                    })
                    continue
                
                available_amount = float(material_bin.get('remaining', 0))
                if available_amount < required_amount:
                    missing_materials.append({
                        'material_code': material_code,
                        'required': required_amount,
                        'available': available_amount,
                        'reason': 'insufficient'
                    })
            
            if missing_materials:
                return {
                    'available': False,
                    'reason': 'insufficient_materials',
                    'message': '物料不足',
                    'missing_materials': missing_materials
                }
            
            return {
                'available': True,
                'reason': 'ok',
                'message': '可以制作',
                'missing_materials': []
            }
            
        except Exception as e:
            logger.error(f"检查配方可用性失败: {e}")
            return {
                'available': False,
                'reason': 'error',
                'message': f'检查失败: {str(e)}',
                'missing_materials': []
            }
    
    def start_brewing(self, order_id: str, recipe_id: str) -> Dict[str, Any]:
        """开始制作咖啡"""
        with self.brewing_lock:
            try:
                # 检查是否可以制作
                can_brew_result = self.can_brew()
                if not can_brew_result['can_brew']:
                    return {
                        'success': False,
                        'reason': can_brew_result['reason'],
                        'message': can_brew_result['message']
                    }
                
                # 检查配方可用性
                availability_result = self.check_recipe_availability(recipe_id)
                if not availability_result['available']:
                    return {
                        'success': False,
                        'reason': availability_result['reason'],
                        'message': availability_result['message'],
                        'missing_materials': availability_result.get('missing_materials', [])
                    }
                
                # 设置制作状态
                self.is_busy = True
                self.current_brewing = {
                    'order_id': order_id,
                    'recipe_id': recipe_id,
                    'start_ts': int(datetime.now().timestamp()),
                    'status': 'brewing',
                    'current_step': 0,
                    'progress_pct': 0
                }
                
                # 扣减物料
                self.consume_materials(recipe_id)
                
                # 启动制作线程
                brewing_thread = threading.Thread(
                    target=self.brewing_process,
                    args=(order_id, recipe_id),
                    daemon=True
                )
                brewing_thread.start()
                
                # 发布制作开始事件
                redis_service.publish_event('brew_start', {
                    'order_id': order_id,
                    'recipe_id': recipe_id
                })
                
                logger.info(f"开始制作: {order_id}, 配方: {recipe_id}")
                return {
                    'success': True,
                    'reason': 'ok',
                    'message': '制作开始'
                }
                
            except Exception as e:
                self.is_busy = False
                self.current_brewing = None
                logger.error(f"开始制作失败: {e}")
                return {
                    'success': False,
                    'reason': 'error',
                    'message': f'制作启动失败: {str(e)}'
                }
    
    def brewing_process(self, order_id: str, recipe_id: str):
        """制作流程处理"""
        try:
            # 获取配方信息
            recipe_data = redis_service.get_recipe(recipe_id)
            recipe_name = recipe_data.get('name', '未知饮品')
            
            # 制作步骤
            steps = [
                {'name': '准备原料', 'duration': 3, 'progress': 10},
                {'name': '研磨咖啡豆', 'duration': 8, 'progress': 30},
                {'name': '加热水温', 'duration': 5, 'progress': 50},
                {'name': '咖啡萃取', 'duration': 15, 'progress': 80},
                {'name': '添加配料', 'duration': 4, 'progress': 95},
                {'name': '完成制作', 'duration': 2, 'progress': 100}
            ]
            
            total_duration = sum(step['duration'] for step in steps)
            elapsed_time = 0
            
            for i, step in enumerate(steps):
                if not self.current_brewing:  # 检查是否被中断
                    return
                
                # 更新当前步骤
                self.current_brewing.update({
                    'current_step': i,
                    'step_name': step['name'],
                    'progress_pct': step['progress'],
                    'eta_s': total_duration - elapsed_time
                })
                
                # 发布进度更新事件
                redis_service.publish_event('brew_progress', {
                    'order_id': order_id,
                    'step': step['name'],
                    'step_index': i,
                    'total_steps': len(steps),
                    'pct': step['progress'],
                    'eta_s': total_duration - elapsed_time
                })
                
                logger.debug(f"制作进度: {order_id} - {step['name']} ({step['progress']}%)")
                
                # 模拟制作时间
                time.sleep(step['duration'])
                elapsed_time += step['duration']
            
            # 制作完成
            self.complete_brewing(order_id, True)
            
        except Exception as e:
            logger.error(f"制作过程失败: {e}")
            self.complete_brewing(order_id, False, str(e))
    
    def complete_brewing(self, order_id: str, success: bool, error: Optional[str] = None):
        """完成制作"""
        with self.brewing_lock:
            try:
                if not self.current_brewing:
                    return
                
                # 更新制作状态
                self.current_brewing.update({
                    'status': 'completed' if success else 'failed',
                    'completed_ts': int(datetime.now().timestamp()),
                    'success': success
                })
                
                if error:
                    self.current_brewing['error'] = error
                
                # 发布制作完成事件
                redis_service.publish_event('brew_done', {
                    'order_id': order_id,
                    'ok': success,
                    'error': error
                })
                
                # 重置状态
                self.is_busy = False
                self.current_brewing = None
                
                if success:
                    logger.info(f"制作完成: {order_id}")
                else:
                    logger.error(f"制作失败: {order_id}, 错误: {error}")
                
            except Exception as e:
                logger.error(f"完成制作处理失败: {e}")
                self.is_busy = False
                self.current_brewing = None
    
    def consume_materials(self, recipe_id: str):
        """消耗物料"""
        try:
            # 获取配方所需物料
            recipe_data = redis_service.get_recipe(recipe_id)
            required_materials = recipe_data.get('materials', {})
            
            # 获取所有料盒
            bins = redis_service.get_all_bins()
            
            # 扣减每种物料
            for material_code, required_amount in required_materials.items():
                # 找到对应的料盒
                for bin_index, bin_info in bins.items():
                    if bin_info.get('material_code') == material_code:
                        current_remaining = float(bin_info.get('remaining', 0))
                        new_remaining = max(0, current_remaining - required_amount)
                        
                        # 更新料盒信息
                        bin_info['remaining'] = new_remaining
                        bin_info['last_sync_ts'] = int(datetime.now().timestamp())
                        
                        redis_service.set_bin_info(bin_index, bin_info)
                        
                        # 发布物料更新事件
                        capacity = float(bin_info.get('capacity', 100))
                        pct = (new_remaining / capacity * 100) if capacity > 0 else 0
                        threshold = float(bin_info.get('threshold_low_pct', 20))
                        
                        redis_service.publish_event('material_update', {
                            'bin_index': bin_index,
                            'material_code': material_code,
                            'remaining': new_remaining,
                            'pct': pct,
                            'low': pct < threshold
                        })
                        
                        logger.debug(f"消耗物料: {material_code} -{required_amount}, 剩余: {new_remaining}")
                        break
            
        except Exception as e:
            logger.error(f"消耗物料失败: {e}")
    
    def get_brewing_status(self) -> Optional[Dict[str, Any]]:
        """获取当前制作状态"""
        return self.current_brewing.copy() if self.current_brewing else None
    
    def stop_brewing(self, order_id: str = None) -> bool:
        """停止制作"""
        with self.brewing_lock:
            try:
                if not self.current_brewing:
                    return False
                
                if order_id and self.current_brewing.get('order_id') != order_id:
                    return False
                
                # 停止制作
                current_order_id = self.current_brewing.get('order_id')
                self.complete_brewing(current_order_id, False, '制作被中断')
                
                logger.info(f"停止制作: {current_order_id}")
                return True
                
            except Exception as e:
                logger.error(f"停止制作失败: {e}")
                return False

# 创建全局实例
brewing_service = BrewingService()
