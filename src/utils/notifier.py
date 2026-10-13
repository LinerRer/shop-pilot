import requests
from utils.config import settings


def send_notification(title: str, content: str) -> bool:
    """主动推送异常告警。配置了webhook则真实发送，未配置则模拟打印到控制台。"""
    text = f"【{title}】\n{content}"

    if not settings.notify_webhook_url:
        print("=" * 50)
        print("[模拟推送] 未配置 webhook，以下为推送内容：")
        print(text)
        print("=" * 50)
        return True

    if settings.notify_channel == "feishu":
        payload = {"msg_type": "text", "content": {"text": text}}
    else:
        payload = {"msgtype": "text", "text": {"content": text}}

    try:
        resp = requests.post(settings.notify_webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[推送失败] {e}")
        return False
