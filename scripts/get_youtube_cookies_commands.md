# 服务器端 YouTube Cookies 配置命令

## 快速命令列表

### 1. 安装依赖

#### 安装 yt-dlp
```bash
pip install yt-dlp
```

#### 安装 Node.js（必需，用于解决 YouTube 的 n-challenge）
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# CentOS/RHEL
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo yum install -y nodejs

# 验证安装
node --version
npm --version
```

### 2. 上传 cookies.txt 到服务器
在本地电脑执行（替换服务器信息）：
```bash
scp cookies.txt user@your-server:/path/to/project/
```

### 3. 在服务器上设置权限
```bash
cd /path/to/project
chmod 600 cookies.txt
```

### 4. 测试 cookies 是否有效
```bash
yt-dlp --cookies cookies.txt --skip-download --print title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 5. 测试完整下载流程
```bash
yt-dlp --cookies cookies.txt \
  --extract-audio \
  --audio-format mp3 \
  --audio-quality 192K \
  --output "test.%(ext)s" \
  "https://www.youtube.com/watch?v=GUxIotkN2zg"
```

### 6. 清理测试文件
```bash
rm test.mp3
```

---

## 一键执行脚本

给脚本添加执行权限：
```bash
chmod +x scripts/setup_youtube_cookies.sh
```

运行配置脚本：
```bash
./scripts/setup_youtube_cookies.sh
```

---

## 如何在本地获取 cookies.txt

### 方法 1: 使用浏览器插件（最简单）

1. 安装插件：
   - **Chrome**: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/)

2. 在浏览器登录 YouTube

3. 点击插件图标 → Export → 保存为 `cookies.txt`

### 方法 2: 使用 yt-dlp 命令（需要本地有浏览器）

在本地电脑执行：
```bash
# Chrome
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Firefox
yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Safari (macOS)
yt-dlp --cookies-from-browser safari --cookies cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## 故障排查

### 下载失败 - n challenge solving failed

这是 YouTube 的反机器人机制，需要 Node.js：

```bash
# 检查 Node.js 是否安装
node --version

# 如果未安装，安装 Node.js
# Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# CentOS/RHEL:
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo yum install -y nodejs

# 验证
node --version
```

### Cookies 无效或过期
```bash
# 重新从浏览器获取 cookies
# 确保浏览器已登录 YouTube
# 重新上传到服务器
```

### 下载失败
```bash
# 检查 ffmpeg 是否安装
ffmpeg -version

# Ubuntu/Debian 安装 ffmpeg
sudo apt update && sudo apt install -y ffmpeg

# CentOS/RHEL 安装 ffmpeg
sudo yum install -y epel-release
sudo yum install -y ffmpeg

# macOS 安装 ffmpeg
brew install ffmpeg
```

### 权限问题
```bash
# 确保 cookies.txt 权限正确
ls -la cookies.txt
# 应该显示: -rw------- (600)

# 如果不对，重新设置
chmod 600 cookies.txt
```

---

## 服务器完整部署流程

```bash
# 1. 进入项目目录
cd /path/to/project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Node.js（必需，用于 YouTube n-challenge）
# Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证 Node.js
node --version

# 4. 安装 ffmpeg（如果未安装）
# Ubuntu/Debian:
sudo apt install -y ffmpeg

# 5. 上传 cookies.txt（在本地执行）
# scp cookies.txt user@server:/path/to/project/

# 6. 设置权限
chmod 600 cookies.txt

# 6. 测试
yt-dlp --cookies cookies.txt --skip-download --print title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 7. 重启服务
# 如果使用 systemd:
sudo systemctl restart perapera

# 如果使用 supervisor:
sudo supervisorctl restart perapera

# 如果手动运行:
# 先停止旧进程，然后
python run.py
```

---

## API 测试

服务启动后测试端点：

```bash
# 使用默认视频
curl "http://localhost:8000/api/v1/common/yt_audio" -o test.mp3

# 指定视频 URL
curl "http://localhost:8000/api/v1/common/yt_audio?url=https://www.youtube.com/watch?v=GUxIotkN2zg" -o audio.mp3
```

---

## 注意事项

1. **安全性**: cookies.txt 包含登录凭证，不要泄露或提交到 git
2. **有效期**: Cookies 会过期，建议每 1-2 个月更新一次
3. **备份**: 建议保存一份 cookies.txt 备份
4. **监控**: 如果下载频繁失败，可能需要更新 cookies
