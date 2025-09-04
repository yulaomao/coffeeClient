import json
import logging
from typing import Any, Dict, List, Optional
from config import config
from services.redis_service import redis_service

logger = logging.getLogger(__name__)


def _device_prefix(device_id: str) -> str:
    return f"cm:dev:{device_id}:menu"


def _safe_json_loads(s: Optional[str], default):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def _pick_i18n_name(i18n_json: Optional[str], fallback: str) -> str:
    data = _safe_json_loads(i18n_json, {})
    lang = getattr(config, 'DEFAULT_LANGUAGE', 'zh-CN')
    # 兼容 zh-CN/zh
    val = None
    if lang in data:
        val = data.get(lang)
    if not val and 'zh' in data:
        val = data.get('zh')
    if not val and 'en' in data:
        val = data.get('en')
    return val or fallback


def _int_or_default(v: Any, d: int = 0) -> int:
    try:
        if v is None or v == '':
            return d
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d


class MenuService:
    def __init__(self):
        pass

    def get_menu_meta(self, device_id: str) -> Dict[str, Any]:
        key = f"{_device_prefix(device_id)}:meta"
        return redis_service.redis_client.hgetall(key) or {}

    def get_available_set(self, device_id: str) -> set:
        key = f"{_device_prefix(device_id)}:available"
        try:
            return set(redis_service.redis_client.smembers(key))
        except Exception:
            return set()

    def get_categories(self, device_id: str) -> List[Dict[str, Any]]:
        zkey = f"{_device_prefix(device_id)}:cats"
        r = redis_service.redis_client
        cat_ids = r.zrange(zkey, 0, -1)  # 已按 score 排序
        cats: List[Dict[str, Any]] = []
        for cid in cat_ids:
            hkey = f"{_device_prefix(device_id)}:cat:{cid}"
            h = r.hgetall(hkey)
            if not h:
                continue
            # 仅展示 visible=="1"
            if h.get('visible') != '1':
                continue
            cats.append({
                'id': h.get('id', cid),
                'raw': h,
                'name': _pick_i18n_name(h.get('name_i18n_json'), h.get('id', cid)),
                'sort_order': _int_or_default(h.get('sort_order'), 0),
            })
        return cats

    def get_items_by_category(self, device_id: str, cat_id: str) -> List[Dict[str, Any]]:
        zkey = f"{_device_prefix(device_id)}:cat:{cat_id}:items"
        r = redis_service.redis_client
        item_ids = r.zrange(zkey, 0, -1)
        avail = self.get_available_set(device_id)
        items: List[Dict[str, Any]] = []
        for iid in item_ids:
            hkey = f"{_device_prefix(device_id)}:item:{iid}"
            it = r.hgetall(hkey)
            if not it:
                continue
            # 展示层只显示 visibility==visible
            if it.get('visibility') != 'visible':
                continue
            recipe_id = it.get('recipe_id')
            recipe = redis_service.get_recipe(recipe_id) if recipe_id else None
            # 价格：优先 item.price_cents_override，否则 recipe.default_price_cents/price_cents
            override_cents = it.get('price_cents_override')
            if override_cents in (None, ''):
                effective_cents = _int_or_default(
                    recipe.get('default_price_cents') if recipe else None,
                    _int_or_default(recipe.get('price_cents') if recipe else None, 0)
                )
            else:
                effective_cents = _int_or_default(override_cents, 0)

            items.append({
                'id': it.get('id', iid),
                'cat_id': it.get('cat_id', cat_id),
                'recipe_id': recipe_id,
                'name': _pick_i18n_name(it.get('name_i18n_json'), it.get('id', iid)),
                'image_url': it.get('image_url'),
                'price_cents': effective_cents,
                'visibility': it.get('visibility'),
                'options_schema': _safe_json_loads(it.get('options_schema_json'), {}),
                'badges': [s for s in (it.get('badges_csv') or '').split(',') if s],
                'schedule': _safe_json_loads(it.get('schedule_json'), {}),
                'tags': [s for s in (it.get('tags_csv') or '').split(',') if s],
                'sort_order': _int_or_default(it.get('sort_order'), 0),
                'available': it.get('id', iid) in avail,
                'raw': it,
            })
        return items

    def get_menu(self, device_id: str) -> Dict[str, Any]:
        meta = self.get_menu_meta(device_id)
        cats = self.get_categories(device_id)
        result_cats: List[Dict[str, Any]] = []
        for c in cats:
            items = self.get_items_by_category(device_id, c['id'])
            if not items:
                continue
            result_cats.append({
                'id': c['id'],
                'name': c['name'],
                'sort_order': c['sort_order'],
                'items': items
            })
        return { 'meta': meta, 'categories': result_cats }

    def get_item(self, device_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        r = redis_service.redis_client
        hkey = f"{_device_prefix(device_id)}:item:{item_id}"
        it = r.hgetall(hkey)
        if not it:
            return None
        recipe_id = it.get('recipe_id')
        recipe = redis_service.get_recipe(recipe_id) if recipe_id else None
        override_cents = it.get('price_cents_override')
        if override_cents in (None, ''):
            effective_cents = _int_or_default(
                recipe.get('default_price_cents') if recipe else None,
                _int_or_default(recipe.get('price_cents') if recipe else None, 0)
            )
        else:
            effective_cents = _int_or_default(override_cents, 0)
        avail = self.get_available_set(device_id)
        return {
            'id': it.get('id', item_id),
            'cat_id': it.get('cat_id'),
            'recipe_id': recipe_id,
            'name': _pick_i18n_name(it.get('name_i18n_json'), it.get('id', item_id)),
            'image_url': it.get('image_url'),
            'price_cents': effective_cents,
            'visibility': it.get('visibility'),
            'options_schema': _safe_json_loads(it.get('options_schema_json'), {}),
            'badges': [s for s in (it.get('badges_csv') or '').split(',') if s],
            'schedule': _safe_json_loads(it.get('schedule_json'), {}),
            'tags': [s for s in (it.get('tags_csv') or '').split(',') if s],
            'available': it.get('id', item_id) in avail,
            'raw': it,
        }


menu_service = MenuService()
