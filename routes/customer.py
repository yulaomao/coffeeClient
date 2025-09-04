from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import json
import uuid
import logging
from datetime import datetime
from services.redis_service import redis_service
from services.payment_service import payment_service
from services.brewing_service import brewing_service
from services.menu_service import menu_service
from config import config

logger = logging.getLogger(__name__)

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/')
def idle():
    """吸引屏（首页）"""
    try:
        # 检查设备状态
        device_info = redis_service.get_device_info()
        device_status = device_info.get('status', 'offline')
        
        # 检查是否有低料
        low_bins = redis_service.get_low_bins()
        
        # 检查制作状态
        brewing_status = brewing_service.get_brewing_status()
        is_brewing = brewing_status is not None
        
        # 如果设备不可用，显示停服页面
        if device_status != 'online' or len(low_bins) > 2:  # 超过2个料盒低料
            return render_template('customer/out_of_service.html',
                                 reason='maintenance' if device_status != 'online' else 'low_materials',
                                 low_bins_count=len(low_bins))
        
        # 如果正在制作，显示制作页面
        if is_brewing:
            return redirect(url_for('customer.brewing', order_id=brewing_status['order_id']))
        
        return render_template('customer/idle.html', 
                             device_info=device_info)
        
    except Exception as e:
        logger.error(f"首页加载失败: {e}")
        return render_template('error.html', 
                             error_code=500, 
                             error_message='页面加载失败'), 500

@customer_bp.route('/menu')
def menu():
    """菜单页面（按设备菜单结构）"""
    try:
        menu_data = menu_service.get_menu(config.DEVICE_ID)
        categories = menu_data.get('categories', [])
        # 统计可选/总数
        total = sum(len(c.get('items', [])) for c in categories)
        available = sum(1 for c in categories for it in c.get('items', []) if it.get('available'))
        return render_template('customer/menu.html', categories=categories, total_count=total, available_count=available, device_id=config.DEVICE_ID)
    except Exception as e:
        logger.error(f"菜单页面加载失败: {e}")
        return render_template('error.html', error_code=500, error_message='菜单加载失败'), 500

@customer_bp.route('/product/<item_id>')
def product_detail(item_id):
    """商品详情页面"""
    try:
        # 获取商品与配方信息
        item = menu_service.get_item(config.DEVICE_ID, item_id)
        if not item:
            return render_template('error.html',
                                 error_code=404,
                                 error_message='商品不存在'), 404
        recipe_id = item.get('recipe_id')
        availability = brewing_service.check_recipe_availability(recipe_id) if recipe_id else {'available': False, 'message': '无配方'}
        # 叠加菜单可售状态
        available = bool(item.get('available')) and bool(availability.get('available'))
        availability = {
            'available': available,
            'message': '' if available else (availability.get('message') or '不可售'),
            'missing_materials': availability.get('missing_materials', [])
        }
        
        # 规格选项：来自 item.options_schema，必要时回退默认
        options_schema = item.get('options_schema') or {}
        default_options = {
            'size': [
                {'id': 'regular', 'name': '标准', 'price_add': 0},
                {'id': 'large', 'name': '大杯', 'price_add': 200}
            ],
            'temperature': [
                {'id': 'hot', 'name': '热饮', 'price_add': 0},
                {'id': 'cold', 'name': '冷饮', 'price_add': 0}
            ],
            'sugar': [
                {'id': 'normal', 'name': '正常糖', 'price_add': 0},
                {'id': 'half', 'name': '半糖', 'price_add': 0},
                {'id': 'none', 'name': '无糖', 'price_add': 0}
            ]
        }
        options = default_options
        # 将 schema 中的数组类选项映射为标签
        for key, val in options_schema.items():
            if isinstance(val, list):
                options[key] = [{'id': str(v), 'name': str(v), 'price_add': 0} for v in val]
        
        return render_template('customer/product_detail.html',
                             item_id=item_id,
                             item=item,
                             availability=availability,
                             options=options)
        
    except Exception as e:
        logger.error(f"商品详情页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@customer_bp.route('/payment', methods=['GET', 'POST'])
def payment():
    """支付选择页面"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            # 兼容老参数 recipe_id；优先使用 item_id
            item_id = data.get('item_id')
            recipe_id = data.get('recipe_id')
            if not item_id and recipe_id:
                # 尝试通过配方反查一个可用商品（简化处理：直接使用配方）
                pass
            
            # 读取设备商品以获取最终价格与配方
            item = None
            if item_id:
                item = menu_service.get_item(config.DEVICE_ID, item_id)
                if item:
                    recipe_id = item.get('recipe_id')
            options = data.get('options', {})
            
            # 验证商品与配方
            if not item or not recipe_id:
                return jsonify({'success': False, 'message': '商品不存在'})
            
            # 检查可制作性
            availability = brewing_service.check_recipe_availability(recipe_id)
            if not availability['available']:
                return jsonify({'success': False, 
                              'message': availability['message'],
                              'missing_materials': availability.get('missing_materials', [])})
            
            # 计算价格
            base_price = int(item.get('price_cents', 0))
            options_price = 0
            
            # 这里可以根据选项计算额外价格
            if options.get('size') == 'large':
                options_price += 200  # 大杯加2元
            
            total_price = base_price + options_price

            # 生成订单ID并构建订单数据
            order_id = str(uuid.uuid4())
            order_data = {
                'order_id': order_id,
                'recipe_id': recipe_id,
                'recipe_name': item.get('name'),
                'amount_cents': total_price,
                'options': options,
                'status': 'paid'  # 默认完成支付
            }

            # 写入 Redis 订单记录
            try:
                redis_service.create_order(order_data.copy())
            except Exception as e:
                logger.warning(f"创建订单记录失败(可忽略): {e}")

            # 将订单保存到 session
            session['order_data'] = {
                'recipe_id': recipe_id,
                'recipe_name': item.get('name'),
                'options': options,
                'base_price_cents': base_price,
                'options_price_cents': options_price,
                'total_price_cents': total_price
            }
            session['current_order_id'] = order_id

            # 启动制作流程
            brew_res = brewing_service.start_brewing(order_id, recipe_id)
            if not brew_res.get('success'):
                return jsonify({'success': False, 'message': brew_res.get('message', '制作启动失败')}), 400

            # 返回跳转到制作页面
            return jsonify({
                'success': True,
                'order_id': order_id,
                'total_price_cents': total_price,
                'redirect_url': url_for('customer.brewing', order_id=order_id)
            })
        
        # GET请求显示支付页面
        order_data = session.get('order_data')
        if not order_data:
            return redirect(url_for('customer.menu'))
        
        # 获取可用支付方式
        payment_methods = payment_service.get_payment_methods()
        
        return render_template('customer/payment.html',
                             order_data=order_data,
                             payment_methods=payment_methods)
        
    except Exception as e:
        logger.error(f"支付页面处理失败: {e}")
        return jsonify({'success': False, 'message': '处理失败'})

# -------------------- 购物车逻辑 --------------------
def _get_cart():
    cart = session.get('cart')
    if not cart:
        cart = {'items': [], 'total_cents': 0, 'count': 0}
    return cart

def _save_cart(cart):
    session['cart'] = cart

def _price_with_options(base_price: int, options: dict) -> int:
    extra = 0
    # 与支付逻辑保持一致：大杯+200 分
    if options and options.get('size') == 'large':
        extra += 200
    return int(base_price) + extra

def _recalc_cart(cart):
    total = 0
    count = 0
    for it in cart['items']:
        line = int(it.get('price_cents', 0)) * int(it.get('qty', 1))
        total += line
        count += int(it.get('qty', 1))
    cart['total_cents'] = total
    cart['count'] = count
    return cart

@customer_bp.route('/cart', methods=['GET'])
def view_cart():
    cart = _recalc_cart(_get_cart())
    _save_cart(cart)
    return render_template('customer/cart.html', cart=cart)

@customer_bp.route('/cart/add', methods=['POST'])
def cart_add():
    try:
        data = request.get_json() or {}
        item_id = data.get('item_id')
        qty = int(data.get('qty', 1))
        options = data.get('options', {})
        if not item_id or qty <= 0:
            return jsonify({'ok': False, 'message': '参数错误'}), 400
        item = menu_service.get_item(config.DEVICE_ID, item_id)
        if not item:
            return jsonify({'ok': False, 'message': '商品不存在'}), 404
        # 可售与配方校验
        recipe_id = item.get('recipe_id')
        avail = brewing_service.check_recipe_availability(recipe_id) if recipe_id else {'available': False, 'message': '无配方'}
        if not (item.get('available') and avail.get('available')):
            return jsonify({'ok': False, 'message': avail.get('message', '不可售')}), 400
        # 定价
        base_price = int(item.get('price_cents', 0))
        final_price = _price_with_options(base_price, options)
        # 入车
        cart = _get_cart()
        cart_item = {
            'cart_item_id': str(uuid.uuid4()),
            'item_id': item_id,
            'recipe_id': recipe_id,
            'name': item.get('name'),
            'price_cents': final_price,
            'base_price_cents': base_price,
            'options': options,
            'qty': qty
        }
        cart['items'].append(cart_item)
        _recalc_cart(cart)
        _save_cart(cart)
        return jsonify({'ok': True, 'cart': {'count': cart['count'], 'total_cents': cart['total_cents']}})
    except Exception as e:
        logger.error(f"加入购物车失败: {e}")
        return jsonify({'ok': False, 'message': '加入失败'}), 500

@customer_bp.route('/cart/update', methods=['POST'])
def cart_update():
    try:
        data = request.get_json() or {}
        cart_item_id = data.get('cart_item_id')
        qty = int(data.get('qty', 1))
        if not cart_item_id or qty < 0:
            return jsonify({'ok': False, 'message': '参数错误'}), 400
        cart = _get_cart()
        new_items = []
        for it in cart['items']:
            if it.get('cart_item_id') == cart_item_id:
                if qty == 0:
                    continue
                it['qty'] = qty
            new_items.append(it)
        cart['items'] = new_items
        _recalc_cart(cart)
        _save_cart(cart)
        return jsonify({'ok': True, 'cart': cart})
    except Exception as e:
        logger.error(f"更新购物车失败: {e}")
        return jsonify({'ok': False, 'message': '更新失败'}), 500

@customer_bp.route('/cart/remove', methods=['POST'])
def cart_remove():
    try:
        data = request.get_json() or {}
        cart_item_id = data.get('cart_item_id')
        if not cart_item_id:
            return jsonify({'ok': False, 'message': '参数错误'}), 400
        cart = _get_cart()
        cart['items'] = [it for it in cart['items'] if it.get('cart_item_id') != cart_item_id]
        _recalc_cart(cart)
        _save_cart(cart)
        return jsonify({'ok': True, 'cart': cart})
    except Exception as e:
        logger.error(f"移除购物车项失败: {e}")
        return jsonify({'ok': False, 'message': '移除失败'}), 500

@customer_bp.route('/cart/clear', methods=['POST'])
def cart_clear():
    _save_cart({'items': [], 'total_cents': 0, 'count': 0})
    return jsonify({'ok': True})

@customer_bp.route('/checkout', methods=['POST'])
def checkout():
    """从购物车结算：创建订单并开始第一杯制作（其余项目前作为订单记录）。"""
    try:
        cart = _recalc_cart(_get_cart())
        if not cart['items']:
            return jsonify({'ok': False, 'message': '购物车为空'}), 400
        # 取第一项作为本次制作目标
        first = cart['items'][0]
        recipe_id = first.get('recipe_id')
        if not recipe_id:
            return jsonify({'ok': False, 'message': '缺少配方'}), 400
        avail = brewing_service.check_recipe_availability(recipe_id)
        if not avail.get('available'):
            return jsonify({'ok': False, 'message': avail.get('message', '不可制作')}), 400
        order_id = str(uuid.uuid4())
        order_data = {
            'order_id': order_id,
            'recipe_id': recipe_id,
            'recipe_name': first.get('name'),
            'amount_cents': cart['total_cents'],
            'items': cart['items'],  # 将整车记录入订单
            'status': 'paid'
        }
        try:
            redis_service.create_order(order_data.copy())
        except Exception as e:
            logger.warning(f"创建订单记录失败(可忽略): {e}")
        # 覆盖 session order_data 以复用既有模板
        session['order_data'] = {
            'recipe_id': recipe_id,
            'recipe_name': first.get('name'),
            'options': first.get('options', {}),
            'base_price_cents': int(first.get('base_price_cents', 0)),
            'options_price_cents': int(first.get('price_cents', 0)) - int(first.get('base_price_cents', 0)),
            'total_price_cents': cart['total_cents']
        }
        session['current_order_id'] = order_id
        # 清空购物车
        _save_cart({'items': [], 'total_cents': 0, 'count': 0})
        # 开始制作第一杯
        brew_res = brewing_service.start_brewing(order_id, recipe_id)
        if not brew_res.get('success'):
            return jsonify({'ok': False, 'message': brew_res.get('message', '制作启动失败')}), 400
        return jsonify({'ok': True, 'order_id': order_id, 'redirect_url': url_for('customer.brewing', order_id=order_id)})
    except Exception as e:
        logger.error(f"结算失败: {e}")
        return jsonify({'ok': False, 'message': '结算失败'}), 500

@customer_bp.route('/qr/<payment_method>')
def qr_payment(payment_method):
    """二维码支付页面"""
    try:
        order_data = session.get('order_data')
        if not order_data:
            return redirect(url_for('customer.menu'))
        
        # 检查支付方式是否可用
        payment_methods = payment_service.get_payment_methods()
        if payment_method not in payment_methods or not payment_methods[payment_method]['available']:
            return render_template('error.html',
                                 error_code=400,
                                 error_message='支付方式不可用'), 400
        
        # 生成订单ID
        order_id = str(uuid.uuid4())
        
        # 创建支付会话
        payment_data = {
            'order_id': order_id,
            'amount_cents': order_data['total_price_cents'],
            'payment_method': payment_method
        }
        
        payment_session = payment_service.create_payment(payment_data)
        
        # 保存订单ID到session
        session['current_order_id'] = order_id
        
        return render_template('customer/qr_payment.html',
                             payment_session=payment_session,
                             order_data=order_data,
                             payment_method_info=payment_methods[payment_method])
        
    except Exception as e:
        logger.error(f"二维码支付页面失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='支付页面加载失败'), 500

@customer_bp.route('/brewing/<order_id>')
def brewing(order_id):
    """制作进度页面"""
    try:
        # 检查订单是否存在
        order_data = session.get('order_data')
        current_order_id = session.get('current_order_id')
        
        if not order_data or current_order_id != order_id:
            return redirect(url_for('customer.idle'))
        
        # 获取制作状态
        brewing_status = brewing_service.get_brewing_status()
        
        return render_template('customer/brewing.html',
                             order_id=order_id,
                             order_data=order_data,
                             brewing_status=brewing_status)
        
    except Exception as e:
        logger.error(f"制作页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@customer_bp.route('/done/<order_id>')
def done(order_id):
    """完成页面"""
    try:
        order_data = session.get('order_data')
        current_order_id = session.get('current_order_id')
        
        if not order_data or current_order_id != order_id:
            return redirect(url_for('customer.idle'))
        
        # 清理session中的订单数据
        session.pop('order_data', None)
        session.pop('current_order_id', None)
        
        return render_template('customer/done.html',
                             order_id=order_id,
                             order_data=order_data)
        
    except Exception as e:
        logger.error(f"完成页面加载失败: {e}")
        return render_template('error.html',
                             error_code=500,
                             error_message='页面加载失败'), 500

@customer_bp.route('/out_of_service')
def out_of_service():
    """停服页面"""
    reason = request.args.get('reason', 'maintenance')
    return render_template('customer/out_of_service.html', reason=reason)
