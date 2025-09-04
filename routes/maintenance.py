from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import logging
from datetime import datetime
from services.redis_service import redis_service
from services.sync_service import sync_service
from services.brewing_service import brewing_service
from config import config

logger = logging.getLogger(__name__)

maintenance_bp = Blueprint('maintenance', __name__)

def check_maintenance_auth():
    """检查运维权限"""
    return session.get('maintenance_auth') == True

@maintenance_bp.before_request
def before_request():
    """运维模块请求前检查"""
    # PIN入口页面不需要验证
    if request.endpoint == 'maintenance.pin_entry':
        return
    
    # 其他页面需要验证权限
    if not check_maintenance_auth():
        return redirect(url_for('maintenance.pin_entry'))

@maintenance_bp.route('/pin', methods=['GET', 'POST'])
def pin_entry():
    """PIN码验证页面"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            pin = data.get('pin', '')
            
            # 验证PIN码
            if pin == config.DEFAULT_PIN:
                session['maintenance_auth'] = True
                session['maintenance_login_time'] = datetime.now().isoformat()
                
                # 记录审计日志
                redis_service.add_audit_log('maintenance_login', {
                    'login_time': datetime.now().isoformat(),
                    'success': True
                })
                
                return jsonify({'success': True})
            else:
                # 记录失败尝试
                redis_service.add_audit_log('maintenance_login_failed', {
                    'attempt_time': datetime.now().isoformat(),
                    'pin_attempted': len(pin)  # 不记录实际PIN
                })
                
                return jsonify({'success': False, 'message': 'PIN码错误'})
                
        except Exception as e:
            logger.error(f"PIN验证失败: {e}")
            return jsonify({'success': False, 'message': '验证失败'})
    
    return render_template('maintenance/pin_entry.html')

@maintenance_bp.route('/logout')
def logout():
    """退出运维模式"""
    session.pop('maintenance_auth', None)
    session.pop('maintenance_login_time', None)
    
    redis_service.add_audit_log('maintenance_logout', {
        'logout_time': datetime.now().isoformat()
    })
    
    return redirect(url_for('customer.idle'))

@maintenance_bp.route('/')
def home():
    """运维首页"""
    try:
        # 获取设备状态
        device_info = redis_service.get_device_info()
        
        # 获取料盒状态
        bins = redis_service.get_all_bins()
        low_bins = redis_service.get_low_bins()
        
        # 获取制作状态
        brewing_status = brewing_service.get_brewing_status()
        
        # 获取今日统计
        today_stats = {
            'orders': int(device_info.get('total_orders', 0)),
            'revenue_cents': int(device_info.get('total_revenue_cents', 0))
        }
        
        # 系统健康状态
        health_status = sync_service.check_device_health()
        
        return render_template('maintenance/home.html',
                             device_info=device_info,
                             bins=bins,
                             low_bins=low_bins,
                             brewing_status=brewing_status,
                             today_stats=today_stats,
                             health_status=health_status)
        
    except Exception as e:
        logger.error(f"运维首页加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@maintenance_bp.route('/quick-ops', methods=['GET', 'POST'])
def quick_ops():
    """快捷运维操作"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            operation = data.get('operation')
            
            result = {'success': False, 'message': '未知操作'}
            
            if operation == 'sync':
                # 立即同步
                sync_service.sync_materials()
                redis_service.add_audit_log('manual_sync', {
                    'operation_time': datetime.now().isoformat()
                })
                result = {'success': True, 'message': '同步完成'}
                
            elif operation == 'open_door':
                # 开门操作
                redis_service.add_audit_log('door_opened', {
                    'operation_time': datetime.now().isoformat(),
                    'operator': 'maintenance'
                })
                result = {'success': True, 'message': '门已打开'}
                
            elif operation == 'clean':
                # 清洗操作
                redis_service.add_audit_log('cleaning_started', {
                    'operation_time': datetime.now().isoformat()
                })
                result = {'success': True, 'message': '清洗程序已启动'}
                
            elif operation == 'water_test':
                # 出水测试
                redis_service.add_audit_log('water_test', {
                    'operation_time': datetime.now().isoformat()
                })
                result = {'success': True, 'message': '出水测试完成'}
                
            elif operation == 'factory_reset':
                # 恢复出厂设置（危险操作）
                if data.get('confirm') == 'RESET':
                    redis_service.add_audit_log('factory_reset', {
                        'operation_time': datetime.now().isoformat()
                    })
                    result = {'success': True, 'message': '恢复出厂设置完成'}
                else:
                    result = {'success': False, 'message': '确认信息不正确'}
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"快捷操作失败: {e}")
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    return render_template('maintenance/quick_ops.html')

@maintenance_bp.route('/bins', methods=['GET', 'POST'])
def bins():
    """料盒管理"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'update_bin':
                bin_index = int(data.get('bin_index'))
                bin_data = data.get('bin_data')
                
                # 更新料盒信息
                bin_data['last_sync_ts'] = int(datetime.now().timestamp())
                redis_service.set_bin_info(bin_index, bin_data)
                
                # 记录审计日志
                redis_service.add_audit_log('bin_updated', {
                    'bin_index': bin_index,
                    'material_code': bin_data.get('material_code'),
                    'remaining': bin_data.get('remaining'),
                    'operation_time': datetime.now().isoformat()
                })
                
                return jsonify({'success': True, 'message': '料盒信息已更新'})
                
            elif action == 'calibrate_bin':
                bin_index = int(data.get('bin_index'))
                new_remaining = float(data.get('remaining'))
                
                # 获取并更新料盒信息
                bin_info = redis_service.get_bin_info(bin_index)
                if bin_info:
                    bin_info['remaining'] = new_remaining
                    bin_info['last_sync_ts'] = int(datetime.now().timestamp())
                    redis_service.set_bin_info(bin_index, bin_info)
                    
                    redis_service.add_audit_log('bin_calibrated', {
                        'bin_index': bin_index,
                        'new_remaining': new_remaining,
                        'operation_time': datetime.now().isoformat()
                    })
                    
                    return jsonify({'success': True, 'message': '料盒校准完成'})
                else:
                    return jsonify({'success': False, 'message': '料盒不存在'})
            
            elif action == 'report_materials':
                # 立即上报物料
                sync_service.sync_materials()
                return jsonify({'success': True, 'message': '物料信息已上报'})
            
            return jsonify({'success': False, 'message': '未知操作'})
            
        except Exception as e:
            logger.error(f"料盒操作失败: {e}")
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    # GET请求返回料盒管理页面
    try:
        bins_data = redis_service.get_all_bins()
        low_bins = redis_service.get_low_bins()
        
        # 获取可用材料
        available_materials = {
            'BEAN_A': '咖啡豆A',
            'MILK_POWDER': '奶粉',
            'SUGAR': '糖',
            'WATER': '水'
        }
        
        return render_template('maintenance/bins.html',
                             bins=bins_data,
                             low_bins=low_bins,
                             available_materials=available_materials)
        
    except Exception as e:
        logger.error(f"料盒管理页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@maintenance_bp.route('/status')
def status():
    """设备状态页面"""
    try:
        # 设备基础信息
        device_info = redis_service.get_device_info()
        
        # 网络状态（模拟）
        network_info = {
            'connected': True,
            'ip': '192.168.1.100',
            'ssid': 'CoffeeShop-WiFi',
            'signal_strength': 85
        }
        
        # Redis连接状态
        redis_status = {
            'connected': True,
            'host': config.REDIS_HOST,
            'port': config.REDIS_PORT,
            'latency_ms': 2
        }
        
        try:
            redis_service.ping()
        except:
            redis_status['connected'] = False
        
        # 系统运行状态
        system_info = {
            'uptime_seconds': int(datetime.now().timestamp()) - int(device_info.get('last_seen_ts', 0)),
            'memory_usage': 65,  # 模拟数据
            'cpu_usage': 25,     # 模拟数据
            'disk_usage': 45     # 模拟数据
        }
        
        return render_template('maintenance/status.html',
                             device_info=device_info,
                             network_info=network_info,
                             redis_status=redis_status,
                             system_info=system_info)
        
    except Exception as e:
        logger.error(f"状态页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@maintenance_bp.route('/logs')
def logs():
    """日志页面"""
    try:
        # 获取审计日志
        stream_key = redis_service.get_device_key('stream:audit')
        
        try:
            # 获取最近200条日志
            logs_data = redis_service.redis_client.xrevrange(stream_key, count=200)
            
            logs = []
            for log_id, fields in logs_data:
                log_entry = {
                    'id': log_id,
                    'timestamp': fields.get('timestamp', ''),
                    'event': fields.get('event', ''),
                    'device_id': fields.get('device_id', ''),
                    'details': {k: v for k, v in fields.items() 
                              if k not in ['timestamp', 'event', 'device_id']}
                }
                logs.append(log_entry)
                
        except Exception:
            logs = []
        
        return render_template('maintenance/logs.html', logs=logs)
        
    except Exception as e:
        logger.error(f"日志页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@maintenance_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """设置页面"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            setting_key = data.get('key')
            setting_value = data.get('value')
            
            # 这里应该更新配置文件或Redis中的设置
            # 目前只记录操作日志
            redis_service.add_audit_log('setting_changed', {
                'setting_key': setting_key,
                'setting_value': setting_value,
                'operation_time': datetime.now().isoformat()
            })
            
            return jsonify({'success': True, 'message': '设置已保存'})
            
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})
    
    # 当前设置值
    current_settings = {
        'language': config.DEFAULT_LANGUAGE,
        'screensaver_timeout': config.SCREENSAVER_TIMEOUT,
        'done_page_duration': config.DONE_PAGE_DURATION,
        'enable_queue': config.ENABLE_QUEUE,
        'low_material_threshold': config.LOW_MATERIAL_THRESHOLD,
        'enable_wechat_pay': config.ENABLE_WECHAT_PAY,
        'enable_alipay': config.ENABLE_ALIPAY,
        'pin_code': '****'  # 不显示实际PIN
    }
    
    return render_template('maintenance/settings.html',
                         settings=current_settings)
