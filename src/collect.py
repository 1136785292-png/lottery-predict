"""
数据采集模块
- 足球：从 football-data.co.uk 下载公开 CSV（欧洲 5 大联赛 + 部分次级联赛，20+ 年历史赔率 + 结果）
- 篮球：MVP 阶段先用占位逻辑，后续接入 balldontlie / nba_api
"""
import os
import io
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# 路径配置
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# football-data.co.uk 公开数据集（每联赛每个赛季一个 CSV）
# 注：B365 = Bet365, BbAv = 平均赔率, 这些是国际博彩公司
# 中国体彩赔率会略有不同（抽水略高），但赔率分布规律一致
FOOTBALL_LEAGUES = {
    "E0": "Premier League (英超)",
    "E1": "Championship (英冠)",
    "SP1": "La Liga (西甲)",
    "D1": "Bundesliga (德甲)",
    "I1": "Serie A (意甲)",
    "F1": "Ligue 1 (法甲)",
}

BASE_URL = "https://www.football-data.co.uk/mmz4281"


def download_league_csv(league_code: str, season: str) -> pd.DataFrame | None:
    """
    下载某个联赛某个赛季的 CSV
    season 格式: "2425" 代表 2024-2025 赛季
    """
    url = f"{BASE_URL}/{season}/{league_code}.csv"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df["League"] = league_code
        return df
    except Exception as e:
        print(f"[WARN] 下载 {league_code} {season} 失败: {e}")
        return None


def collect_football_history(start_season: str = "2122", end_season: str = "2425") -> pd.DataFrame:
    """
    批量下载历史数据
    season 格式: "2122" = 2021-22 赛季开始
    """
    print(f"[INFO] 开始采集足球历史数据：{start_season} - {end_season}")
    all_dfs = []

    # 把 "2122" 解析成 ["2122", "2223", "2324", "2425"]
    start_year = int(start_season[:2])
    end_year = int(end_season[:2])
    seasons = [f"{y:02d}{(y+1)%100:02d}" for y in range(start_year, end_year + 1)]

    for league_code in FOOTBALL_LEAGUES.keys():
        for season in seasons:
            df = download_league_csv(league_code, season)
            if df is not None:
                all_dfs.append(df)
                print(f"[OK] {league_code} {season}：{len(df)} 场")

    if not all_dfs:
        print("[ERROR] 没有任何数据被下载")
        return pd.DataFrame()

    full_df = pd.concat(all_dfs, ignore_index=True)
    print(f"[OK] 总计 {len(full_df)} 场比赛")

    # 标准化列名
    full_df = normalize_football_columns(full_df)
    return full_df


def normalize_football_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    把 football-data.co.uk 的原始列标准化
    关键列：Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, B365H, B365D, B365A
    """
    column_map = {
        "Date": "date",
        "HomeTeam": "home_team",
        "AwayTeam": "away_team",
        "FTHG": "home_goals",
        "FTAG": "away_goals",
        "FTR": "result",  # H=主胜, D=平, A=客胜
        "B365H": "odds_home",
        "B365D": "odds_draw",
        "B365A": "odds_away",
        "BbAvH": "avg_odds_home",
        "BbAvD": "avg_odds_draw",
        "BbAvA": "avg_odds_away",
        "League": "league",
    }

    # 只保留存在的列
    existing = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=existing)

    # 必要列
    needed = ["date", "home_team", "away_team", "home_goals", "away_goals", "result", "league"]
    for col in needed:
        if col not in df.columns:
            df[col] = None

    # 赔率列：取 Bet365，如果缺失用平均赔率
    for side in ["home", "draw", "away"]:
        odds_col = f"odds_{side}"
        if odds_col not in df.columns:
            avg_col = f"avg_odds_{side}"
            if avg_col in df.columns:
                df[odds_col] = df[avg_col]
            else:
                df[odds_col] = None

    # 日期解析（多种格式兼容）
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    # 过滤无效数据
    df = df.dropna(subset=["date", "home_team", "away_team", "result"])

    # 计算总进球
    df["total_goals"] = df["home_goals"] + df["away_goals"]

    return df


def save_data(df: pd.DataFrame, name: str):
    """保存到 data/processed/"""
    path = PROCESSED_DIR / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"[OK] 保存到 {path}（{len(df)} 行）")


def load_processed(name: str) -> pd.DataFrame:
    """从 data/processed/ 读取"""
    path = PROCESSED_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["date"])


if __name__ == "__main__":
    df = collect_football_history(start_season="2122", end_season="2425")
    if not df.empty:
        save_data(df, "football_history")
        print(f"\n[STAT] 数据概览：")
        print(f"  时间范围：{df['date'].min()} 至 {df['date'].max()}")
        print(f"  联赛：{df['league'].nunique()} 个")
        print(f"  比赛：{len(df)} 场")
        print(f"  字段：{list(df.columns)}")
