import asyncio
import sys
import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from agent.generate_report import main


def run_report():
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 开始自动生成运营日报...")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"日报生成失败：{e}")


if __name__ == "__main__":
    sched = BlockingScheduler(timezone="Asia/Shanghai")
    sched.add_job(run_report, CronTrigger(hour=8, minute=0))
    print("无人值守模式已启动：每天早上 8:00 自动生成运营日报。按 Ctrl+C 停止。")
    sched.start()
