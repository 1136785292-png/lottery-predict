"""
双轨评分模型
- 纯赔率评分：基于历史同赔率区间的真实胜率
- 基本面评分：基于球队近期状态、主客场、联赛性质
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


# ============================================================
# 1. 纯赔率评分
# ============================================================
def pure_odds_score(odds: float, history_df: pd.DataFrame) -> float:
    """
    给定赔率，从历史数据中找同赔率区间的比赛，统计实际胜率
    返回 0-1 之间的胜率估计
    """
    if odds is None or odds <= 1.0:
        return 0.0

    # 在历史数据中找同赔率区间的比赛
    # 用 ±0.05 的窗口
    lower = odds - 0.05
    upper = odds + 0.05

    # 找主胜赔率在区间的比赛
    matches = history_df[
        (history_df["odds_home"] >= lower) &
        (history_df["odds_home"] <= upper)
    ]

    if len(matches) < 20:
        # 样本太少，扩大窗口
        lower = odds - 0.10
        upper = odds + 0.10
        matches = history_df[
            (history_df["odds_home"] >= lower) &
            (history_df["odds_home"] <= upper)
        ]

    if len(matches) < 10:
        # 还是太少，回归到市场反推概率
        return 1.0 / odds

    # 主胜率
    win_rate = (matches["result"] == "H").mean()
    return float(win_rate)


# ============================================================
# 2. 基本面评分（简化版）
# ============================================================
def fundamentals_score(home_team: str, away_team: str, history_df: pd.DataFrame,
                       home_odds: float, league: str = None) -> Tuple[float, Dict]:
    """
    基于近期战绩、主客场优势的评分
    返回 (胜率, 解释 dict)
    """
    if history_df.empty:
        return 1.0 / home_odds if home_odds > 0 else 0.5, {}

    # 找两队历史交锋
    h2h = history_df[
        ((history_df["home_team"] == home_team) & (history_df["away_team"] == away_team)) |
        ((history_df["home_team"] == away_team) & (history_df["away_team"] == home_team))
    ]

    # 找主队最近 10 场主场比赛
    home_recent = history_df[
        history_df["home_team"] == home_team
    ].sort_values("date", ascending=False).head(10)

    # 找客队最近 10 场客场比赛
    away_recent = history_df[
        history_df["away_team"] == away_team
    ].sort_values("date", ascending=False).head(10)

    explanation = {}

    # 1. 主队主场胜率
    if len(home_recent) >= 5:
        home_home_winrate = (home_recent["result"] == "H").mean()
    else:
        home_home_winrate = 0.5
    explanation["主队主场胜率(近10场)"] = f"{home_home_winrate:.1%}"

    # 2. 客队客场胜率（这里算客队"胜"的比例，含平局不变）
    if len(away_recent) >= 5:
        away_away_winrate = (away_recent["result"] == "A").mean()
    else:
        away_away_winrate = 0.3
    explanation["客队客场胜率(近10场)"] = f"{away_away_winrate:.1%}"

    # 3. 联赛类型调整
    league_strength = {
        "E0": 1.0,   # 英超 - 主客场差异大
        "SP1": 1.0,  # 西甲
        "D1": 1.0,   # 德甲
        "I1": 0.95,  # 意甲 - 平局多
        "F1": 0.95,  # 法甲
    }
    league_factor = league_strength.get(league, 1.0)

    # 综合评分
    # 基础：主队主场胜率
    # 加成：客队客场胜率低（说明主队优势大）
    base = home_home_winrate * 0.65
    advantage = (1.0 - away_away_winrate) * 0.20
    h2h_factor = 0.0
    if len(h2h) >= 3:
        # 历史交锋中主队作为主队时的胜率
        home_h2h = h2h[h2h["home_team"] == home_team]
        if len(home_h2h) >= 2:
            h2h_factor = (home_h2h["result"] == "H").mean() * 0.15

    raw = (base + advantage + h2h_factor) * league_factor

    # 限制在合理范围
    final = max(0.4, min(0.95, raw))

    return float(final), explanation


# ============================================================
# 3. 双轨合并
# ============================================================
def dual_track_evaluate(home_team: str, away_team: str, home_odds: float,
                       draw_odds: float = None, away_odds: float = None,
                       history_df: pd.DataFrame = None,
                       league: str = None,
                       bet_on: str = "home") -> Dict:
    """
    双轨评分主函数
    bet_on: "home" / "draw" / "away"
    返回字典包含两个评分、合并评分、推荐理由
    """
    if history_df is None or history_df.empty:
        # 退化为纯赔率反推
        if bet_on == "home":
            return {
                "pure_odds_score": 1.0 / home_odds,
                "fundamentals_score": 1.0 / home_odds,
                "combined": 1.0 / home_odds,
                "ev": (1.0 / home_odds) * home_odds - 1,
                "explanation": {"说明": "无历史数据，使用赔率反推"},
                "verdict": "skip" if 1.0 / home_odds < 0.7 else "neutral"
            }

    # 选择赔率
    if bet_on == "home":
        odds = home_odds
    elif bet_on == "draw":
        odds = draw_odds
    else:
        odds = away_odds

    # 纯赔率评分
    p_score = pure_odds_score(odds, history_df)

    # 基本面评分
    f_score, f_explanation = fundamentals_score(
        home_team, away_team, history_df, odds, league
    )

    # 合并（70% 纯赔率 + 30% 基本面）
    # 理由：低赔率区间市场定价效率高，基本面能提分但不应反客为主
    combined = p_score * 0.70 + f_score * 0.30

    # EV 计算
    ev = combined * odds - 1.0

    # 推荐判定
    if combined >= 0.80 and ev > 0.02:
        verdict = "strong_pick"
    elif combined >= 0.72 and ev > 0.0:
        verdict = "pick"
    elif combined >= 0.65:
        verdict = "neutral"
    else:
        verdict = "skip"

    return {
        "pure_odds_score": round(p_score, 4),
        "fundamentals_score": round(f_score, 4),
        "combined": round(combined, 4),
        "ev": round(ev, 4),
        "explanation": f_explanation,
        "verdict": verdict,
        "bet_on": bet_on,
        "odds": odds,
    }


# ============================================================
# 4. 找同赔率区间的"稳"比赛
# ============================================================
def find_safe_matches(history_df: pd.DataFrame, target_date=None,
                     max_odds: float = 1.4, min_odds: float = 1.05,
                     league_filter: List[str] = None) -> pd.DataFrame:
    """
    从历史数据中找出赔率 ≤ 1.4 的"低赔率稳胆"比赛
    用于回测
    """
    df = history_df.copy()

    if league_filter:
        df = df[df["league"].isin(league_filter)]

    df = df[(df["odds_home"] >= min_odds) & (df["odds_home"] <= max_odds)]
    df = df.dropna(subset=["odds_home", "result"])

    return df
