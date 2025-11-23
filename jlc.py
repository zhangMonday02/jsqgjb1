import os
import sys
import time
import random
import json
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==================== 统一日志 ====================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ==================== 浏览器初始化（关键！）===================
def create_driver():
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

    # 关键：双保险开启日志（兼容所有 ChromeDriver 版本）
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")

    driver = webdriver.Chrome(options=chrome_options)
    
    # 彻底隐藏 webdriver 特征
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.navigator.chrome = {runtime: {},  };
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """
    })
    return driver

# ==================== 登录核心函数（已强化跳转等待）===================
def perform_login(driver, username, password):
    wait = WebDriverWait(driver, 30)

    driver.get("https://passport.jlc.com/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F&bizExtendedParam=%7B%22jlcGroup_source%22%3A%22jlc%22%7D")
    log("打开登录页")

    # 切换到账号登录
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"账号登录")]')))
        btn.click()
        log("已切换到账号登录")
    except:
        log("账号登录已是默认")

    # 输入账号密码
    wait.until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="请输入手机号码 / 客户编号 / 邮箱"]')))
    driver.find_element(By.XPATH, '//input[@placeholder="请输入手机号码 / 客户编号 / 邮箱"]').send_keys(username)
    driver.find_element(By.XPATH, '//input[@type="password"]').send_keys(password)
    log("已填写账号密码")

    # 点击登录
    driver.find_element(By.CSS_SELECTOR, "button.submit").click()
    log("点击登录按钮")

    # 处理滑块
    try:
        slider = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".btn_slide")))
        track = driver.find_element(By.CSS_SELECTOR, ".nc_scale")
        distance = track.size['width'] - slider.size['width'] - random.randint(5, 15)

        actions = ActionChains(driver)
        actions.click_and_hold(slider).move_by_offset(distance, random.randint(-3, 3)).pause(0.3).release().perform()
        log(f"滑块已拖动 {distance}px")
        time.sleep(2)
    except:
        log("本次无滑块或滑块已自动通过")

    # 关键：等待真正跳转（最多 30 秒）
    try:
        WebDriverWait(driver, 30).until(
            lambda d: "www.jlc.com" in d.current_url and "passport.jlc.com" not in d.current_url
        )
        log("登录成功！已跳转到 www.jlc.com")
        return True
    except:
        log(f"登录失败，当前URL: {driver.current_url}")
        log(f"页面标题: {driver.title}")
        return False

# ==================== 主程序 ====================
def main():
    if len(sys.argv) < 5:
        print("用法: python jlc.py <账号> <密码> <SKU> <活动ID>")
        print("示例: python jlc.py 13812345678 123456 SKUJC6 b51c4cf07b794278a79092674af8b563")
        sys.exit(1)

    username = sys.argv[1].strip()
    password = sys.argv[2].strip()
    target_sku = sys.argv[3].strip()
    activity_id = sys.argv[4].strip()

    log(f"启动 | 账号: {username} | SKU: {target_sku} | 活动ID: {activity_id}")

    driver = create_driver()

    try:
        if not perform_login(driver, username, password):
            log("登录失败，程序退出")
            sys.exit(1)

        # 进入活动页
        driver.get("https://www.jlc.com/portal/anniversary-doubleActivity")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        log("已进入活动页面")

        # 动态注入 JS（使用 replace 避免大括号冲突）
        js_template = """
(function() {
'use strict';
const CONFIG = {
    activityAccessId: "REPLACE_ACTIVITY_ID",
    targetSku: "REPLACE_TARGET_SKU",
    BURST_COUNT: 30,
    leadTime: 300
};
const URLS = { list: "/api/integral/seckill/ns/getSeckillGoods", buy: "/api/integral/seckill/exchangeSeckillGoods" };

console.log(`%c 嘉立创秒杀脚本已加载 | SKU: \( {CONFIG.targetSku} | ID: \){CONFIG.activityAccessId}`, "color:#0f0;font-size:16px");

async function fetchJson(u,d){try{const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});return await r.json()}catch(e){return{error:true}}}

async function checkSystem(){
    const res = await fetchJson(URLS.list, {categoryAccessId: CONFIG.activityAccessId});
    if(!res.data) throw "获取列表失败";
    const t = res.data.seckillGoodsResponseVos.find(x=>x.skuCode===CONFIG.targetSku);
    if(!t) throw "未找到目标SKU";
    console.log("自检通过:", t.skuTitle);
}
function execute(gid){
    const p = {goodsDetailAccessId: gid, categoryAccessId: CONFIG.activityAccessId, source: 4};
    if(!window.p) {console.log("Payload:", p); window.p=1;}
    return fetchJson(URLS.buy, p);
}
async function start(){
    const list = await fetchJson(URLS.list, {categoryAccessId: CONFIG.activityAccessId});
    if(!list.data) return console.error("列表失败");
    const target = list.data.seckillGoodsResponseVos.find(x=>x.skuCode===CONFIG.targetSku);
    if(!target) return console.error("SKU不存在");
    const gid = target.voucherSeckillActivityDetailAccessId;

    const serverTime = new Date(list.data.currentTime).getTime();
    const startTime = new Date(list.data.activityBeginTime).getTime();
    const delta = serverTime - Date.now();
    const realStart = startTime - delta;
    const waitMs = realStart - Date.now() - CONFIG.leadTime;

    console.log(`服务器时间差: \( {delta}ms | 预计开抢: \){new Date(startTime).toLocaleString()}`);

    const run = () => {
        console.log("开始轰炸！");
        let c=0, stop=false;
        const success = r => { if(r.code===200 && r.success && !stop){ stop=true; console.log("%c 抢到了！！！", "font-size:40px;color:red"); alert("抢到啦！"); }};
        for(let i=0;i<CONFIG.BURST_COUNT;i++){ if(stop)break; c++; execute(gid).then(success); }
        setTimeout(()=>{if(!stop)console.log("超时未抢到");},15000);
    };
    if(waitMs<=0) run(); else setTimeout(run, waitMs);
}
(async()=>{await checkSystem(); await start();})();
})();
"""

        final_js = js_template.replace("REPLACE_ACTIVITY_ID", activity_id).replace("REPLACE_TARGET_SKU", target_sku)
        driver.execute_script(final_js)
        log("JS 抢购脚本已注入")

        # 等待到 10:05（可自行改时间）
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz)
        target = now.replace(hour=10, minute=5, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        log(f"程序将运行到北京时间 {target.strftime('%Y-%m-%d %H:%M:%S')} 后退出")

        last = []
        while datetime.now(tz) < target:
            try:
                logs = driver.get_log('browser')
                for e in logs:
                    if e not in last:
                        log(f"JS: {e['message']}")
                last = logs[:]
            except: pass
            time.sleep(1)

        log("时间到，程序结束")
    except Exception as e:
        log(f"异常: {e}")
    finally:
        driver.quit()
        log("浏览器已关闭")

if __name__ == "__main__":
    main()
