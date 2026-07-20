"""
每日推荐（占位实现）
- MVP 阶段先用历史最近数据 + 模拟"今日比赛"
- 后续接入中国体彩官方数据
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

from collect import load_processed
from model import dual_track_evaluate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DAILY_DIR = DATA_DIR / "daily"
DAILY_DIR.mkdir(parents=True, exist_ok=True)


def simulate_today_matches(history_df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """
    模拟"今日比赛"
    MVP 阶段：从历史数据中随机取 n 场赔率 ≤ 1.5 的比赛
    真实接入后：从中国体彩 API 拉取
    """
    if history_df.empty:
        return pd.DataFrame()

    # 取最近 30 天内赔率 ≤ 1.5 的比赛作为"今日比赛"
    last_date = history_df["date"].max()
    cutoff = last_date - timedelta(days=30)
    recent = history_df[
        (history_df["date"] >= cutoff) &
        (history_df["odds_home"] <= 1.5) &
        (history_df["odds_home"] >= 1.05)
    ]

    if len(recent) < n:
        return recent.head(n)

    return recent.sample(n=min(n, len(recent)), random_state=int(datetime.now().timestamp()) % 1000)


def generate_daily_recommendation():
    """生成今日推荐"""
    history = load_processed("football_history")
    today_matches = simulate_today_matches(history, n=20)

    if today_matches.empty:
        result = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "no_data",
            "recommendation": None,
            "message": "暂无今日比赛数据",
        }
    else:
        # 对每场比赛评分
        scored = []
        for _, row in today_matches.iterrows():
            eval_ = dual_track_evaluate(
                row["home_team"], row["away_team"],
                row["odds_home"], row.get("odds_draw"), row["odds_away"],
                history, row.get("league"), "home"
            )
            scored.append({
                "home": row["home_team"],
                "away": row["away_team"],
                "league": row.get("league", ""),
                "odds": float(row["odds_home"]),
                "pure_score": eval_["pure_odds_score"],
                "fund_score": eval_["fundamentals_score"],
                "combined": eval_["combined"],
                "ev": eval_["ev"],
                "verdict": eval_["verdict"],
            })

        # 按 combined 排序
        scored.sort(key=lambda x: x["combined"], reverse=True)

        # 选最强的 2 场做 2 串 1
        top2 = scored[:2]
        if len(top2) >= 2:
            combined_odds = top2[0]["odds"] * top2[1]["odds"]
            p_both = top2[0]["combined"] * top2[1]["combined"]
            ev = p_both * combined_odds - 1
            recommendation = {
                "match1": top2[0],
                "match2": top2[1],
                "combined_odds": round(combined_odds, 3),
                "p_both": round(p_both, 4),
                "ev": round(ev, 4),
            }
        else:
            recommendation = None

        result = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "ok",
            "total_candidates": len(scored),
            "top_picks": scored[:5],
            "recommendation": recommendation,
            "disclaimer": "⚠️ 演示模式：当前用历史比赛模拟。真实接入中国体彩数据后，会显示真正的今日推荐。",
        }

    # 保存
    out_path = DAILY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 同步到 docs/data
    docs_data = Path(__file__).resolve().parent.parent / "docs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    with open(docs_data / "daily.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[OK] 今日推荐已生成：{out_path}")


if __name__ == "__main__":
    generate_daily_recommendation()
