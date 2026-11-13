# Apple UI Skill · 通用界面设计技能

为网页、移动 App 和 Windows/macOS/Linux 电脑客户端提供一致的设计方法、
平台适配、组件参考和可追溯验证。Apple 是设计研究来源之一；使用它不要求
苹果设备、SwiftUI 或 Xcode，也不要求产品采用苹果外观。

本仓库是**成品分发入口**：提供安装、更新、使用说明和版本下载。
完整运行文件放在 Releases 的成品包中；开发仓库、内部规划、测试报告和
研究过程不随成品发布。安装后的 Skill 指令、知识资料及运行代码可以在本机查看。

**授权：允许许可证规定的非商业使用；商业用途须获得单独书面授权。**
采用 [PolyForm Noncommercial 1.0.0](LICENSE.md)，属于非商业授权分发，
不是 OSI 意义的开源许可。详见 [授权与第三方说明](NOTICE.md)。

## 一键安装

需要 Python **3.10 或更高版本**。默认安装到当前用户的 Codex 技能目录。
安装器会校验版本及 SHA-256，并在安装前检查压缩包路径。

Windows PowerShell：

```powershell
irm 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/install.ps1?v=2.0.0-dev.5-1' | iex
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/install.sh | bash
```

需要查看脚本或选择其他宿主时，先下载或克隆本仓库，再运行：

```text
python installer.py --agent codex
python installer.py --agent claude
python installer.py --agent gemini
```

| 宿主 | 默认用户级安装位置 | 调用方式 |
| --- | --- | --- |
| Codex | `~/.agents/skills/apple-ui-skill` | `$apple-ui-skill` |
| Claude Code | `~/.claude/skills/apple-ui-skill` | `/apple-ui-skill` |
| Gemini CLI | `~/.gemini/skills/apple-ui-skill` | 按宿主的技能发现/激活流程使用 |

项目级安装使用 `--scope project`，从目标项目目录启动；也可通过
`--destination <完整目标目录>` 指定路径。不要同时向同一宿主的多个发现目录
安装同名 Skill。安装后开启一个新会话，或使用宿主支持的技能刷新功能。
宿主账号权限、额度和工具授权由宿主自身管理。

## 开始使用

例如：

```text
使用 apple-ui-skill，为 Windows 和 Web 设计一个工单管理界面。
保留现有 React 技术栈，支持搜索、编辑、保存失败重试、键盘操作和窄窗口。
请先确定信息架构、状态模型和视觉系统，再实现并验证主要流程。
```

成品包含：

- 面向实际产品和目标平台的设计流程、信息架构和八项视觉系统绑定。
- 设计来源查询、核心指南分析、图像构图和有边界的视频观察。
- 菜单、选择器、组合框、日期、浮层、表单、模态、导航和搜索参考。
- React/Vue 薄适配及 SSR、水合和生命周期参考。
- 项目四件套、状态恢复、显式迁移与分模式的交付检查。
- 可选的当次浏览器回放，以及连接项目自身桌面/移动验证器的接口。

可用功能完整保留，开发维护资料被排除。能力查询会说明哪些是设计指导、
哪些有参考实现、哪些仅在具名环境实际执行过。参考代码并不等于用户产品已经验证。

## 检查与可选依赖

进入安装目录后运行：

```text
python -B scripts/validate_skill.py --structure-only
python -B scripts/query_capabilities.py --gaps
python -B scripts/apple_ui_workflow.py --help
```

基本设计、查询和工作流脚本使用 Python 标准库。需要实际浏览器回放时，
在你自己的 Python 环境安装可选依赖：

```text
python -m pip install -r requirements-live.txt
python -m playwright install chromium
python -B scripts/validate_skill.py --live --browser chromium --output-dir <技能目录之外的证据目录>
```

Linux 浏览器还需要对应系统依赖。React/Vue 回放另外需要 Node 和运行包中的
框架依赖清单；按随包说明安装到独立目录。移动/桌面项目需要自己选择的平台
运行环境；没有某个平台的 SDK 不影响设计指导，但不能据此声称该平台已运行通过。

## 更新与恢复

```text
python installer.py --agent codex --update
```

已有安装不会被默认覆盖。显式更新会保留旧目录备份；本地修改也会留在备份中。
如果上一次安装中断，按安装器给出的提示使用 `--recover`。备份路径会打印出来，
不要在确认迁移完成之前删除它。更新到某个版本不等于自动迁移用户项目的四件套。

## 下载与版本

[Releases](https://github.com/rw0104/apple-ui-skill/releases) 提供完整运行包、
版本说明及 SHA-256 清单。`distribution.json` 固定安装器默认获取的版本。
本次版本为 **2.0.0-dev.5 开发预览版**；保留已知能力边界，不标成正式稳定版。
核心本地功能可离线使用，依赖安装与查阅最新官方来源需要网络。

## 商业授权

商业用途没有获得默认许可。请通过
[商业授权申请](https://github.com/rw0104/apple-ui-skill/issues/new?template=commercial-authorization.yml)
联系维护者，说明使用场景和范围，取得单独书面授权后再开展对应商业使用。
普通非商业使用遵守随包许可证即可，无需获取技术激活码。

安装器只获取发行包，不收集设计项目或上传本地项目内容。
