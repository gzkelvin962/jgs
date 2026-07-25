# 个性化红军表情服务部署

网页不会保存或要求普通用户填写 OpenAI 密钥或 API 地址。管理员只需配置一次，之后用户访问统一网址即可。

## 本机演示

1. 安装 Python 3.10 或更高版本。
2. 把 `.env.local.example` 复制为 `.env.local`，由管理员填写：

```text
OPENAI_API_KEY=管理员的 OpenAI API Key
```

3. 运行 `START-JGS-MINIAPP.ps1`，然后打开：

```text
http://127.0.0.1:8787/
```

页面会自动检查服务和密钥状态。服务未连接时不会显示预生成图片冒充本次结果，也不会要求普通用户选择备用模板。

## 正式部署

把 `jinggangshan-agent-api-example.py`、`index.html` 和 `assets` 目录部署到同一服务。Python 服务已经同时提供网页和以下 API：

```text
/api/jinggangshan-sticker/customize
/api/jinggangshan-agent
/api/jinggangshan-user
```

网页会自动使用当前域名，不需要修改用户浏览器。生产环境应启用 HTTPS、访问频率限制、服务端日志脱敏和管理员审核记录。

## 审核与隐私

- 上传前要求本人或授权确认；未成年人须取得监护人同意。
- 后端先调用图像安全审核，再调用图片编辑模型。
- 后端默认不把原始人像或生成结果写入磁盘。
- API Key 只能保存在服务器环境变量中，不能写入 HTML 或前端 JavaScript。
- `.env.local` 不会被打进导出压缩包，也不应提交到代码仓库。
