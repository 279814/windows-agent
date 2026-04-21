# 第一阶段测试运行手册

## 1. 如何启动 MCP Server

在 `dev` 目录下运行：

```bash
uv run desktop-agent-dev
```

如果要接真实 Windows-MCP 后端：

```bash
uv run desktop-agent-dev --windows-mcp-root E:\path\to\Windows-MCP
```

## 2. 如何执行第一阶段最终测试

推荐运行：

```bash
uv run python scripts/run_phase1_tests.py --real-backend-root E:\developdata\code\windows-mcp\Windows-MCP-main
```

如果只想先跑本地测试：

```bash
uv run python scripts/run_phase1_tests.py --skip-integration
```

## 3. 如何直观查看效果

### 方式一：看真实桌面变化

- 先打开一个测试窗口，例如记事本。
- 执行点击、输入、快捷键。
- 直接观察窗口是否变化。

### 方式二：看截图和 UIA 输出

脚本会输出：

- 运行前后的窗口状态
- 截图是否存在
- UIA 节点是否读取成功
- 执行动作后的返回结构

### 方式三：看 diff

脚本会对前后状态做简单 diff，帮助你快速判断：

- 活动窗口是否变化
- 截图是否真的采集到了
- UIA 节点是否发生变化

## 4. 当前系统执行流程

1. 客户端把目标发给 MCP Server。
2. Planner 生成简单任务计划。
3. Perception 读取窗口 / 截图 / UIA。
4. SafetyGate 判断是否允许动作。
5. Executor 执行点击 / 输入 / 快捷键 / 窗口操作。
6. Perception 再次读取状态。
7. 系统对前后状态做 diff。
8. 返回结果给客户端。

## 5. 支持的客户端

当前阶段可以通过标准 MCP 方式接入：

- Claude
- Cursor
- Codex

前提是它们都已配置为连接本项目暴露的 MCP Server。
