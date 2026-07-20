# ============================================
# 稳胆 2 串 1 · 一键部署脚本
# ============================================
# 用法：先注册 GitHub 账号 + 拿到用户名
#      然后右键 PowerShell "以管理员身份运行" 跑这个脚本
# ============================================

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUsername,

    [string]$RepoName = "lottery-predict"
)

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  稳胆 2 串 1 · 一键部署到 GitHub + Pages" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 步骤 1：检查环境
Write-Host "[1/6] 检查环境..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "  ✓ Git: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Git 未安装" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装 Git：" -ForegroundColor Yellow
    Write-Host "  1. 打开 https://git-scm.com/download/win" -ForegroundColor White
    Write-Host "  2. 下载 64-bit Git for Windows Setup" -ForegroundColor White
    Write-Host "  3. 一路 Next 安装（保持默认选项）" -ForegroundColor White
    Write-Host "  4. 安装完关掉 PowerShell，重新打开再跑这个脚本" -ForegroundColor White
    Write-Host ""
    exit 1
}

# 步骤 2：配置 git 用户信息
Write-Host ""
Write-Host "[2/6] 配置 Git 用户信息..." -ForegroundColor Yellow
$defaultEmail = "$GitHubUsername@users.noreply.github.com"
git config --global user.name "$GitHubUsername" 2>&1 | Out-Null
git config --global user.email "$defaultEmail" 2>&1 | Out-Null
Write-Host "  ✓ user.name: $GitHubUsername" -ForegroundColor Green
Write-Host "  ✓ user.email: $defaultEmail" -ForegroundColor Green

# 步骤 3：进入项目目录 + 初始化
Write-Host ""
Write-Host "[3/6] 初始化项目..." -ForegroundColor Yellow
Set-Location $projectDir

if (Test-Path ".git") {
    Write-Host "  ! .git 目录已存在，跳过 init" -ForegroundColor Yellow
} else {
    git init | Out-Null
    Write-Host "  ✓ git init" -ForegroundColor Green
}

# 步骤 4：添加 + 提交
Write-Host ""
Write-Host "[4/6] 添加 + 提交代码..." -ForegroundColor Yellow
git add . | Out-Null
$status = git status --short
if ($status) {
    git commit -m "init: 稳胆 2 串 1 回测系统 v0.1" 2>&1 | Out-Null
    Write-Host "  ✓ git commit" -ForegroundColor Green
} else {
    Write-Host "  ! 没有新文件需要提交（可能已经提交过）" -ForegroundColor Yellow
}

# 步骤 5：设置 remote
Write-Host ""
Write-Host "[5/6] 设置 GitHub 远程仓库..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/$GitHubUsername/$RepoName.git"
$existingRemote = git remote get-url origin 2>&1
if ($existingRemote -and $existingRemote -notmatch "error") {
    Write-Host "  ! remote origin 已存在：$existingRemote" -ForegroundColor Yellow
    $confirm = Read-Host "    是否覆盖? (y/n)"
    if ($confirm -eq "y") {
        git remote set-url origin $remoteUrl | Out-Null
        Write-Host "  ✓ 已更新为: $remoteUrl" -ForegroundColor Green
    }
} else {
    git remote add origin $remoteUrl 2>&1 | Out-Null
    Write-Host "  ✓ remote: $remoteUrl" -ForegroundColor Green
}

git branch -M main | Out-Null
Write-Host "  ✓ branch: main" -ForegroundColor Green

# 步骤 6：推送
Write-Host ""
Write-Host "[6/6] 推送到 GitHub..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ⚠️  接下来会要求你输入 GitHub 凭据：" -ForegroundColor Magenta
Write-Host "      Username: $GitHubUsername" -ForegroundColor White
Write-Host "      Password: 用 Personal Access Token（不是 GitHub 密码）" -ForegroundColor White
Write-Host ""
Write-Host "      没有 Token? 现在去生成一个（1 分钟）：" -ForegroundColor Yellow
Write-Host "      https://github.com/settings/tokens/new" -ForegroundColor Cyan
Write-Host "      - Note: lottery-predict-deploy" -ForegroundColor White
Write-Host "      - Expiration: 90 days" -ForegroundColor White
Write-Host "      - Scopes: 勾选 'repo'（自动会勾 'workflow' 和 'write:packages'）" -ForegroundColor White
Write-Host "      - 点 Generate token → 复制 token（ghp_xxxxx 开头）" -ForegroundColor White
Write-Host "      - ⚠️ token 只显示一次，复制后保存" -ForegroundColor Red
Write-Host ""
Write-Host "      准备好后按 Enter 继续..." -ForegroundColor Yellow
Read-Host

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ✓ 推送成功！" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "接下来 3 步手动操作（GitHub 网页）：" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  步骤 A：开启 GitHub Pages" -ForegroundColor Yellow
    Write-Host "    打开 https://github.com/$GitHubUsername/$RepoName/settings/pages" -ForegroundColor White
    Write-Host "    Source 选 'GitHub Actions'" -ForegroundColor White
    Write-Host "    点 Save" -ForegroundColor White
    Write-Host ""
    Write-Host "  步骤 B：触发第一次回测" -ForegroundColor Yellow
    Write-Host "    打开 https://github.com/$GitHubUsername/$RepoName/actions" -ForegroundColor White
    Write-Host "    左侧选 '每周回测' → 右侧 'Run workflow' → 绿色按钮" -ForegroundColor White
    Write-Host "    等 5-10 分钟跑完" -ForegroundColor White
    Write-Host ""
    Write-Host "  步骤 C：访问看板" -ForegroundColor Yellow
    Write-Host "    打开 https://$GitHubUsername.github.io/$RepoName/" -ForegroundColor White
    Write-Host ""
    Write-Host "完成后回来告诉我跑出来的数字！" -ForegroundColor Magenta
} else {
    Write-Host ""
    Write-Host "  ✗ 推送失败" -ForegroundColor Red
    Write-Host "  常见原因：" -ForegroundColor Yellow
    Write-Host "    1. 仓库还没建 → https://github.com/new" -ForegroundColor White
    Write-Host "    2. Token 错/过期 → 重新生成" -ForegroundColor White
    Write-Host "    3. 网络问题 → 重试" -ForegroundColor White
    Write-Host ""
    Write-Host "  把报错贴给我，我帮你看" -ForegroundColor Cyan
}
