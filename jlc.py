import os
import sys
import time
import json
import tempfile
import random
import requests
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 全局变量用于收集总结日志
in_summary = False
summary_logs = []

def log(msg):
    full_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(full_msg, flush=True)
    if in_summary:
        summary_logs.append(msg)  # 只收集纯消息，无时间戳

def format_nickname(nickname):
    """格式化昵称，只显示第一个字和最后一个字，中间用星号代替"""
    if not nickname or len(nickname.strip()) == 0:
        return "未知用户"
    
    nickname = nickname.strip()
    if len(nickname) == 1:
        return f"{nickname}*"
    elif len(nickname) == 2:
        return f"{nickname[0]}*"
    else:
        return f"{nickname[0]}{'*' * (len(nickname)-2)}{nickname[-1]}"

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

def get_user_nickname_from_api(driver):
    """通过API获取用户昵称"""
    try:
        # 获取当前页面的Cookie
        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'application/json, text/plain, */*',
            'cookie': cookie_str
        }
        
        # 调用用户信息API
        response = requests.get("https://oshwhub.com/api/users", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data.get('success'):
                nickname = data.get('result', {}).get('nickname', '')
                if nickname:
                    formatted_nickname = format_nickname(nickname)
                    log(f"👤 昵称: {formatted_nickname}")
                    return formatted_nickname
        
        log(f"⚠ 无法获取用户昵称")
        return None
    except Exception as e:
        log(f"⚠ 获取用户昵称失败: {e}")
        return None

def ensure_login_page(driver):
    """确保进入登录页面，如果未检测到登录页面则重启浏览器"""
    max_restarts = 5
    restarts = 0
    
    while restarts < max_restarts:
        try:
            driver.get("https://oshwhub.com/sign_in")
            log(f"已打开 JLC 签到页")
            
            WebDriverWait(driver, 10).until(lambda d: "passport.jlc.com/login" in d.current_url)
            current_url = driver.current_url

            # 检查是否在登录页面
            if "passport.jlc.com/login" in current_url:
                log(f"✅ 检测到未登录状态")
                return True
            else:
                restarts += 1
                if restarts < max_restarts:
                    # 静默重启浏览器
                    driver.quit()
                    
                    # 重新初始化浏览器
                    chrome_options = Options()
                    chrome_options.add_argument("--headless=new")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--window-size=1920,1080")
                    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
                    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)

                    caps = DesiredCapabilities.CHROME
                    caps['goog:loggingPrefs'] = {'browser': 'ALL'}
                    
                    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    # 静默等待后继续循环
                    time.sleep(2)
                else:
                    log(f"❌ 重启浏览器{max_restarts}次后仍无法进入登录页面")
                    return False
                    
        except Exception as e:
            restarts += 1
            if restarts < max_restarts:
                try:
                    driver.quit()
                except:
                    pass
                
                # 重新初始化浏览器
                chrome_options = Options()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                caps = DesiredCapabilities.CHROME
                caps['goog:loggingPrefs'] = {'browser': 'ALL'}
                
                driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                time.sleep(2)
            else:
                log(f"❌ 重启浏览器{max_restarts}次后仍出现异常: {e}")
                return False
    
    return False

def check_password_error(driver):
    """检查页面是否显示密码错误提示"""
    try:
        # 等待可能出现的错误提示元素
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
                # 使用短暂的等待来检查错误提示
                error_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if error_element.is_displayed():
                    error_text = error_element.text.strip()
                    if any(keyword in error_text for keyword in ['账号或密码不正确', '用户名或密码错误', '密码错误', '登录失败']):
                        log(f"❌ 检测到账号或密码错误，跳过此账号")
                        return True
            except:
                continue
                
        return False
    except Exception as e:
        log(f"⚠ 检查密码错误时出现异常: {e}")
        return False

def sign_in_account(username, password):
    """为单个账号执行完整的登录流程"""
    log(f"开始处理账号")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'browser': 'ALL'}
    
    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    wait = WebDriverWait(driver, 25)
    
    # 记录详细结果
    result = {
        'nickname': '未知',
        'login_success': False,
        'password_error': False
    }

    try:
        # 1. 确保进入登录页面
        if not ensure_login_page(driver):
            result['login_success'] = False
            return result, driver

        current_url = driver.current_url

        # 2. 登录流程
        log(f"检测到未登录状态，正在执行登录流程...")

        try:
            phone_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"账号登录")]'))
            )
            phone_btn.click()
            log(f"已切换账号登录")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="请输入手机号码 / 客户编号 / 邮箱"]')))
        except Exception as e:
            log(f"账号登录按钮可能已默认选中: {e}")

        # 输入账号密码
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
            log(f"已输入账号密码")
        except Exception as e:
            log(f"❌ 登录输入框未找到: {e}")
            result['login_success'] = False
            return result, driver

        # 点击登录
        try:
            login_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
            )
            login_btn.click()
            log(f"已点击登录按钮")
        except Exception as e:
            log(f"❌ 登录按钮定位失败: {e}")
            result['login_success'] = False
            return result, driver

        # 立即检查密码错误提示（点击登录按钮后）
        time.sleep(1)  # 给错误提示一点时间显示
        if check_password_error(driver):
            result['password_error'] = True
            result['login_success'] = False
            return result, driver

        # 处理滑块验证
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".btn_slide")))
        try:
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
            log(f"滑块拖动完成")
            
            # 滑块验证后立即检查密码错误提示
            time.sleep(1)  # 给错误提示一点时间显示
            if check_password_error(driver):
                result['password_error'] = True
                result['login_success'] = False
                return result, driver
                
            WebDriverWait(driver, 10).until(lambda d: "oshwhub.com" in d.current_url and "passport.jlc.com" not in d.current_url)
            
        except Exception as e:
            log(f"滑块验证处理: {e}")
            # 滑块验证失败后检查密码错误
            time.sleep(1)
            if check_password_error(driver):
                result['password_error'] = True
                result['login_success'] = False
                return result, driver

        # 等待跳转
        log(f"等待登录跳转...")
        max_wait = 15
        jumped = False
        for i in range(max_wait):
            current_url = driver.current_url
            
            # 检查是否成功跳转回签到页面
            if "oshwhub.com" in current_url and "passport.jlc.com" not in current_url:
                log(f"成功跳转回签到页面")
                jumped = True
                break
            
            time.sleep(1)
        
        if not jumped:
            current_title = driver.title
            log(f"❌ 跳转超时，当前页面标题: {current_title}")
            result['login_success'] = False
            return result, driver

        # 3. 获取用户昵称
        time.sleep(1)
        nickname = get_user_nickname_from_api(driver)
        if nickname:
            result['nickname'] = nickname
        else:
            result['nickname'] = '未知'

        result['login_success'] = True
        log(f"✅ 登录成功")

        # 4. 打开活动页面
        log(f"打开活动页面...")
        activity_url = "https://www.jlc.com/portal/anniversary-doubleActivity?spm=PCB.Homepage.banner.1003"
        driver.get(activity_url)
        log(f"已打开活动页面: {activity_url}")
        
        # 5. 等待页面完全加载并额外等待10秒
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        log(f"页面加载完成，额外等待10秒...")
        time.sleep(10)

    except Exception as e:
        log(f"❌ 程序执行错误: {e}")
        result['login_success'] = False
    return result, driver

def process_account(username, password):
    """处理单个账号，包含重试机制，并合并多次尝试的最佳结果"""
    max_retries = 3  # 最多重试3次
    merged_result = {
        'nickname': '未知',
        'login_success': False,
        'password_error': False  # 标记密码错误
    }
    
    merged_success = {'login': False}
    driver = None

    for attempt in range(max_retries + 1):  # 第一次执行 + 重试次数
        result, current_driver = sign_in_account(username, password)
        driver = current_driver if current_driver else driver
        
        # 如果检测到密码错误，立即停止重试
        if result.get('password_error'):
            merged_result['password_error'] = True
            merged_result['login_success'] = False
            merged_result['nickname'] = '未知'
            break
        
        # 合并登录结果：如果本次成功且之前未成功，则更新
        if result['login_success'] and not merged_success['login']:
            merged_success['login'] = True
            merged_result['login_success'] = True
            merged_result['nickname'] = result['nickname']
        
        # 检查是否还需要重试（排除密码错误的情况）
        if not should_retry(merged_success['login'], merged_result['password_error']) or attempt >= max_retries:
            break
        else:
            log(f"🔄 准备第 {attempt + 1} 次重试，等待 {random.randint(2, 6)} 秒后重新开始...")
            time.sleep(random.randint(2, 6))
    
    # 最终设置success字段基于合并
    merged_result['login_success'] = merged_success['login']
    
    return merged_result, driver

def should_retry(login_success, password_error):
    """判断是否需要重试：如果登录未成功，且不是密码错误"""
    need_retry = (not login_success) and not password_error
    return need_retry

def execute_js_and_monitor_logs(driver):
    js_script = """
(function() {
'use strict';

// ================= 配置区域 =================  
const CONFIG = {  
    // 必填项：活动/分类ID  
    activityAccessId: "b51c4cf07b794278a79092674af8b563",   

    // 目标商品的 SKU Code  
    targetSku: "SKUJC6",   

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

console.log(`%c 🚀 嘉立创秒杀脚本 By zhangMonday 已加载 [目标SKU: ${CONFIG.targetSku}]`, "background: #222; color: #00ff00; font-size:14px;");  
console.log(`🔑 已使用活动 ID: ${CONFIG.activityAccessId}`);  
console.log(`🔥 轰炸数量: ${CONFIG.BURST_COUNT} 次`);  

// ================= 通用请求函数 =================  
async function fetchJson(url, data) {  
    try {  
        const response = await fetch(url, {  
            method: "POST",  
            headers: { "Content-Type": "application/json" },  
            body: JSON.stringify(data)  
        });  
        return await response.json();  
    } catch (e) {  
        // 异步请求失败不影响其他请求  
        return { error: true, message: e.message };  
    }  
}  

// ================= 调试/自检功能 (checkSystem) =================  
async function checkSystem() {  
    console.log("%c 🔍 开始系统自检...", "font-weight:bold; font-size:16px; color: #1890ff;");  

    // [1/3] 列表  
    console.log("%c[1/3] 正在请求商品列表...", "color: gray");  
    const listPayload = { categoryAccessId: CONFIG.activityAccessId };  
    const listRes = await fetchJson(URLS.list, listPayload);  
    console.log("📄 列表接口返回:", listRes);  

    if (!listRes.data || !listRes.data.seckillGoodsResponseVos) {  
        throw new Error("❌ 列表获取失败，请检查 activityAccessId 或登录状态");  
    }  

    // [2/3] 验证 SKU  
    const target = listRes.data.seckillGoodsResponseVos.find(item => item.skuCode === CONFIG.targetSku);  
    if (!target) {  
        throw new Error(`❌ 未找到 SKU 为 [${CONFIG.targetSku}] 的商品。`);  
    }  
    console.log(`✅ [2/3] SKU匹配成功: ${target.skuTitle}`);  
      
    // [3/3] 测试抢购接口 (单次发送)  
    console.log("%c[3/3] 正在模拟一次抢购请求 (测试 Payload)...", "color: orange");  
    const buyPayload = {  
        "goodsDetailAccessId": target.voucherSeckillActivityDetailAccessId,  
        "categoryAccessId": CONFIG.activityAccessId,  
        "source": 4  
    };  
    console.log("📦 发送的抢购请求体:", buyPayload);  

    const buyRes = await fetchJson(URLS.buy, buyPayload);  
    console.log("📡 抢购接口返回:", buyRes);  

    if (buyRes.code === 200 && buyRes.success) {  
        console.log("%c 🎉 我操居然抢购成功了！", "color: red; font-weight:bold");  
    } else {  
        console.log(`ℹ️ 预期结果 (如果活动未开始): ${buyRes.message || "未知错误"}`);  
        console.log("%c ✅ 接口链路通畅，Payload 格式已确认无误。", "color: green; font-weight:bold");  
    }  
}  

// ================= 核心执行函数 (执行抢购) =================  
// 此函数现在返回 Promise，用于并发调用  
function executeSeckill(goodsDetailAccessId) {  
    const payload = {  
        "goodsDetailAccessId": goodsDetailAccessId,  
        "categoryAccessId": CONFIG.activityAccessId,  
        "source": 4  
    };  

    // 仅在第一次打印 payload 确认  
    if(!window.hasLoggedPayload) {  
        console.log("💣 准备发送的最终 Payload:", JSON.stringify(payload));  
        window.hasLoggedPayload = true;  
    }  
      
    return fetchJson(URLS.buy, payload);  
}  

// ================= 正式抢购流程=================  
async function startJLCSeckill() {  
    console.log("🚀 启动正式抢购流程...");  
      
    // 1. 获取商品信息并进行时间同步  
    const listPayload = { categoryAccessId: CONFIG.activityAccessId };  
      
    const listReqStart = Date.now(); // 记录本地请求开始时间  
    const listRes = await fetchJson(URLS.list, listPayload);  
    const listReqEnd = Date.now();   // 记录本地请求结束时间  
      
    if(!listRes.data) return console.error("❌ 无法获取列表，请检查 Activity ID 或登录状态");  
      
    const target = listRes.data.seckillGoodsResponseVos.find(item => item.skuCode === CONFIG.targetSku);  
    if(!target) return console.error("❌ 找不到目标商品 SKU，请检查 CONFIG.targetSku");  

    const goodsDetailAccessId = target.voucherSeckillActivityDetailAccessId;  

    // 2. 时间校准计算  
    const serverTime = new Date(listRes.data.currentTime).getTime();  
    const activityStartTime = new Date(listRes.data.activityBeginTime).getTime();  

    const RTT = listReqEnd - listReqStart;  
    const localTimeAtServerSend = listReqEnd - RTT / 2;  
    const timeDelta = serverTime - localTimeAtServerSend;   
      
    const adjustedStartTime = activityStartTime - timeDelta;   
    const trueTimeLeft = adjustedStartTime - Date.now();  

    // 3. 显示时间信息  
    console.log(`\n===== 🕒 时间同步与调度 =====`);  
    console.log(`⏱️ 服务器当前时间: ${new Date(serverTime).toLocaleTimeString('zh-CN', { hour12: false })}.${serverTime % 1000}`);  
    console.log(`⏰ 预期开抢时间: ${new Date(activityStartTime).toLocaleTimeString('zh-CN', { hour12: false })}.${activityStartTime % 1000}`);  
    console.log(`⚙️ 服务器/本地时差 (Server - Local): ${timeDelta.toFixed(0)} ms`);  
    console.log(`=============================`);  

    // 4. 定义执行器 (并发)  
    const run = () => {  
        console.log(`🔥 启动并发轰炸！立即发送 ${CONFIG.BURST_COUNT} 个请求...`);  
        let stop = false;  
        let count = 0;  
          
        // Success handler for all concurrent Promises  
        const handleSuccess = (res) => {  
            if (res.code === 200 && res.success && !stop) {  
                stop = true;  
                // 在成功后设置一个小的定时器，确保停止计时器  
                setTimeout(() => {  
                    console.log(`%c 🎉🎉🎉 牛逼抢到了！总共发送 ${count} 次请求！ 🎉🎉🎉`, "font-size: 30px; color: red; font-weight: bold;");  
                    alert("抢购成功！");  
                }, 50);   
            }  
        };  
          
        // 发送请求突发循环 (Fire and Forget)  
        for (let i = 0; i < CONFIG.BURST_COUNT; i++) {  
            if (stop) break;  
            count++;  
              
            executeSeckill(goodsDetailAccessId)  
                .then(handleSuccess)  
                .catch(e => { /* 忽略网络层面的错误 */ });   
        }  

        // 15秒后停止 (检查计时器来停止，以防成功处理失败)  
        setTimeout(() => {  
            if(!stop) {  
                stop = true;  
                console.log(`🛑 停止请求（超时保护）。共计尝试发送 ${count} 次请求。没显示牛逼抢到了就是妹成功，哎`);  
            }  
        }, 15000);  
    };  

    // 5. 倒计时调度  
    if (trueTimeLeft <= CONFIG.leadTime) {  
        run();  
    } else {  
        setTimeout(run, trueTimeLeft - CONFIG.leadTime);  
        console.log(`⏳ 定时器已设置，将在 ${ (trueTimeLeft - CONFIG.leadTime)/1000 } 秒后启动抢购...`);  
    }  
}  

// 自动执行自检和抢购  
(async () => {  
    try {  
        await checkSystem();  
        console.log("%c ✅ 自检通过，自动启动抢购流程...", "color: green; font-weight:bold");  
        await startJLCSeckill();  
    } catch (e) {  
        console.error("❌ 脚本执行失败:", e.message);  
    }  
})();

})();
    """
    log("执行控制台脚本...")
    driver.execute_script(js_script)

    log("开始监控浏览器控制台日志...")
    last_log_time = time.time()
    while True:
        logs = driver.get_log('browser')
        for entry in logs:
            if entry['level'] == 'SEVERE':
                log(f"[浏览器控制台 - ERROR] {entry['message']}")
            elif entry['level'] == 'WARNING':
                log(f"[浏览器控制台 - WARN] {entry['message']}")
            else:
                log(f"[浏览器控制台] {entry['message']}")
        time.sleep(1)  # 每秒检查一次日志

        # 检查是否到达退出时间
        now = datetime.now(timezone(timedelta(hours=8)))  # 北京时间
        target_time = datetime(now.year, now.month, now.day, 10, 5, 0, tzinfo=timezone(timedelta(hours=8)))
        if now >= target_time:
            log("已到达北京时间10:05，程序正常退出")
            sys.exit(0)

# 推送函数（保留原函数）
def push_summary():
    if not summary_logs:
        return
    
    title = "嘉立创活动总结"
    text = "\n".join(summary_logs)
    full_text = f"{title}\n{text}"  # 有些平台不需要单独标题
    
    # Telegram
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if telegram_bot_token and telegram_chat_id:
        try:
            url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
            params = {'chat_id': telegram_chat_id, 'text': full_text}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                log("Telegram-日志已推送")
        except:
            pass  # 静默失败

    # 企业微信 (WeChat Work)
    wechat_webhook_key = os.getenv('WECHAT_WEBHOOK_KEY')
    if wechat_webhook_key:
        try:
            if wechat_webhook_key.startswith('https://'):
                url = wechat_webhook_key
            else:
                url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={wechat_webhook_key}"
            body = {"msgtype": "text", "text": {"content": full_text}}
            response = requests.post(url, json=body)
            if response.status_code == 200:
                log("企业微信-日志已推送")
        except:
            pass

    # 钉钉 (DingTalk)
    dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK')
    if dingtalk_webhook:
        try:
            if dingtalk_webhook.startswith('https://'):
                url = dingtalk_webhook
            else:
                url = f"https://oapi.dingtalk.com/robot/send?access_token={dingtalk_webhook}"
            body = {"msgtype": "text", "text": {"content": full_text}}
            response = requests.post(url, json=body)
            if response.status_code == 200:
                log("钉钉-日志已推送")
        except:
            pass

    # PushPlus
    pushplus_token = os.getenv('PUSHPLUS_TOKEN')
    if pushplus_token:
        try:
            url = "http://www.pushplus.plus/send"
            body = {"token": pushplus_token, "title": title, "content": text}
            response = requests.post(url, json=body)
            if response.status_code == 200:
                log("PushPlus-日志已推送")
        except:
            pass

    # Server酱
    serverchan_sckey = os.getenv('SERVERCHAN_SCKEY')
    if serverchan_sckey:
        try:
            url = f"https://sctapi.ftqq.com/{serverchan_sckey}.send"
            body = {"title": title, "desp": text}
            response = requests.post(url, data=body)
            if response.status_code == 200:
                log("Server酱-日志已推送")
        except:
            pass

    # 酷推 (CoolPush)
    coolpush_skey = os.getenv('COOLPUSH_SKEY')
    if coolpush_skey:
        try:
            url = f"https://push.xuthus.cc/send/{coolpush_skey}?c={full_text}"
            response = requests.get(url)
            if response.status_code == 200:
                log("酷推-日志已推送")
        except:
            pass

    # 自定义API
    custom_webhook = os.getenv('CUSTOM_WEBHOOK')
    if custom_webhook:
        try:
            body = {"title": title, "content": text}
            response = requests.post(custom_webhook, json=body)
            if response.status_code == 200:
                log("自定义API-日志已推送")
        except:
            pass

def main():
    global in_summary
    
    if len(sys.argv) < 3:
        print("用法: python choujiang.py 账号 密码")
        print("示例: python choujiang.py user1 pwd1")
        sys.exit(1)
    
    username = sys.argv[1].strip()
    password = sys.argv[2].strip()
    
    log(f"开始处理账号的任务")
    
    # 处理单个账号
    result, driver = process_account(username, password)
    
    if result['login_success']:
        # 执行 JS 并监控日志，直到时间到
        execute_js_and_monitor_logs(driver)
    else:
        log("❌ 登录失败，程序退出")
        if driver:
            driver.quit()
        sys.exit(1)
    
    # 输出总结（如果需要）
    log("=" * 70)
    in_summary = True  # 启用总结收集
    log("📊 活动任务完成总结")
    log("=" * 70)
    
    # 总体统计（简化版）
    log(f"登录状态: {'✅ 成功' if result['login_success'] else '❌ 失败'}")
    if result['password_error']:
        log("❌ 账号或密码错误")
    
    log("=" * 70)
    
    # 推送总结
    push_summary()
    
    if driver:
        driver.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
