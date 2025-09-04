/* 智能咖啡机主JavaScript文件 */

// 全局配置
window.CoffeeMachine = {
    config: {
        apiBase: '/api',
        sseEndpoint: '/events',
        heartbeatInterval: 30000,
        statusCheckInterval: 10000,
        paymentTimeout: 300000, // 5分钟
        screenSaverTimeout: 30000 // 30秒
    },
    
    state: {
        isOnline: true,
        isBrewingActive: false,
        currentOrder: null,
        eventSource: null,
        statusCheckTimer: null,
        heartbeatTimer: null
    },
    
    // 初始化
    init: function() {
        console.log('咖啡机系统初始化...');
        this.initEventSource();
        this.initStatusCheck();
        this.initTouchOptimizations();
        this.initAccessibility();
    },
    
    // 初始化SSE事件源
    initEventSource: function() {
        if (this.state.eventSource) {
            this.state.eventSource.close();
        }
        
        try {
            this.state.eventSource = new EventSource(this.config.sseEndpoint);
            
            this.state.eventSource.onopen = function() {
                console.log('SSE连接已建立');
            };
            
            this.state.eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                CoffeeMachine.handleSSEEvent(data);
            };
            
            this.state.eventSource.onerror = function(event) {
                console.error('SSE连接错误:', event);
                setTimeout(() => {
                    CoffeeMachine.initEventSource();
                }, 5000);
            };
            
        } catch (error) {
            console.error('SSE初始化失败:', error);
        }
    },
    
    // 处理SSE事件
    handleSSEEvent: function(data) {
        console.log('收到SSE事件:', data);
        
        switch (data.type) {
            case 'pay_update':
                this.handlePaymentUpdate(data);
                break;
            case 'brew_progress':
                this.handleBrewProgress(data);
                break;
            case 'brew_done':
                this.handleBrewDone(data);
                break;
            case 'material_update':
                this.handleMaterialUpdate(data);
                break;
            case 'command_claimed':
            case 'command_done':
                this.handleCommandUpdate(data);
                break;
            case 'net_status':
                this.handleNetworkStatus(data);
                break;
            case 'heartbeat':
                // 心跳事件，更新在线状态
                this.state.isOnline = true;
                break;
        }
        
        // 触发自定义事件
        const customEvent = new CustomEvent('coffeeEvent', { detail: data });
        document.dispatchEvent(customEvent);
    },
    
    // 处理支付状态更新
    handlePaymentUpdate: function(data) {
        const { order_id, status, txn_id } = data;
        
        if (status === 'paid') {
            // 支付成功
            this.showToast('支付成功！正在准备制作...', 'success');
            
            // 如果在支付页面，跳转到制作页面
            if (window.location.pathname.includes('qr') || window.location.pathname.includes('payment')) {
                setTimeout(() => {
                    window.location.href = `/brewing/${order_id}`;
                }, 1000);
            }
        } else if (status === 'failed' || status === 'timeout' || status === 'cancelled') {
            // 支付失败
            this.showToast('支付失败，请重新选择', 'error');
            
            setTimeout(() => {
                window.location.href = '/menu';
            }, 2000);
        }
    },
    
    // 处理制作进度更新
    handleBrewProgress: function(data) {
        const { order_id, step, pct, eta_s } = data;
        
        // 更新进度条
        const progressBar = document.getElementById('brewProgress');
        if (progressBar) {
            progressBar.style.width = `${pct}%`;
            progressBar.textContent = `${pct}%`;
        }
        
        // 更新步骤文本
        const stepText = document.getElementById('brewStep');
        if (stepText) {
            stepText.textContent = step;
        }
        
        // 更新预计时间
        const etaText = document.getElementById('brewEta');
        if (etaText && eta_s > 0) {
            const minutes = Math.floor(eta_s / 60);
            const seconds = eta_s % 60;
            etaText.textContent = `预计还需 ${minutes > 0 ? minutes + '分' : ''}${seconds}秒`;
        }
    },
    
    // 处理制作完成
    handleBrewDone: function(data) {
        const { order_id, ok, error } = data;
        
        if (ok) {
            // 制作成功
            this.showToast('您的咖啡制作完成！', 'success');
            setTimeout(() => {
                window.location.href = `/done/${order_id}`;
            }, 1000);
        } else {
            // 制作失败
            this.showToast(`制作失败：${error || '未知错误'}`, 'error');
            setTimeout(() => {
                window.location.href = '/menu';
            }, 3000);
        }
    },
    
    // 处理物料更新
    handleMaterialUpdate: function(data) {
        const { bin_index, material_code, remaining, pct, low } = data;
        
        // 更新物料显示
        const materialElement = document.querySelector(`[data-bin-index="${bin_index}"]`);
        if (materialElement) {
            const percentElement = materialElement.querySelector('.material-percent');
            const statusElement = materialElement.querySelector('.material-status');
            
            if (percentElement) {
                percentElement.textContent = `${pct.toFixed(1)}%`;
            }
            
            if (statusElement) {
                statusElement.className = `material-status ${low ? 'text-danger' : 'text-success'}`;
                statusElement.innerHTML = `<i class="fas ${low ? 'fa-exclamation-triangle' : 'fa-check-circle'}"></i>`;
            }
        }
        
        // 如果物料不足，可能需要刷新菜单
        if (low) {
            this.showToast(`${material_code} 物料不足`, 'warning');
        }
    },
    
    // 处理命令更新
    handleCommandUpdate: function(data) {
        const { command_id, type, status } = data;
        
        if (data.type === 'command_claimed') {
            this.showToast(`正在执行远程${type}命令...`, 'info');
        } else if (data.type === 'command_done') {
            const message = status === 'success' ? 
                `远程${type}命令执行成功` : 
                `远程${type}命令执行失败`;
            this.showToast(message, status === 'success' ? 'success' : 'error');
        }
    },
    
    // 处理网络状态
    handleNetworkStatus: function(data) {
        this.state.isOnline = data.online;
        
        if (!data.online) {
            this.showToast('网络连接中断', 'error');
            setTimeout(() => {
                window.location.href = '/customer/out_of_service?reason=network';
            }, 2000);
        } else {
            this.showToast('网络连接已恢复', 'success');
        }
    },
    
    // 初始化状态检查
    initStatusCheck: function() {
        this.state.statusCheckTimer = setInterval(() => {
            this.checkDeviceStatus();
        }, this.config.statusCheckInterval);
    },
    
    // 检查设备状态
    checkDeviceStatus: function() {
        return fetch(`${this.config.apiBase}/device/status`)
            .then(response => response.json())
            .then(data => {
                const device = data.device;
                
                if (!device || device.status !== 'online') {
                    this.state.isOnline = false;
                    window.location.href = '/customer/out_of_service?reason=offline';
                } else {
                    this.state.isOnline = true;
                }
                
                return data;
            })
            .catch(error => {
                console.error('状态检查失败:', error);
                this.state.isOnline = false;
            });
    },
    
    // 初始化触控优化
    initTouchOptimizations: function() {
        // 禁用双击缩放
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(event) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        // 添加触控反馈
        document.addEventListener('touchstart', function(event) {
            if (event.target.closest('.touch-feedback')) {
                event.target.closest('.touch-feedback').style.transform = 'scale(0.95)';
            }
        });
        
        document.addEventListener('touchend', function(event) {
            if (event.target.closest('.touch-feedback')) {
                setTimeout(() => {
                    event.target.closest('.touch-feedback').style.transform = 'scale(1)';
                }, 150);
            }
        });
    },
    
    // 初始化无障碍功能
    initAccessibility: function() {
        // 焦点管理
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.addEventListener('mousedown', function() {
            document.body.classList.remove('keyboard-navigation');
        });
        
        // ARIA实时更新
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'announcer';
        document.body.appendChild(announcer);
    },
    
    // 显示提示消息
    showToast: function(message, type = 'info', duration = 3000) {
        // 移除现有提示
        const existingToast = document.getElementById('toast-container');
        if (existingToast) {
            existingToast.remove();
        }
        
        // 创建提示容器
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed top-0 start-50 translate-middle-x p-3';
        toastContainer.style.zIndex = '9999';
        
        // 确定样式
        let bgClass = 'bg-info';
        let icon = 'fa-info-circle';
        
        switch (type) {
            case 'success':
                bgClass = 'bg-success';
                icon = 'fa-check-circle';
                break;
            case 'error':
                bgClass = 'bg-danger';
                icon = 'fa-times-circle';
                break;
            case 'warning':
                bgClass = 'bg-warning text-dark';
                icon = 'fa-exclamation-triangle';
                break;
        }
        
        // 创建提示内容
        toastContainer.innerHTML = `
            <div class="toast show ${bgClass} text-white" role="alert">
                <div class="toast-body d-flex align-items-center">
                    <i class="fas ${icon} me-2"></i>
                    <span>${message}</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(toastContainer);
        
        // 更新ARIA通知
        const announcer = document.getElementById('announcer');
        if (announcer) {
            announcer.textContent = message;
        }
        
        // 自动隐藏
        setTimeout(() => {
            toastContainer.remove();
        }, duration);
    },
    
    // API请求封装
    api: {
        get: function(endpoint) {
            return fetch(`${CoffeeMachine.config.apiBase}${endpoint}`)
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                });
        },
        
        post: function(endpoint, data) {
            return fetch(`${CoffeeMachine.config.apiBase}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            });
        }
    },
    
    // 工具函数
    utils: {
        // 格式化价格
        formatPrice: function(cents) {
            return (cents / 100).toFixed(2);
        },
        
        // 格式化时间
        formatTime: function(timestamp) {
            return new Date(timestamp * 1000).toLocaleString('zh-CN');
        },
        
        // 防抖函数
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // 节流函数
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        }
    },
    
    // 清理资源
    cleanup: function() {
        if (this.state.eventSource) {
            this.state.eventSource.close();
        }
        if (this.state.statusCheckTimer) {
            clearInterval(this.state.statusCheckTimer);
        }
        if (this.state.heartbeatTimer) {
            clearInterval(this.state.heartbeatTimer);
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    CoffeeMachine.init();
});

// 页面卸载前清理资源
window.addEventListener('beforeunload', function() {
    CoffeeMachine.cleanup();
});

// 导出全局对象
window.CM = CoffeeMachine;
