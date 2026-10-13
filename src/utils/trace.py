import json
import datetime
from utils.config import settings


def log_trace(tag, messages):
    settings.log_dir.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    path = settings.log_dir / f"trace_{today}.log"

    lines = [f"\n===== {datetime.datetime.now().strftime('%H:%M:%S')} | {tag} ====="]
    for m in messages:
        content = str(m.content).strip()[:300] if m.content else ""
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                args = json.dumps(tc.get("args", {}), ensure_ascii=False)[:200]
                lines.append(f"  [调用工具] {tc['name']}  参数: {args}")
        elif type(m).__name__ == "ToolMessage":
            lines.append(f"  [工具返回] {content}")
        elif type(m).__name__ == "AIMessage" and not tool_calls:
            lines.append(f"  [最终回答] {content}")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path
