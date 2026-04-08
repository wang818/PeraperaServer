# RapidAPI YouTube 下载配置指南

使用 RapidAPI 的 YouTube MP3 下载服务，稳定可靠，无需担心 IP 被封。

## 步骤 1: 注册 RapidAPI 账号

1. 访问 https://rapidapi.com
2. 点击 "Sign Up" 注册账号（可以用 Google/GitHub 登录）
3. 验证邮箱

## 步骤 2: 订阅 YouTube MP3 API

### 推荐 API 1: YouTube MP3 (ytjar)
1. 访问: https://rapidapi.com/ytjar/api/youtube-mp36
2. 点击 "Subscribe to Test"
3. 选择免费计划（通常有每月免费额度）
4. 点击 "Subscribe"

### 备用 API 2: YouTube MP3 Downloader
1. 访问: https://rapidapi.com/youtube-mp3-downloader2/api/youtube-mp3-downloader2
2. 同样订阅免费计划

## 步骤 3: 获取 API Key

1. 订阅后，在 API 页面找到 "X-RapidAPI-Key"
2. 复制这个 Key（类似: `1234567890abcdef1234567890abcdef`）

## 步骤 4: 配置环境变量

在服务器的 `.env` 文件中添加：

```env
RAPIDAPI_KEY=你的RapidAPI密钥
```

示例：
```env
RAPIDAPI_KEY=1234567890abcdef1234567890abcdef
```

## 步骤 5: 重启服务

```bash
# SSH 登录服务器后
cd /var/www/PeraperaServer
sudo systemctl restart perapera.service
```

## 步骤 6: 测试

```bash
curl -X 'GET' \
  'http://www.perapera.cc/api/v1/common/yt_audio?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DGUxIotkN2zg' \
  -H 'accept: application/json'
```

## 免费额度说明

大多数 RapidAPI 的 YouTube 下载服务提供：
- 免费层级: 100-500 次请求/月
- 基础付费: $5-10/月，1000-5000 次请求
- 专业版: $20-50/月，无限或更高额度

## 推荐的 API 服务

### 1. YouTube MP3 (ytjar)
- URL: https://rapidapi.com/ytjar/api/youtube-mp36
- 免费额度: 500 次/月
- 速度: 快
- 稳定性: 高

### 2. YouTube to MP3 Downloader
- URL: https://rapidapi.com/youtube-mp3-downloader2/api/youtube-mp3-downloader2
- 免费额度: 100 次/月
- 速度: 中等
- 稳定性: 高

### 3. YouTube MP3 Audio Video Downloader
- URL: https://rapidapi.com/nikzeferis/api/youtube-mp3-audio-video-downloader
- 免费额度: 100 次/月
- 速度: 快
- 稳定性: 高

## 监控使用量

1. 登录 RapidAPI
2. 进入 "My Apps"
3. 查看 "Analytics" 了解使用情况

## 故障排查

### 错误: "RAPIDAPI_KEY 未配置"
- 检查 `.env` 文件是否包含 `RAPIDAPI_KEY`
- 重启服务

### 错误: "所有下载方案都失败"
- 检查 API Key 是否正确
- 确认已订阅相应的 API
- 检查免费额度是否用完

### 错误: 401 Unauthorized
- API Key 错误或已过期
- 重新复制正确的 Key

### 错误: 429 Too Many Requests
- 超出免费额度
- 升级到付费计划或等待下月重置

## 成本估算

假设每天 100 次下载：
- 每月约 3000 次请求
- 免费额度不够，需要付费计划
- 预计成本: $10-20/月

## 优势

✅ 无需担心 IP 被封
✅ 稳定可靠
✅ 速度快
✅ 有免费额度
✅ 易于扩展

## 参考链接

- RapidAPI 官网: https://rapidapi.com
- RapidAPI 文档: https://docs.rapidapi.com
