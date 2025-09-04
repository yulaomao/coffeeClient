import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'coffee-machine-secret-key-2023')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Redis配置
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
    
    # 设备配置
    DEVICE_ID = os.environ.get('DEVICE_ID', 'dev-001')
    MERCHANT_ID = os.environ.get('MERCHANT_ID', 'merchant-001')
    DEVICE_ALIAS = os.environ.get('DEVICE_ALIAS', '咖啡机-大厅')
    DEVICE_MODEL = os.environ.get('DEVICE_MODEL', 'CM-2000')
    FIRMWARE_VERSION = os.environ.get('FIRMWARE_VERSION', '1.0.0')
    
    # 支付配置
    PAYMENT_TIMEOUT = int(os.environ.get('PAYMENT_TIMEOUT', 300))
    ENABLE_WECHAT_PAY = os.environ.get('ENABLE_WECHAT_PAY', 'True').lower() == 'true'
    ENABLE_ALIPAY = os.environ.get('ENABLE_ALIPAY', 'True').lower() == 'true'
    WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', '')
    WECHAT_MCH_ID = os.environ.get('WECHAT_MCH_ID', '')
    ALIPAY_APP_ID = os.environ.get('ALIPAY_APP_ID', '')
    
    # UI配置
    SCREENSAVER_TIMEOUT = int(os.environ.get('SCREENSAVER_TIMEOUT', 30))
    DONE_PAGE_DURATION = int(os.environ.get('DONE_PAGE_DURATION', 10))
    ENABLE_QUEUE = os.environ.get('ENABLE_QUEUE', 'False').lower() == 'true'
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'zh-CN')
    DEFAULT_PIN = os.environ.get('DEFAULT_PIN', '0000')
    
    # 物料配置
    LOW_MATERIAL_THRESHOLD = int(os.environ.get('LOW_MATERIAL_THRESHOLD', 20))
    AUTO_REPORT_MATERIALS = os.environ.get('AUTO_REPORT_MATERIALS', 'True').lower() == 'true'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'device.log')

config = Config()
