"""
回测引擎
- 模拟每天从历史数据中选 2 场赔率 ≤ 1.4 的比赛做 2 串 1
- 比较 3 种策略：随机选 / 纯赔率筛选 / 双轨模型筛选
- 输出胜率、收益、最大回撤
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from model import dual_track_evaluate, find_safe_matches
from collect import load_processed

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "backtest"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 单场胜率预测（用于 2 串 1 联合概率）
# ============================================================
def predict_match_outcome(row, history_df: pd.DataFrame) -> Dict:
    """
    对一场比赛，主胜/平/客胜各自评分
    返回每个结果的 (概率, 赔率)
    """
    home_odds = row["odds_home"]
    draw_odds = row.get("odds_draw")
    away_odds = row["odds_away"]
    league = row.get("league")

    # 主胜评分
    home_eval = dual_track_evaluate(
        row["home_team"], row["away_team"],
        home_odds, draw_odds, away_odds,
        history_df, league, "home"
    )
    # 客胜评分
    away_eval = dual_track_evaluate(
        row["home_team"], row["away_team"],
        home_odds, draw_odds, away_odds,
        history_df, league, "away"
    )

    # 归一化（保证三个概率和 = 1）
    p_home = home_eval["combined"]
    p_away = away_eval["combined"]
    p_draw = max(0.05, 1.0 - p_home - p_away) if draw_odds else 0.0

    total = p_home + p_draw + p_away
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    return {
        "p_home": p_home,
        "p_draw": p_draw,
        "p_away": p_away,
        "home_eval": home_eval,
        "away_eval": away_eval,
    }


# ============================================================
# 2 串 1 组合评分
# ============================================================
def evaluate_2in1(match1, match2, history_df, strategy="dual_track") -> Dict:
    """
    对两场比赛的 2 串 1 组合评分
    关注"主胜"+"主胜"组合（最常见）

    strategy:
      - "random": 随机，不看评分
      - "odds_only": 只看赔率（赔率最低的优先）
      - "dual_track": 双轨评分最高的优先
    """
    pred1 = predict_match_outcome(match1, history_df)
    pred2 = predict_match_outcome(match2, history_df)

    # 假设：两场都买"主胜"
    p_both_home = pred1["p_home"] * pred2["p_home"]
    combined_odds = match1["odds_home"] * match2["odds_home"]
    ev = p_both_home * combined_odds - 1.0

    return {
        "match1": {
            "home": match1["home_team"],
            "away": match1["away_team"],
            "odds": match1["odds_home"],
            "p_home": pred1["p_home"],
            "score": pred1["home_eval"]["combined"],
        },
        "match2": {
            "home": match2["home_team"],
            "away": match2["away_team"],
            "odds": match2["odds_home"],
            "p_home": pred2["p_home"],
            "score": pred2["home_eval"]["combined"],
        },
        "p_both_home": p_both_home,
        "combined_odds": combined_odds,
        "ev": ev,
    }


# ============================================================
# 主回测
# ============================================================
def run_backtest(history_df: pd.DataFrame, strategy: str = "dual_track",
                 bet_per_period: float = 100.0,
                 max_periods: int = 500) -> Dict:
    """
    跑回测

    每天：
      1. 找当天的所有比赛
      2. 过滤出"赔率 ≤ 1.4"的主胜比赛
      3. 根据 strategy 选 2 场
      4. 模拟下注 + 结算
    """
    print(f"\n[BACKTEST] 策略：{strategy}，每期：¥{bet_per_period}，最多 {max_periods} 期")

    df = history_df.copy().sort_values("date").reset_index(drop=True)

    # 按日期分组
    daily_groups = df.groupby(df["date"].dt.date)

    results = []
    bankroll = 0.0
    peak = 0.0
    max_drawdown = 0.0
    periods_run = 0

    for date, day_df in daily_groups:
        if periods_run >= max_periods:
            break

        # 找当天"赔率 ≤ 1.4"的主胜比赛
        candidates = find_safe_matches(day_df, max_odds=1.4, min_odds=1.05)

        if len(candidates) < 2:
            continue  # 当天比赛不够 2 场，跳过

        # 选 2 场
        if strategy == "random":
            selected = candidates.sample(n=min(2, len(candidates)), random_state=42)
        elif strategy == "odds_only":
            selected = candidates.nsmallest(2, "odds_home")
        elif strategy == "dual_track":
            # 用模型对每场打分，选分最高的 2 场
            scores = []
            for _, row in candidates.iterrows():
                # 用历史数据（截止到当前日期）评分
                past_df = df[df["date"] < date]
                if past_df.empty:
                    continue
                eval_ = dual_track_evaluate(
                    row["home_team"], row["away_team"],
                    row["odds_home"], row.get("odds_draw"), row["odds_away"],
                    past_df, row.get("league"), "home"
                )
                scores.append((eval_["combined"], eval_["ev"], row))
            scores.sort(key=lambda x: x[0], reverse=True)
            selected = pd.DataFrame([s[2] for s in scores[:2]])
        else:
            selected = candidates.head(2)

        if len(selected) < 2:
            continue

        # 模拟下注
        m1, m2 = selected.iloc[0], selected.iloc[1]
        combined_odds = m1["odds_home"] * m2["odds_home"]

        # 判定是否两场都主胜
        m1_win = m1["result"] == "H"
        m2_win = m2["result"] == "H"
        both_win = m1_win and m2_win

        pnl = (combined_odds - 1) * bet_per_period if both_win else -bet_per_period
        bankroll += pnl
        peak = max(peak, bankroll)
        drawdown = peak - bankroll
        max_drawdown = max(max_drawdown, drawdown)

        results.append({
            "date": str(date),
            "m1": f"{m1['home_team']} vs {m1['away_team']}",
            "m1_odds": m1["odds_home"],
            "m1_win": m1_win,
            "m2": f"{m2['home_team']} vs {m2['away_team']}",
            "m2_odds": m2["odds_home"],
            "m2_win": m2_win,
            "combined_odds": round(combined_odds, 3),
            "both_win": both_win,
            "pnl": round(pnl, 2),
            "bankroll": round(bankroll, 2),
        })

        periods_run += 1

    # 统计
    if not results:
        return {"error": "无有效回测数据"}

    results_df = pd.DataFrame(results)
    total_periods = len(results_df)
    win_count = results_df["both_win"].sum()
    win_rate = win_count / total_periods
    total_pnl = results_df["pnl"].sum()
    roi = total_pnl / (bet_per_period * total_periods) * 100

    summary = {
        "strategy": strategy,
        "total_periods": total_periods,
        "win_count": int(win_count),
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "roi_pct": round(roi, 2),
        "max_drawdown": round(max_drawdown, 2),
        "bet_per_period": bet_per_period,
        "start_date": str(results_df["date"].min()),
        "end_date": str(results_df["date"].max()),
    }

    print(f"\n[SUMMARY] {strategy}")
    print(f"  期数：{total_periods}")
    print(f"  命中：{win_count}（{win_rate:.1%}）")
    print(f"  净收益：¥{total_pnl:.2f}")
    print(f"  ROI：{roi:+.2f}%")
    print(f"  最大回撤：¥{max_drawdown:.2f}")

    return {
        "summary": summary,
        "history": results_df.to_dict(orient="records"),
    }


# ============================================================
# 多策略对比
# ============================================================
def compare_strategies(history_df: pd.DataFrame, max_periods: int = 500) -> Dict:
    """3 策略对比"""
    strategies = ["random", "odds_only", "dual_track"]
    comparison = {}

    for s in strategies:
        result = run_backtest(history_df, strategy=s, max_periods=max_periods)
        if "summary" in result:
            comparison[s] = result["summary"]
            # 保存历史
            hist_df = pd.DataFrame(result["history"])
            hist_df.to_csv(OUTPUT_DIR / f"history_{s}.csv", index=False)

    # 保存对比结果
    with open(OUTPUT_DIR / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    return comparison


if __name__ == "__main__":
    print("[LOAD] 读取历史数据...")
    history = load_processed("football_history")

    if history.empty:
        print("[ERROR] 没有历史数据，请先跑 collect.py")
    else:
        print(f"[OK] {len(history)} 场比赛")
        comparison = compare_strategies(history, max_periods=500)
        print(f"\n[FINAL] 对比结果：")
        for s, summary in comparison.items():
            print(f"  {s}: 胜率 {summary['win_rate']:.1%}，ROI {summary['roi_pct']:+.2f}%")
