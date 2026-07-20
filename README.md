# 稳胆 2 串 1 · 自动回测系统

> 赔率 ≤ 1.4 的 2 串 1 长期胜率验证 · 0 元部署 · 每周自动跑

## 这是什么

一个**完全自动跑**的体彩回测系统：
- 📊 **每周日北京时间 10:00** 自动跑 500 期回测
- 📈 自动生成对比报告（3 策略：随机 / 纯赔率 / 双轨模型）
- 🌐 自动部署到 GitHub Pages，你打开网页就能看
- 💰 **0 元**（GitHub Actions 免费层 2000 分钟/月，足够用）

## 工作原理

```
每周日 10:00 (北京时间)
  └─ GitHub Actions 自动触发
     ├─ 下载 football-data.co.uk 历史数据（5 大联赛 + 部分次级联赛，4 个赛季）
     ├─ 跑 3 策略回测
     ├─ 跑双轨评分模型
     ├─ 生成 JSON 报告
     └─ 部署到 GitHub Pages
```

## 你要做的（3 步，5 分钟）

### 第 1 步：建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名填：`lottery-predict`
3. 选 **Public**（必须是 Public 才能用 GitHub Pages 免费版）
4. **不要**勾选 "Add a README file" / "Add .gitignore" / "Choose a license"
5. 点 **Create repository**

### 第 2 步：把代码推上去

打开 PowerShell 或 Git Bash，复制粘贴下面所有命令：

```bash
# 切到项目目录
cd C:\Users\Gaoxxxx\.mavis\agents\mavis\workspace\lottery-predict

# 初始化 git
git init
git add .
git commit -m "init: 稳胆 2 串 1 回测系统 v0.1"

# 关联你的 GitHub 仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/lottery-predict.git
git branch -M main
git push -u origin main
```

> ⚠️ 第一次 push 会要求你登录 GitHub。如果弹出登录框，用你的 GitHub 账号登录即可。

### 第 3 步：开启 GitHub Pages

1. 打开你刚创建的仓库页面
2. 顶部菜单点 **Settings**
3. 左侧菜单点 **Pages**
4. **Source** 选 **GitHub Actions**
5. 保存

### 第 4 步（可选）：手动触发第一次回测

1. 仓库页面点 **Actions** 标签
2. 左侧选 **每周回测**
3. 右侧点 **Run workflow** → 绿色按钮
4. 等待 5-10 分钟跑完

跑完后访问：
```
https://YOUR_USERNAME.github.io/lottery-predict/
```

就能看到回测看板。

## 项目结构

```
lottery-predict/
├── .github/workflows/
│   ├── backtest.yml       # 每周日跑回测
│   └── daily.yml          # 每天跑每日推荐（开发中）
├── src/
│   ├── collect.py         # 数据采集
│   ├── model.py           # 双轨评分模型
│   ├── backtest.py        # 回测引擎
│   ├── daily.py           # 每日推荐（占位）
│   └── generate_report.py # 报告生成
├── docs/                  # GitHub Pages 静态站点
│   ├── index.html         # 看板主页
│   └── data/              # 自动生成的 JSON 报告
├── data/                  # 原始数据 + 回测结果
├── requirements.txt
└── README.md
```

## 后续开发计划

- [ ] 接中国体彩官方数据（爬虫）
- [ ] 接入 NBA 篮球数据
- [ ] 双轨模型调优
- [ ] 微信小程序订阅消息推送
- [ ] 资金管理（凯利公式）模块

## 风险提示

⚠️ 本项目**不保证盈利**。体彩长期稳定盈利极难，本系统的价值是：
- 把"凭感觉选"变成"有数据支撑"
- 把"长期必然亏"变成"可能微赚"
- 透明、可复盘

请理性下注，量力而行。

## 许可

个人项目，仅供学习和研究使用。
