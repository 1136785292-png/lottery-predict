"""
报告生成器
- 把回测结果、每日推荐生成成 JSON 文件给前端展示
"""
import json
from pathlib import Path
from datetime import datetime

from collect import load_processed
from backtest import OUTPUT_DIR, compare_strategies

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
DATA_DIR = DOCS_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_backtest_report():
    """生成回测报告 JSON"""
    print("[INFO] 生成回测报告...")
    history = load_processed("football_history")

    if history.empty:
        print("[WARN] 没有历史数据，先生成占位报告")
        placeholder = {
            "generated_at": datetime.now().isoformat(),
            "status": "no_data",
            "message": "等待第一次 GitHub Actions 跑回测",
        }
        with open(DATA_DIR / "backtest.json", "w", encoding="utf-8") as f:
            json.dump(placeholder, f, indent=2, ensure_ascii=False)
        return

    # 跑 3 策略对比
    comparison = compare_strategies(history, max_periods=500)

    # 读历史数据
    histories = {}
    for s in ["random", "odds_only", "dual_track"]:
        hist_path = OUTPUT_DIR / f"history_{s}.csv"
        if hist_path.exists():
            import pandas as pd
            hdf = pd.read_csv(hist_path)
            # 转成前端友好的格式
            histories[s] = {
                "dates": hdf["date"].tolist(),
                "bankrolls": hdf["bankroll"].tolist(),
                "pnls": hdf["pnl"].tolist(),
                "win_count": int(hdf["both_win"].sum()),
                "total": len(hdf),
            }

    report = {
        "generated_at": datetime.now().isoformat(),
        "status": "ok",
        "comparison": comparison,
        "histories": histories,
    }

    with open(DATA_DIR / "backtest.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[OK] 报告已生成：{DATA_DIR / 'backtest.json'}")


def generate_daily_report():
    """生成每日推荐 JSON（占位）"""
    print("[INFO] 生成每日推荐...")
    placeholder = {
        "generated_at": datetime.now().isoformat(),
        "status": "placeholder",
        "message": "每日推荐功能开发中 - 中国体彩数据接入后启用",
        "recommendation": None,
    }
    with open(DATA_DIR / "daily.json", "w", encoding="utf-8") as f:
        json.dump(placeholder, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    generate_backtest_report()
    generate_daily_report()
    print("[DONE]")
