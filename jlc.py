import os
import sys
import time
import random
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json  # 补充缺少的 import

def log(msg):
    full_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(full_msg, flush=True)

def with_retry(func, max_retries=5, delay=1):
    """如果函数返回None或抛出异常，静默重试"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    return result
                time.sleep(delay + random.uniform(0, 1))  # 随机延迟
            except Exception:
                time.sleep(delay + random.uniform(0, 1))  # 随机延迟
        return None
    return wrapper

@with_retry
def extract_token_from_local_storage(driver):
    """从 localStorage 提取 X-JLC-AccessToken"""
    try:
        token = driver.execute_script("return window.localStorage.getItem('X-JLC-AccessToken');")
        if token:
            log(f"成功从 localStorage 提取 token: {token[:30]}...")
            return token
        else:
            alternative_keys = [
                "x-jlc-accesstoken",
                "accessToken", 
                "token",
                "jlc-token"
            ]
            for key in alternative_keys:
                token = driver.execute_script(f"return window.localStorage.getItem('{key}');")
                if token:
                    log(f"从 localStorage 的 {key} 提取到 token: {token[:30]}...")
                    return token
    except Exception as e:
        log(f"从 localStorage 提取 token 失败: {e}")
    
    return None

@with_retry
def extract_secretkey_from_devtools(driver):
    """使用 DevTools 从网络请求中提取 secretkey"""
    secretkey = None
    
    try:
        logs = driver.get_log('performance')
        
        for entry in logs:
            try:
                message = json.loads(entry['message'])
                message_type = message.get('message', {}).get('method', '')
                
                if message_type == 'Network.requestWillBeSent':
                    request = message.get('message', {}).get('params', {}).get('request', {})
                    url = request.get('url', '')
                    
                    if 'm.jlc.com' in url:
                        headers = request.get('headers', {})
                        secretkey = (
                            headers.get('secretkey') or 
                            headers.get('SecretKey') or
                            headers.get('secretKey') or
                            headers.get('SECRETKEY')
                        )
                        
                        if secretkey:
                            log(f"从请求中提取到 secretkey: {secretkey[:20]}...")
                            return secretkey
                
                elif message_type == 'Network.responseReceived':
                    response = message.get('message', {}).get('params', {}).get('response', {})
                    url = response.get('url', '')
                    
                    if 'm.jlc.com' in url:
                        headers = response.get('requestHeaders', {})
                        secretkey = (
                            headers.get('secretkey') or 
                            headers.get('SecretKey') or
                            headers.get('secretKey') or
                            headers.get('SECRETKEY')
                        )
                        
                        if secretkey:
                            log(f"从响应中提取到 secretkey: {secretkey[:20]}...")
                            return secretkey
                            
            except:
                continue
                
    except Exception as e:
        log(f"DevTools 提取 secretkey 出错: {e}")
    
    return secretkey

def ensure_login_page(driver):
    """确保进入登录页面，如果未检测到登录页面则重启浏览器"""
    max_restarts = 5
    restarts = 0
    
    while restarts < max_restarts:
        try:
            driver.get("https://passport.jlc.com/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F&bizExtendedParam=%7B%22jlcGroup_source%22%3A%22jlc%22%7D")
            log("已打开 JLC 登录页")
            
            WebDriverWait(driver, 10).until(lambda d: "passport.jlc.com/login" in d.current_url)
            current_url = driver.current_url

            if "passport.jlc.com/login" in current_url:
                log("检测到登录页面")
                return True
            else:
                restarts += 1
                if restarts < max_restarts:
                    driver.quit()
                    
                    chrome_options = Options()
                    chrome_options.add_argument("--headless=new")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--window-size=1920,1080")
                    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)

                    caps = DesiredCapabilities.CHROME
                    caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
                    
                    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    time.sleep(2)
                else:
                    log(f"重启浏览器{max_restarts}次后仍无法进入登录页面")
                    return False
                    
        except Exception as e:
            restarts += 1
            if restarts < max_restarts:
                try:
                    driver.quit()
                except:
                    pass
                
                chrome_options = Options()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                caps = DesiredCapabilities.CHROME
                caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
                
                driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                time.sleep(2)
            else:
                log(f"重启浏览器{max_restarts}次后仍出现异常: {e}")
                return False
    
    return False

def check_password_error(driver):
    """检查页面是否显示密码错误提示"""
    try:
        error_selectors = [
            "//*[contains(text(), '账号或密码不正确')]",
            "//*[contains(text(), '用户名或密码错误')]",
            "//*[contains(text(), '密码错误')]",
            "//*[contains(text(), '登录失败')]",
            "//*[contains(@class, 'error')]",
            "//*[contains(@class, 'err-msg')]",
            "//*[contains(@class, 'toast')]",
            "//*[contains(@class, 'message')]"
        ]
        
        for selector in error_selectors:
            try:
                error_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if error_element.is_displayed():
                    error_text = error_element.text.strip()
                    if any(keyword in error_text for keyword in ['账号或密码不正确', '用户名或密码错误', '密码错误', '登录失败']):
                        log("检测到账号或密码错误")
                        return True
            except:
                continue
                
        return False
    except Exception as e:
        log(f"检查密码错误时出现异常: {e}")
        return False

def perform_login(driver, username, password):
    wait = WebDriverWait(driver, 25)
    
    if not ensure_login_page(driver):
        return False

    log("检测到登录页面，正在执行登录流程...")

    try:
        phone_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"账号登录")]'))
        )
        phone_btn.click()
        log("已切换账号登录")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="请输入手机号码 / 客户编号 / 邮箱"]')))
    except Exception as e:
        log(f"账号登录按钮可能已默认选中: {e}")

    try:
        user_input = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@placeholder="请输入手机号码 / 客户编号 / 邮箱"]'))
        )
        user_input.clear()
        user_input.send_keys(username)

        pwd_input = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
        )
        pwd_input.clear()
        pwd_input.send_keys(password)
        log("已输入账号密码")
    except Exception as e:
        log(f"登录输入框未找到: {e}")
        return False

    try:
        login_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
        )
        login_btn.click()
        log("已点击登录按钮")
    except Exception as e:
        log(f"登录按钮定位失败: {e}")
        return False

    time.sleep(1)
    if check_password_error(driver):
        return False

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".btn_slide")))
        slider = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_slide"))
        )
        
        track = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".nc_scale"))
        )
        
        track_width = track.size['width']
        slider_width = slider.size['width']
        move_distance = track_width - slider_width - 10
        
        log(f"检测到滑块验证码，滑动距离: {move_distance}px")
        
        actions = ActionChains(driver)
        actions.click_and_hold(slider).perform()
        time.sleep(0.5)
        
        quick_distance = int(move_distance * random.uniform(0.6, 0.8))
        slow_distance = move_distance - quick_distance
        
        y_offset1 = random.randint(-2, 2)
        actions.move_by_offset(quick_distance, y_offset1).perform()
        time.sleep(random.uniform(0.1, 0.3))
        
        y_offset2 = random.randint(-2, 2)
        actions.move_by_offset(slow_distance, y_offset2).perform()
        time.sleep(random.uniform(0.05, 0.15))
        
        actions.release().perform()
        log("滑块拖动完成")
        
        time.sleep(1)
        if check_password_error(driver):
            return False
            
        WebDriverWait(driver, 10).until(lambda d: "www.jlc.com" in d.current_url and "passport.jlc.com" not in d.current_url)
        
    except Exception as e:
        log(f"滑块验证处理: {e}")
        time.sleep(1)
        if check_password_error(driver):
            return False

    log("等待登录跳转...")
    max_wait = 15
    jumped = False
    for i in range(max_wait):
        current_url = driver.current_url
        
        if "www.jlc.com" in current_url and "passport.jlc.com" not in current_url:
            log("成功跳转回首页")
            jumped = True
            break
        
        time.sleep(1)
    
    if not jumped:
        current_title = driver.title
        log(f"跳转超时，当前页面标题: {current_title}")
        return False

    return True

def main():
    if len(sys.argv) < 5:
        print("用法: python jlc.py 账号 密码 SKU 活动ID")
        print("示例: python jlc.py 13812345678 mypass123 SKUJC6 b51c4cf07b794278a79092674af8b563")
        sys.exit(1)
    
    username = sys.argv[1].strip()
    password = sys.argv[2].strip()
    target_sku = sys.argv[3].strip()
    activity_id = sys.argv[4].strip()
    
    log(f"启动任务 | 账号: {username} | 目标SKU: {target_sku} | 活动ID: {activity_id}")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
    
    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        if not perform_login(driver, username, password):
            log("登录失败，程序退出")
            sys.exit(1)
        
        driver.get("https://www.jlc.com/portal/anniversary-doubleActivity")
        log("已跳转到 https://www.jlc.com/portal/anniversary-doubleActivity")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        log("页面加载完毕")
        
        # 动态注入 JS 脚本，使用 replace 替换占位符
        raw_js_script = """
(function() {
'use strict';

// ================= 配置区域 =================  
const CONFIG = {  
    // 必填项：活动/分类ID  
    activityAccessId: "REPLACE_ACTIVITY_ID",   

    // 目标商品的 SKU Code  
    targetSku: "REPLACE_TARGET_SKU",   

    // 并发突发请求数量：在开抢时，脚本会立即发送这个数量的请求。  
    // 就30吧，立创服务器太拉了，太多别给他干爆了  
    BURST_COUNT: 30,   

    // 提前多少毫秒开始预热请求 (Lead Time)  
    leadTime: 300  
};  

// 接口地址  
const URLS = {  
    list: "/api/integral/seckill/ns/getSeckillGoods",  
    buy: "/api/integral/seckill/exchangeSeckillGoods"  
};  

console.log(`%c  嘉立创秒杀脚本 By zhangMonday 已加载 [目标SKU: ${CONFIG.targetSku}]`, "background: #222; color: #00ff00; font-size:14px;");  
console.log(` 已使用活动 ID: ${CONFIG.activityAccessId}`);  
console.log(` 轰炸数量: ${CONFIG.BURST_COUNT} 次`);  

async function fetchJson(url, data) {  
    try {  
        const response = await fetch(url, {  
            method: "POST",  
            headers: { "Content-Type": "application/json" },  
            body: JSON.stringify(data)  
        });  
        return await response.json();  
    } catch (e) {  
        return { error: true, message: e.message };  
    }  
}  

async function checkSystem() {  
    console.log("%c  开始系统自检...", "font-weight:bold; font-size:16px; color: #1890ff;");  

    console.log("%c[1/3] 正在请求商品列表...", "color: gray");  
    const listPayload = { categoryAccessId: CONFIG.activityAccessId };  
    const listRes = await fetchJson(URLS.list, listPayload);  
    console.log("列表接口返回:", listRes);  

    if (!listRes.data || !listRes.data.seckillGoodsResponseVos) {  
        throw new Error("列表获取失败，请检查 activityAccessId 或登录状态");  
    }  

    const target = listRes.data.seckillGoodsResponseVos.find(item => item.skuCode === CONFIG.targetSku);  
    if (!target) {  
        throw new Error(`未找到 SKU 为 [${CONFIG.targetSku}] 的商品。`);  
    }  
    console.log(`[2/3] SKU匹配成功: ${target.skuTitle}`);  
      
    console.log("%c[3/3] 正在模拟一次抢购请求 (测试 Payload)...", "color: orange");  
    const buyPayload = {  
        "goodsDetailAccessId": target.voucherSeckillActivityDetailAccessId,  
        "categoryAccessId": CONFIG.activityAccessId,  
        "source": 4  
    };  
    console.log("发送的抢购请求体:", buyPayload);  

    const buyRes = await fetchJson(URLS.buy, buyPayload);  
    console.log("抢购接口返回:", buyRes);  

    if (buyRes.code === 200 && buyRes.success) {  
        console.log("%c  我操居然抢购成功了！", "color: red; font-weight:bold");  
    } else {  
        console.log(`预期结果 (如果活动未开始): ${buyRes.message || "未知错误"}`);  
        console.log("%c  接口链路通畅，Payload 格式已确认无误。", "color: green; font-weight:bold");  
    }  
}  

function executeSeckill(goodsDetailAccessId) {  
    const payload = {  
        "goodsDetailAccessId": goodsDetailAccessId,  
        "categoryAccessId": CONFIG.activityAccessId,  
        "source": 4  
    };  

    if(!window.hasLoggedPayload) {  
        console.log("准备发送的最终 Payload:", JSON.stringify(payload));  
        window.hasLoggedPayload = true;  
    }  
      
    return fetchJson(URLS.buy, payload);  
}  

async function startJLCSeckill() {  
    console.log("启动正式抢购流程...");  
      
    const listPayload = { categoryAccessId: CONFIG.activityAccessId };  
      
    const listReqStart = Date.now();  
    const listRes = await fetchJson(URLS.list, listPayload);  
    const listReqEnd = Date.now();  
      
    if(!listRes.data) return console.error("无法获取列表，请检查 Activity ID 或登录状态");  
      
    const target = listRes.data.seckillGoodsResponseVos.find(item => item.skuCode === CONFIG.targetSku);  
    if(!target) return console.error("找不到目标商品 SKU，请检查 CONFIG.targetSku");  

    const goodsDetailAccessId = target.voucherSeckillActivityDetailAccessId;  

    const serverTime = new Date(listRes.data.currentTime).getTime();  
    const activityStartTime = new Date(listRes.data.activityBeginTime).getTime();  

    const RTT = listReqEnd - listReqStart;  
    const localTimeAtServerSend = listReqEnd - RTT / 2;  
    const timeDelta = serverTime - localTimeAtServerSend;   
      
    const adjustedStartTime = activityStartTime - timeDelta;   
    const trueTimeLeft = adjustedStartTime - Date.now();  

    console.log(`\\n=====  时间同步与调度 =====`);  
    console.log(`服务器当前时间: ${new Date(serverTime).toLocaleTimeString('zh-CN', { hour12: false })}.${serverTime % 1000}`);  
    console.log(`预期开抢时间: ${new Date(activityStartTime).toLocaleTimeString('zh-CN', { hour12: false })}.${activityStartTime % 1000}`);  
    console.log(`服务器/本地时差 (Server - Local): ${timeDelta.toFixed(0)} ms`);  
    console.log(`=============================`);  

    const run = () => {  
        console.log(`启动并发轰炸！立即发送 ${CONFIG.BURST_COUNT} 个请求...`);  
        let stop = false;  
        let count = 0;  
          
        const handleSuccess = (res) => {  
            if (res.code === 200 && res.success && !stop) {  
                stop = true;  
                setTimeout(() => {  
                    console.log(`%c  牛逼抢到了！总共发送 ${count} 次请求！ `, "font-size: 30px; color: red; font-weight: bold;");  
                    alert("抢购成功！");  
                }, 50);   
            }  
        };  
          
        for (let i = 0; i < CONFIG.BURST_COUNT; i++) {  
            if (stop) break;  
            count++;  
              
            executeSeckill(goodsDetailAccessId)  
                .then(handleSuccess)  
                .catch(e => { });   
        }  

        setTimeout(() => {  
            if(!stop) {  
                stop = true;  
                console.log(`停止请求（超时保护）。共计尝试发送 ${count} 次请求。没显示牛逼抢到了就是妹成功，哎`);  
            }  
        }, 15000);  
    };  

    if (trueTimeLeft <= CONFIG.leadTime) {  
        run();  
    } else {  
        setTimeout(run, trueTimeLeft - CONFIG.leadTime);  
        console.log(`定时器已设置，将在 ${ (trueTimeLeft - CONFIG.leadTime)/1000 } 秒后启动抢购...`);  
    }  
}  

(async () => {  
    try {  
        await checkSystem();  
        console.log("%c  自检通过，自动启动抢购流程...", "color: green; font-weight:bold");  
        await startJLCSeckill();  
    } catch (e) {  
        console.error("脚本执行失败:", e.message);  
    }  
})();

})();
"""
        js_script = raw_js_script.replace("REPLACE_ACTIVITY_ID", activity_id) \
                                 .replace("REPLACE_TARGET_SKU", target_sku)
        
        driver.execute_script(js_script)
        log("JS脚本已注入并执行（动态配置）")
        
        # 计算目标时间：当天北京时间10:05，如果已过则第二天
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        target_time = now.replace(hour=10, minute=5, second=0, microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        
        log(f"程序将等待直到北京时间 {target_time.strftime('%Y-%m-%d %H:%M:%S')} 后退出")
        
        last_logs = []
        while datetime.now(beijing_tz) < target_time:
            try:
                browser_logs = driver.get_log('browser')
                new_logs = [entry for entry in browser_logs if entry not in last_logs]
                for entry in new_logs:
                    log(f"浏览器控制台输出: {entry['message']}")
                last_logs.extend(new_logs)
            except Exception as e:
                log(f"获取浏览器日志出错: {e}")
            
            time.sleep(1)
        
        log("已达到北京时间10:05，程序正常退出")
        sys.exit(0)
    
    except Exception as e:
        log(f"程序执行错误: {e}")
        sys.exit(1)
    finally:
        driver.quit()
        log("浏览器已关闭")

if __name__ == "__main__":
    main()
