# YouTube Cookies 配置说明

## 为什么需要 Cookies？

YouTube 现在要求验证以防止机器人，所以需要提供登录后的 cookies。

## 如何获取 Cookies？

### 方法 1：使用浏览器插件（推荐）

1. 在 Chrome/Firefox 安装插件 "Get cookies.txt LOCALLY"
   - Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

2. 登录 YouTube (https://www.youtube.com)

3. 点击插件图标，选择 "Export" 导出 cookies

4. 保存为 `cookies.txt`

### 方法 2：使用 yt-dlp 命令

在本地电脑（已登录 YouTube 的浏览器）运行：

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

这会生成 `cookies.txt` 文件。

## 部署到服务器

1. 将 `cookies.txt` 文件上传到项目根目录（与 `run.py` 同级）

2. 确保文件权限正确：
```bash
chmod 600 cookies.txt
```

3. 重启服务

## 注意事项

- cookies 文件包含敏感信息，不要提交到 git
- cookies 会过期，如果下载失败可能需要重新获取
- 建议定期更新 cookies（每 1-2 个月）
