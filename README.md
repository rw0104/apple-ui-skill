# Apple UI Skill

让 AI 为网页、App 和桌面软件设计清晰、一致、符合平台习惯的界面。

从页面布局、文字层级和配色，到导航、表单、动效与无障碍，Apple UI Skill
帮助你把产品需求转化为可落地的设计和实现。它结合 Apple 的设计方法与各平台
规范，适配你的产品风格和现有技术栈，适用于 Windows、macOS、Linux、Android、
iOS 和 Web 的界面设计任务。

## 能帮你做什么

- **设计新界面**：梳理信息架构、页面布局和主要操作，让内容与功能有清楚的层级。
- **改进已有产品**：检查视觉一致性、交互反馈、可读性与无障碍，给出具体修改建议。
- **适配不同设备**：为手机、平板和桌面窗口调整导航、密度、输入方式与响应式布局。
- **完善交互细节**：考虑加载、空状态、错误、重试、取消和恢复，让关键操作形成完整流程。
- **落地前端实现**：提供常用组件与 React/Vue 参考，沿用项目已有技术栈。
- **验证实际效果**：在可用的浏览器或应用环境中检查布局、键盘操作、焦点和状态变化。

## 一键安装

需要 **Python 3.10+**。以下命令默认安装到 Codex，安装完成后开启一个新会话即可使用。

Windows PowerShell：

```powershell
irm 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/install.ps1?v=2.0.0-dev.5-1' | iex
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/install.sh | bash
```

### Claude Code、Gemini CLI 或自定义安装

下载或克隆本仓库后运行：

```text
python installer.py --agent codex
python installer.py --agent claude
python installer.py --agent gemini
```

| 工具 | 默认安装位置 | 使用方式 |
| --- | --- | --- |
| Codex | `~/.agents/skills/apple-ui-skill` | `$apple-ui-skill` |
| Claude Code | `~/.claude/skills/apple-ui-skill` | `/apple-ui-skill` |
| Gemini CLI | `~/.gemini/skills/apple-ui-skill` | 按工具提示启用并调用技能 |

只想安装到某个项目，先进入项目目录，再指定安装器的实际路径：

```text
cd <你的项目目录>
python <下载仓库路径>/installer.py --agent codex --scope project
```

也可以用 `--destination <目标目录>` 指定安装位置。已有同名安装时，使用下面的更新命令。

## 这样提需求

描述产品用途、目标平台、技术栈和关键操作，Skill 就能围绕实际任务展开设计。

**优化电脑客户端**

```text
使用 apple-ui-skill，改进这个 Windows 工单客户端。
重点检查列表与详情布局、键盘操作、保存反馈和窄窗口适配。
保留现有功能和品牌色，给出可直接实施的优化建议。
```

**设计一个新页面**

```text
使用 apple-ui-skill，设计一个读书笔记网站。
用户需要整理书籍、查找笔记和继续阅读。
沿用 React，兼顾手机和桌面，风格简洁、阅读舒适。
先给出信息架构和视觉方向，再实现主要页面。
```

**完善移动端流程**

```text
使用 apple-ui-skill，设计 Android 现场服务 App 的工单编辑流程。
支持搜索、修改状态、保存失败重试和返回时保留草稿。
注意触控、大字体和单手使用。
```

如需在浏览器、模拟器或桌面应用中检查实际效果，请在需求中说明。
Skill 会根据项目环境选择可执行的检查，并说明结果覆盖了哪些功能与场景。

## 更新

在下载的安装器所在目录运行：

```text
python installer.py --agent codex --update
```

将 `codex` 换成 `claude` 或 `gemini` 即可更新对应安装。
更新会保留旧版本备份，路径会显示在命令输出中。若安装中断，可按提示使用 `--recover` 恢复。

## 下载与版本

当前版本：**2.0.0-dev.5 · 预览版**。

[查看版本说明与下载](https://github.com/rw0104/apple-ui-skill/releases)

手动安装时，选择以 `-runtime.zip` 结尾的文件，解压后将 `apple-ui-skill`
文件夹放入对应的技能目录。推荐使用上面的一键安装命令，它会自动下载并校验版本。

## 使用许可

本项目采用 [PolyForm Noncommercial 1.0.0](LICENSE.md)，允许许可证规定的
非商业使用。**商业用途需获得单独书面授权**，可通过
[商业授权申请](https://github.com/rw0104/apple-ui-skill/issues/new?template=commercial-authorization.yml)
联系维护者。更多说明见 [NOTICE.md](NOTICE.md)。
