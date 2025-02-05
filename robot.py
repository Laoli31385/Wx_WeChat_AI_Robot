import os
import time
import requests
from dotenv import load_dotenv
from wxauto import WeChat

load_dotenv()

class ChatBotConfig:
    def __init__(self):
        self.api_key = os.getenv('SI_API_KEY')
        self.target_user = os.getenv('TARGET_USER')
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.cooldown = 5
        self.max_retries = 3

class PersonaManager:
    def __init__(self):
        self.system_prompt = """
        你是一个男生，名字叫xx。说话风格要：
        1. xxxxxx
        2. xxxxxx
        3. xxxxxx
        """

class MessageHandler:
    def __init__(self):
        self.wx = WeChat()
        self.last_msg_id = None
        
        # 初始化监听（增加重试机制）
        retry_count = 0
        while retry_count < 3:
            try:
                self.wx.AddListenChat(who = os.getenv('TARGET_USER'), savepic=False)
                break
            except Exception as e:
                print(f"监听初始化失败，重试中... ({retry_count+1}/3)")
                time.sleep(2)
                retry_count += 1

    def safe_reply(self, config):
        try:
            
            # 获取消息时增加空值校验
            msgs = self.wx.GetListenMessage()
            if not msgs:  # 关键修复点1：处理空消息
                return

            for chat in msgs:
                if chat.who == config.target_user:
                    for msg in msgs[chat]:
                        # 关键修复点2：校验消息有效性
                        if (msg.type == 'friend' 
                            and msg.sender != '自己' 
                            and msg.id != self.last_msg_id 
                            and msg.content is not None):
                            
                            print(f"收到原始消息: {msg.__dict__}")  # 查看消息对象完整结构
                            print("--------------------------------------")
                            current_time = time.time()
                            if current_time  > config.cooldown:#if current_time - msg.time > config.cooldown:
                                response = self.generate_response(msg.content, config)
                                if response:  # 关键修复点3：校验API返回
                                    self.wx.SendMsg(response, who=config.target_user)
                                    self.last_msg_id = msg.id
        except Exception as e:
            print(f"安全异常: {str(e)}")

    def generate_response(self, prompt, config):
        """生成回复（增加空内容处理）"""
        #headers = {"Authorization": "sk-rzvgqmzsmbfjfavayjflvdpjoldgqcxybuylurkbhbmmymuu"}
        headers = {"Authorization": f"Bearer {config.api_key}",
                   "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [
                {"role": "system", "content": PersonaManager().system_prompt},
                {"role": "user", "content": prompt[:512]}  # 限制输入长度
            ],
            "temperature": 0.3,
            "frequency_penalty": 0.5,
            "max_tokens": 2048,
            "n": 1,
            "stream": False,
            "top_k" : 50,
            "top_p" : 0.6,
            "response_format": {
                "type": "text"
            }
            
        }
        
        
        try:
            response = requests.post(config.api_url, json=payload, headers=headers, timeout=60)
            result = response.json()
            # 关键修复点4：安全获取返回内容
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"API响应: {response.text}")  # 查看原始API返回
            return content[:100] if content else "嗯？好像没听清楚呢～"  # 空内容兜底
        except Exception as e:
            print(f"API调用异常: {str(e)}")
            print("--------------------------------------")
            return "现在网络不好，等会儿再来找我聊叭[爱心][爱心][爱心]~~"

if __name__ == "__main__":
    config = ChatBotConfig()
    handler = MessageHandler()
    
    print(">>> 安全模式已启动")
    print("--------------------------------------")
    try:
        while True:
            handler.safe_reply(config)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n>>> 安全退出程序")