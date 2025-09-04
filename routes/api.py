from flask import Blueprint, request, jsonify
import logging
import uuid
from datetime import datetime
from services.redis_service import redis_service
from services.payment_service import payment_service
from services.brewing_service import brewing_service
from services.menu_service import menu_service

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/payment/status/<order_id>')
def payment_status(order_id):
    """检查支付状态API"""
    try:
        status = payment_service.check_payment_status(order_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"检查支付状态失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/payment/cancel/<order_id>', methods=['POST'])
def cancel_payment(order_id):
    """取消支付API"""
    try:
        success = payment_service.cancel_payment(order_id)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"取消支付失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/brew/start', methods=['POST'])
def start_brewing():
    """开始制作API"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        recipe_id = data.get('recipe_id')
        
        if not order_id or not recipe_id:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        result = brewing_service.start_brewing(order_id, recipe_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"开始制作失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/brew/status')
def brewing_status():
    """获取制作状态API"""
    try:
        status = brewing_service.get_brewing_status()
        return jsonify({'status': status})
    except Exception as e:
        logger.error(f"获取制作状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/brew/stop', methods=['POST'])
def stop_brewing():
    """停止制作API"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        success = brewing_service.stop_brewing(order_id)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"停止制作失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/recipes')
def get_recipes():
    """获取所有配方API"""
    try:
        recipes = redis_service.get_all_recipes()
        
        # 添加可用性信息
        for recipe_id, recipe_data in recipes.items():
            availability = brewing_service.check_recipe_availability(recipe_id)
            recipe_data['available'] = availability['available']
            recipe_data['availability_reason'] = availability.get('reason', '')
            recipe_data['missing_materials'] = availability.get('missing_materials', [])
        
        return jsonify(recipes)
        
    except Exception as e:
        logger.error(f"获取配方失败: {e}")
        return jsonify({'error': str(e)}), 500

# 新菜单读取 API（设备端使用）
@api_bp.route('/v1/devices/<device_id>/menu')
def api_device_menu(device_id):
    try:
        data = menu_service.get_menu(device_id)
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        logger.error(f"读取菜单失败: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@api_bp.route('/v1/devices/<device_id>/menu/available')
def api_device_menu_available(device_id):
    try:
        avail = list(menu_service.get_available_set(device_id))
        return jsonify({'ok': True, 'data': avail})
    except Exception as e:
        logger.error(f"读取可售集合失败: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@api_bp.route('/recipes/<recipe_id>/availability')
def recipe_availability(recipe_id):
    """检查配方可用性API"""
    try:
        availability = brewing_service.check_recipe_availability(recipe_id)
        return jsonify(availability)
    except Exception as e:
        logger.error(f"检查配方可用性失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/bins')
def get_bins():
    """获取料盒信息API"""
    try:
        bins = redis_service.get_all_bins()
        low_bins = redis_service.get_low_bins()
        
        return jsonify({
            'bins': bins,
            'low_bins': low_bins
        })
        
    except Exception as e:
        logger.error(f"获取料盒信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/device/status')
def device_status():
    """获取设备状态API"""
    try:
        device_info = redis_service.get_device_info()
        brewing_status = brewing_service.get_brewing_status()
        
        return jsonify({
            'device': device_info,
            'brewing': brewing_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/orders', methods=['POST'])
def create_order():
    """创建订单API"""
    try:
        data = request.get_json()
        
        # 生成订单ID
        order_id = data.get('order_id', str(uuid.uuid4()))
        
        # 订单数据
        order_data = {
            'order_id': order_id,
            'recipe_id': data.get('recipe_id'),
            'recipe_name': data.get('recipe_name'),
            'amount_cents': data.get('amount_cents'),
            'options': data.get('options', {}),
            'status': 'created',
            'created_ts': int(datetime.now().timestamp())
        }
        
        # 保存订单
        redis_service.create_order(order_data)
        
        return jsonify({'success': True, 'order_id': order_id})
        
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/orders/<order_id>')
def get_order(order_id):
    """获取订单信息API"""
    try:
        order_data = redis_service.get_order(order_id)
        if not order_data:
            return jsonify({'error': '订单不存在'}), 404
        
        return jsonify(order_data)
        
    except Exception as e:
        logger.error(f"获取订单失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/commands/claim', methods=['POST'])
def claim_command():
    """认领命令API（用于远程命令处理）"""
    try:
        data = request.get_json()
        command_id = data.get('command_id')
        
        if not command_id:
            return jsonify({'success': False, 'message': '命令ID不能为空'}), 400
        
        command_data = redis_service.claim_command(command_id)
        
        if command_data:
            return jsonify({'success': True, 'command': command_data})
        else:
            return jsonify({'success': False, 'message': '命令不存在或已被处理'})
        
    except Exception as e:
        logger.error(f"认领命令失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/commands/<command_id>/complete', methods=['POST'])
def complete_command(command_id):
    """完成命令API"""
    try:
        data = request.get_json()
        success = data.get('success', False)
        result = data.get('result')
        error = data.get('error')
        
        redis_service.complete_command(command_id, success, result, error)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"完成命令失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.errorhandler(404)
def api_not_found(error):
    """API 404错误处理"""
    return jsonify({'error': 'API接口不存在'}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """API 500错误处理"""
    logger.error(f"API内部错误: {error}")
    return jsonify({'error': '内部服务器错误'}), 500
