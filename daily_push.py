"""
Render Cron 入口：執行選股分析並推播至 LINE
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from agents.orchestrator import OrchestratorAgent
from agents.line_notifier import push_report, push_text

def main():
    try:
        agent  = OrchestratorAgent()
        report = agent.run()
        ok = push_report(report)
        print("LINE 推播:", "✅ 成功" if ok else "❌ 失敗")
        sys.exit(0 if ok else 1)
    except Exception as e:
        push_text(f"❌ Stock_AI_MultiAgent 執行失敗：{e}")
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
