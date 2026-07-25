// 會話管理工具 - 處理瀏覽器關閉時的自動登出
import API_CONFIG from '../config/api';

class SessionManager {
  constructor() {
    this.isInitialized = false;
    this.heartbeatInterval = null;
    this.visibilityChangeHandler = null;
    this.beforeUnloadHandler = null;
    this.storageHandler = null;
    
    // 會話配置
    this.config = {
      heartbeatInterval: 30000, // 30秒心跳檢測
      tokenCheckInterval: 60000, // 1分鐘檢查一次token
      sessionKey: 'allcare365_session',
      lastActivityKey: 'allcare365_last_activity'
    };
  }

  // 初始化會話管理
  init() {
    if (this.isInitialized) return;
    
    console.log('SessionManager: 初始化會話管理');
    
    // 設置會話ID
    this.setSessionId();
    
    // 監聽瀏覽器關閉/刷新事件
    this.setupBeforeUnloadHandler();
    
    // 監聽頁面可見性變化
    this.setupVisibilityChangeHandler();
    
    // 監聽localStorage變化（多標籤頁同步）
    this.setupStorageHandler();
    
    // 啟動心跳檢測
    this.startHeartbeat();
    
    // 啟動TOKEN定期檢查
    this.startTokenCheck();
    
    this.isInitialized = true;
  }

  // 設置會話ID
  setSessionId() {
    const sessionId = this.generateSessionId();
    sessionStorage.setItem(this.config.sessionKey, sessionId);
    this.updateLastActivity();
  }

  // 生成會話ID
  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // 更新最後活動時間
  updateLastActivity() {
    const now = Date.now();
    localStorage.setItem(this.config.lastActivityKey, now.toString());
  }

  // 設置瀏覽器關閉處理器
  setupBeforeUnloadHandler() {
    this.beforeUnloadHandler = (event) => {
      console.log('SessionManager: 檢測到瀏覽器即將關閉');
      
      // 檢查是否是最後一個標籤頁
      if (this.isLastTab()) {
        console.log('SessionManager: 這是最後一個標籤頁，執行登出');
        this.performLogout();
      }
      
      // 清理當前標籤頁的會話
      this.cleanupCurrentTab();
    };
    
    window.addEventListener('beforeunload', this.beforeUnloadHandler);
  }

  // 設置頁面可見性變化處理器
  setupVisibilityChangeHandler() {
    this.visibilityChangeHandler = () => {
      if (document.hidden) {
        console.log('SessionManager: 頁面變為不可見');
        this.updateLastActivity();
      } else {
        console.log('SessionManager: 頁面變為可見');
        this.checkAuthStatus();
      }
    };
    
    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
  }

  // 設置localStorage變化處理器（多標籤頁同步）
  setupStorageHandler() {
    this.storageHandler = (event) => {
      // 如果認證狀態被清除，同步登出所有標籤頁
      if (event.key === 'access_token' && !event.newValue) {
        console.log('SessionManager: 檢測到認證狀態被清除，同步登出');
        window.location.href = '/login';
      }
    };
    
    window.addEventListener('storage', this.storageHandler);
  }

  // 檢查是否是最後一個標籤頁
  isLastTab() {
    // 使用localStorage來跟蹤活動標籤頁
    const tabId = sessionStorage.getItem(this.config.sessionKey);
    const activeTabs = JSON.parse(localStorage.getItem('active_tabs') || '[]');
    
    // 移除當前標籤頁
    const remainingTabs = activeTabs.filter(id => id !== tabId);
    localStorage.setItem('active_tabs', JSON.stringify(remainingTabs));
    
    return remainingTabs.length === 0;
  }

  // 註冊當前標籤頁為活動狀態
  registerActiveTab() {
    const tabId = sessionStorage.getItem(this.config.sessionKey);
    const activeTabs = JSON.parse(localStorage.getItem('active_tabs') || '[]');
    
    if (!activeTabs.includes(tabId)) {
      activeTabs.push(tabId);
      localStorage.setItem('active_tabs', JSON.stringify(activeTabs));
    }
  }

  // 清理當前標籤頁
  cleanupCurrentTab() {
    const tabId = sessionStorage.getItem(this.config.sessionKey);
    const activeTabs = JSON.parse(localStorage.getItem('active_tabs') || '[]');
    
    const remainingTabs = activeTabs.filter(id => id !== tabId);
    localStorage.setItem('active_tabs', JSON.stringify(remainingTabs));
    
    // 清理sessionStorage
    sessionStorage.clear();
  }

  // 執行登出操作
  performLogout() {
    console.log('SessionManager: 執行自動登出');
    
    // 清除所有認證相關的存儲
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('active_tabs');
    localStorage.removeItem(this.config.lastActivityKey);
    
    // 觸發登出事件
    window.dispatchEvent(new CustomEvent('session-logout', {
      detail: { reason: 'browser_close' }
    }));
  }

  // 啟動心跳檢測
  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.isAuthenticated()) {
        this.updateLastActivity();
        this.registerActiveTab();
      }
    }, this.config.heartbeatInterval);
  }

  // 啟動TOKEN檢查
  startTokenCheck() {
    setInterval(() => {
      this.checkTokenExpiry();
    }, this.config.tokenCheckInterval);
  }

  // 檢查TOKEN是否即將過期
  checkTokenExpiry() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      const timeUntilExpiry = payload.exp - currentTime;

      // 如果TOKEN在5分鐘內過期，嘗試刷新
      if (timeUntilExpiry < 300 && timeUntilExpiry > 0) {
        console.log('SessionManager: TOKEN即將過期，嘗試刷新');
        this.refreshToken();
      } else if (timeUntilExpiry <= 0) {
        console.log('SessionManager: TOKEN已過期');
        this.handleTokenExpired();
      }
    } catch (error) {
      console.error('SessionManager: TOKEN解析錯誤', error);
      this.handleTokenExpired();
    }
  }

  // 刷新TOKEN
  async refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      console.log('SessionManager: 沒有 refresh token，無法刷新');
      this.handleTokenExpired();
      return;
    }

    try {
      console.log('SessionManager: 嘗試刷新 token...');
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKEN_REFRESH}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      console.log('SessionManager: Token 刷新回應:', response.status, response.statusText);

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        console.log('SessionManager: TOKEN刷新成功');
        
        // 觸發TOKEN刷新事件
        window.dispatchEvent(new CustomEvent('token-refreshed', {
          detail: { newToken: data.access }
        }));
      } else {
        const errorData = await response.text();
        console.error('SessionManager: TOKEN刷新失敗:', response.status, errorData);
        
        // 如果是 token 無效，清除所有認證資料
        if (response.status === 401 || errorData.includes('token not valid')) {
          console.log('SessionManager: Token 已失效，清除認證資料');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user_info');
        }
        this.handleTokenExpired();
      }
    } catch (error) {
      console.error('SessionManager: TOKEN刷新錯誤', error);
      this.handleTokenExpired();
    }
  }

  // 處理TOKEN過期
  handleTokenExpired() {
    console.log('SessionManager: 處理TOKEN過期');
    
    // 顯示友好的提示信息
    this.showTokenExpiredNotification();
    
    // 延遲執行登出，給用戶時間看到提示
    setTimeout(() => {
      this.performLogout();
      window.location.href = '/login';
    }, 3000);
  }

  // 顯示TOKEN過期通知
  showTokenExpiredNotification() {
    // 創建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #ff6b6b;
      color: white;
      padding: 15px 20px;
      border-radius: 5px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      max-width: 300px;
    `;
    notification.innerHTML = `
      <strong>會話已過期</strong><br>
      為了您的安全，系統將在3秒後自動登出
    `;
    
    document.body.appendChild(notification);
    
    // 3秒後移除通知
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
  }

  // 檢查認證狀態
  isAuthenticated() {
    const token = localStorage.getItem('access_token');
    const userInfo = localStorage.getItem('user_info');
    return !!(token && userInfo);
  }

  // 檢查認證狀態（包含TOKEN有效性）
  checkAuthStatus() {
    if (!this.isAuthenticated()) {
      return false;
    }

    const token = localStorage.getItem('access_token');
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp > currentTime;
    } catch (error) {
      console.error('SessionManager: TOKEN驗證錯誤', error);
      return false;
    }
  }

  // 清理資源
  cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    
    if (this.beforeUnloadHandler) {
      window.removeEventListener('beforeunload', this.beforeUnloadHandler);
    }
    
    if (this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    }
    
    if (this.storageHandler) {
      window.removeEventListener('storage', this.storageHandler);
    }
    
    this.isInitialized = false;
  }
}

// 創建全局實例
const sessionManager = new SessionManager();

export default sessionManager;
