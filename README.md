# 井冈山红色文化小程序原型

这是一个面向井冈山红色文化宣传、研学旅行与青年创作场景的小程序交互原型。项目目前采用单页 HTML 原型配合可选的 Python API 服务，支持离线浏览，也预留了联网智能体与 OpenAI 图片生成能力。

## 主要功能

- 首页：红色 IP、短视频、研学路线入口
- 发现：井冈山主题人物词云与知识内容检索
- 井冈山智能体：本地知识库问答、可选联网搜索和路线建议
- 红色 IP：官方表情包下载、漫画互动、个性化红军面相表情包定制
- 研学路线：井冈山地图、路线规划与基于位置的答题积分方案
- 我的：个人资料、积分、推荐、缓存管理和设置

## 快速预览

直接打开以下任一文件即可查看前端原型：

- `outputs/index.html`：开发版本
- `outputs/jinggangshan-miniapp-prototype.html`：资源内嵌的独立版本

也可以解压 `outputs/jinggangshan-miniapp-prototype.zip` 后查看。

## 启动智能体服务

1. 复制 `outputs/.env.local.example` 为 `outputs/.env.local`。
2. 在本地环境文件中填写所需的 OpenAI API Key，不要把真实 Key 提交到仓库。
3. 在 PowerShell 中运行：

```powershell
.\outputs\START-JGS-MINIAPP.ps1
```

启动后通过脚本输出的本地网址访问页面。服务端实现位于：

- `outputs/jinggangshan-agent-api-example.py`
- `outputs/jinggangshan-agent-api-example.mjs`

关于图片生成服务的配置细节见 `outputs/AI-STICKER-SETUP.md`。

## 目录结构

```text
outputs/
  assets/                         图片、表情包与知识库
  proposals/                      暂未合入主程序的交互方案
  index.html                      主开发页面
  jinggangshan-miniapp-prototype.html
  jinggangshan-agent-api-example.py
tools/                            构建与素材切分脚本
work/                             自动化检查脚本
```

## 构建与检查

重新生成独立版和压缩包：

```powershell
.\tools\build-export.ps1
```

项目的浏览器自动化检查脚本位于 `work/*.cjs`。这些脚本需要 Node.js、Playwright 和本机 Chrome。

## 隐私说明

仓库忽略用户上传的人脸照片、个性化表情生成结果、缓存和本地密钥。正式上线个性化人像功能前，还需要接入用户授权、未成年人监护同意、内容安全审核、违规申诉与数据删除机制。
