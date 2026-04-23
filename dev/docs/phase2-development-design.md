# Windows Desktop Agent Phase 2 开发文档

## 1. 文档目标

本文档用于承接 `dev/Windows-MCP-Design-v1.md` 的第二阶段目标，结合当前 `dev/` 与 `Windows-MCP-main/` 的真实代码状态，输出可落地的第二阶段开发方案，覆盖：

- 当前实现状态与问题归纳
- 第二阶段总体目标与边界
- 概要设计
- 详细设计
- 开发任务清单
- 测试与验收清单

本文档默认遵循以下规则：

- 前端/编排/协议扩展统一在 `dev/` 内开发。
- 不直接修改 `Windows-MCP-main/`，仅复用其成熟底层能力。
- 每个模块先定义接口，再实现内部逻辑，再补测试。
- 优先保证稳定性、可恢复性、可验证性。

---

## 2. 输入材料与结论摘要

### 2.1 已阅读材料

- `dev/Windows-MCP-Design-v1.md`
- `dev/README.md`
- `dev/docs/ai-virtual-mouse-motion-scheduler-plan.md`
- `dev/src/desktop_agent_dev/*`
- `Windows-MCP-main/README.md`
- `Windows-MCP-main/docs/源码分析.md`
- `Windows-MCP-main/.claude/skills/windows-mcp-tool-tester/SKILL.md`
- `Windows-MCP-main/src/windows_mcp/*`

### 2.2 当前仓库真实状态

当前仓库与口头阶段描述存在一定偏差，需以代码现状为准：

- `dev/src/desktop_agent_dev/` 已经具备 MCP Server、工具注册、资源目录、输入/窗口/运动/任务等骨架。
- `motion_preview`、`overlay_state` 等 Phase 1 能力已经落地，并在 `manifest.py`、`tool_registry.py` 中作为重点能力暴露。
- `ocr_extract`、`ui_match`、`vision_capture`、`vision_locate` 四个工具仍是明确的 TODO 占位，仅在 `tool_specs/vision_tools.py` 中返回 `not_implemented`。
- `TaskStore` 仍为内存态，尚不具备 checkpoint 持久化、断线恢复、进程重启恢复能力。
- 当前仓库中未发现你提到的以下文件：
  - `dev/docs/stage1-development-plan.md`
  - `dev/docs/phase1_runbook.md`
  - `dev/docs/phase1_final_integration_checklist.md`
  - `dev/scripts/run_phase1_tests.py`

### 2.3 第二阶段核心结论

第二阶段不应被理解为“只把四个 TODO 工具补齐”，而应理解为在现有 Phase 1 骨架上完成以下能力闭环：

1. 视觉感知闭环：`vision_capture`、`ocr_extract`、`vision_locate`、`ui_match`
2. 长任务恢复闭环：任务持久化、checkpoint、恢复与重放
3. 跨应用协同闭环：剪贴板、文件、窗口、进程、任务状态的统一编排
4. 工程交付闭环：安装、依赖探测、健康检查、回归测试

---

## 3. 当前系统理解

## 3.1 `Windows-MCP-main` 的角色

`Windows-MCP-main` 是成熟的 Windows 底层能力仓库，强项在于：

- Desktop/Snapshot/Screenshot 能力成熟
- UIA 树遍历成熟
- 输入与窗口控制成熟
- 剪贴板、进程、通知、注册表等系统能力成熟

其核心价值是为 `dev/` 提供可靠后端，而不是成为未来业务层的主开发目录。

### 3.2 `dev/` 的角色

`dev/` 已经是新的平台主入口，负责：

- MCP Server 入口与工具目录
- 元数据资源与发现机制
- 对底层 Windows-MCP 的适配与兼容
- 输入、窗口、运动、任务等自有封装
- 后续安全、规划、恢复、跨应用协同扩展

### 3.3 当前 `dev/` 架构概览

现有 `dev/src/desktop_agent_dev/` 可抽象为：

- `mcp_server.py`
  - 服务装配入口
  - 初始化 `Perception`、`Executor`、`Planner`、`SafetyGate`、`TaskStore`
- `backend_windows_mcp.py`
  - 动态加载 `Windows-MCP-main` 后端
  - 兼容 `DesktopState`、`focused_control` 等字段差异
- `perception.py`
  - 将后端 `Desktop.get_state()` 转换为本项目的 `DesktopSnapshot`
- `executor.py`
  - 输入、窗口、运动、验证相关的主执行器
- `planner.py`
  - 当前为简单 observe/execute/verify 三步规划器
- `state.py`
  - 当前为内存态任务状态存储
- `tool_specs/*`
  - 工具接口定义与注册
- `manifest.py`、`tool_registry.py`
  - 文档资源、能力目录、工具元数据与 discoverability

### 3.4 当前第二阶段缺口

当前与第二阶段目标直接相关的缺口如下：

- 缺少视觉采集缓存层与视觉结果标准结构
- 缺少 OCR 引擎适配层
- 缺少视觉定位策略与多源融合逻辑
- 缺少 UIA 结构匹配能力
- 缺少任务持久化存储与 checkpoint
- 缺少恢复调度器与重放机制
- 缺少跨应用工作流抽象
- 缺少一键安装、环境探测、能力自检
- 缺少 Phase 2 专项测试与回归基线

---

## 4. 第二阶段目标与范围

## 4.1 阶段目标

第二阶段目标定义为：

- 在不破坏 Phase 1 既有输入/窗口/运动能力的前提下，补齐视觉感知、长任务恢复、跨应用协同和安装交付能力。

### 4.2 范围内

- `vision_capture` 真正输出截图与视觉上下文
- `ocr_extract` 真正输出 OCR 结果
- `vision_locate` 真正输出视觉定位结果
- `ui_match` 真正输出结构匹配结果
- 任务 checkpoint、恢复、恢复后验证
- 跨应用任务编排基础骨架
- 安装器与环境自检
- Phase 2 测试方案与集成回归

### 4.3 范围外

- 训练自定义视觉模型
- 引入重量级云端推理依赖作为唯一方案
- 重写 `Windows-MCP-main` 的底层 UIA 与输入系统
- 在第二阶段内做完整企业策略平台

---

## 5. 第二阶段概要设计

## 5.1 总体设计原则

- 继续采用分层架构，不把视觉/OCR/恢复逻辑直接塞入 `executor.py`
- 对外仍只暴露 MCP 工具，对内新增能力服务层
- 视觉能力优先做“本地可运行 + 可降级 + 可缓存”
- 恢复能力优先保证“状态可重建”，其次才是“动作自动重放”
- 跨应用协同优先做“可编排”和“可验证”，不追求一次性做复杂智能

## 5.2 新增模块建议

建议在 `dev/src/desktop_agent_dev/` 下新增以下模块：

```text
vision/
  __init__.py
  capture.py
  ocr.py
  locate.py
  ui_match.py
  models.py
  cache.py

recovery/
  __init__.py
  store.py
  checkpoints.py
  replayer.py
  policies.py

workflow/
  __init__.py
  artifacts.py
  bridge.py
  coordinator.py
  contracts.py

installer/
  __init__.py
  probe.py
  bootstrap.py
  healthcheck.py
```

## 5.3 第二阶段目标架构

```text
MCP Server
  ├─ Tool Specs / Registry
  ├─ Perception
  ├─ Executor
  ├─ Planner
  ├─ SafetyGate
  ├─ TaskStore (persistent)
  ├─ VisionService
  │   ├─ VisionCaptureService
  │   ├─ OCRService
  │   ├─ VisionLocateService
  │   └─ UIMatchService
  ├─ RecoveryService
  │   ├─ CheckpointStore
  │   ├─ TaskReplayEngine
  │   └─ RecoveryPolicy
  ├─ WorkflowCoordinator
  │   ├─ ArtifactBridge
  │   ├─ Clipboard/File bridge
  │   └─ Cross-app step runner
  └─ Installer/HealthCheck
```

## 5.4 与现有代码的边界

- `Perception` 继续负责基础桌面快照和后端状态适配
- `Executor` 继续负责动作执行、动作验证、窗口控制
- 视觉能力不直接耦合到 `Perception` 内部，而是由 `VisionService` 基于 `Perception` 输出继续加工
- 恢复能力不直接塞到 `TaskStore` 中，而是拆成存储、checkpoint、replay 三层
- 跨应用协同不直接写死到 `Planner`，而是通过 `WorkflowCoordinator` 组织多步任务

---

## 6. 第二阶段详细设计

## 6.1 视觉能力总设计

### 6.1.1 统一设计目标

四个工具应形成一条统一视觉链路：

1. `vision_capture`
   - 采集图像、区域、上下文
2. `ocr_extract`
   - 从图像或区域中提取文本
3. `vision_locate`
   - 基于模板、文本、语义线索定位目标区域
4. `ui_match`
   - 基于 UIA 树与视觉结果对目标做结构级匹配

### 6.1.2 多源优先级

视觉链路的建议优先级：

1. UIA 命中
2. OCR 文本命中
3. 视觉模板/区域命中
4. 坐标兜底

### 6.1.3 统一返回结构

四个工具的结果建议统一包含以下字段：

- `ok`
- `tool`
- `message`
- `data.status`
- `data.source`
- `data.capture_id`
- `data.display_id`
- `data.bounds`
- `data.confidence`
- `data.matches`
- `data.metadata`
- `error`

---

## 6.2 `vision_capture` 详细设计

### 6.2.1 目标

提供标准化视觉采集入口，为 OCR、定位、调试、人工确认提供统一输入。

### 6.2.2 输入参数建议

```json
{
  "mode": "full|active_window|region|control",
  "display_id": 0,
  "region": {"x": 0, "y": 0, "width": 800, "height": 600},
  "window": {"name": "Notepad", "handle": 0, "pid": 0},
  "include_cursor": true,
  "include_annotations": false,
  "persist": true
}
```

### 6.2.3 输出结构建议

```json
{
  "ok": true,
  "tool": "vision_capture",
  "message": "ok",
  "data": {
    "status": "captured",
    "capture_id": "cap-20260423-001",
    "source": "windows-mcp+screenshot-cache",
    "display_id": 0,
    "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080},
    "image_path": "dev/tmp/captures/cap-20260423-001.png",
    "active_window": {...},
    "focused_control": {...},
    "metadata": {...}
  },
  "error": null
}
```

### 6.2.4 内部实现

- 复用 `Perception.snapshot(with_screenshot=True)`
- 增加 `VisionCaptureService`
- 负责：
  - 裁剪区域
  - 写入缓存目录
  - 生成 capture_id
  - 记录显示器/DPI/窗口上下文

### 6.2.5 关键设计点

- 采集结果必须可复用，避免同一任务频繁重复截图
- capture 结果必须可被 OCR、定位和恢复过程引用
- `persist=false` 时可只返回内存句柄或临时文件引用

---

## 6.3 `ocr_extract` 详细设计

### 6.3.1 目标

从全屏、窗口、区域、已缓存 capture 中提取文本及位置信息。

### 6.3.2 输入参数建议

```json
{
  "capture_id": "cap-20260423-001",
  "region": {"x": 100, "y": 200, "width": 400, "height": 120},
  "languages": ["en", "zh"],
  "strategy": "auto|tesseract|windows",
  "include_lines": true,
  "include_words": true,
  "normalize_whitespace": true
}
```

### 6.3.3 输出结构建议

```json
{
  "ok": true,
  "tool": "ocr_extract",
  "message": "ok",
  "data": {
    "status": "extracted",
    "capture_id": "cap-20260423-001",
    "source": "ocr:tesseract",
    "text": "Save As",
    "lines": [
      {
        "text": "Save As",
        "bounds": {"x": 120, "y": 240, "width": 88, "height": 24},
        "confidence": 0.98
      }
    ],
    "words": [
      {
        "text": "Save",
        "bounds": {"x": 120, "y": 240, "width": 44, "height": 24},
        "confidence": 0.99
      }
    ],
    "metadata": {
      "languages": ["en"],
      "engine": "tesseract"
    }
  },
  "error": null
}
```

### 6.3.4 实现策略

- 优先支持本地引擎可插拔：
  - `tesseract` 优先
  - Windows OCR 作为后备或可选
- 新增 `OCRService`
- 输入源统一来自：
  - `capture_id`
  - `vision_capture` 实时截图
  - 指定 region 裁剪

### 6.3.5 关键设计点

- OCR 结果必须保留 bounding boxes
- 对中文/英文混合界面要支持多语言配置
- 输出需要可直接被 `vision_locate` 消费

---

## 6.4 `vision_locate` 详细设计

### 6.4.1 目标

根据文本、模板、颜色、语义标记或上游 OCR 结果定位屏幕目标区域。

### 6.4.2 输入参数建议

```json
{
  "capture_id": "cap-20260423-001",
  "query": {
    "text": "保存",
    "role": "button",
    "near_text": "文件名",
    "template_path": "",
    "color_hint": ""
  },
  "strategy": "auto|ocr-first|template-first|hybrid",
  "max_results": 5,
  "min_confidence": 0.7
}
```

### 6.4.3 输出结构建议

```json
{
  "ok": true,
  "tool": "vision_locate",
  "message": "ok",
  "data": {
    "status": "matched",
    "capture_id": "cap-20260423-001",
    "source": "hybrid",
    "matches": [
      {
        "bounds": {"x": 1014, "y": 768, "width": 90, "height": 30},
        "center": {"x": 1059, "y": 783},
        "confidence": 0.92,
        "matched_by": "ocr+role",
        "text": "保存",
        "role": "button"
      }
    ],
    "metadata": {
      "strategy": "ocr-first"
    }
  },
  "error": null
}
```

### 6.4.4 实现策略

- 新增 `VisionLocateService`
- 支持三种定位方式：
  - OCR 文本定位
  - 模板图匹配
  - 与 UIA/窗口上下文联动的混合定位

### 6.4.5 定位顺序建议

1. 若给出 `text`，优先 OCR 命中
2. 若同时给出 `role`、`near_text`，进行语义过滤
3. 若给出 `template_path`，执行模板匹配
4. 若 UIA 中可找到近似控件，做视觉与 UIA 的交叉验证

### 6.4.6 关键设计点

- 定位结果必须输出多个候选，而不是只输出第一个
- 必须保留 `matched_by`
- 必须显式输出 `confidence`

---

## 6.5 `ui_match` 详细设计

### 6.5.1 目标

基于 UIA 树与目标约束完成结构级匹配，用于解决“视觉上像，但语义不确定”的问题。

### 6.5.2 输入参数建议

```json
{
  "window": {"name": "Notepad", "handle": 0, "pid": 0},
  "selector": {
    "name": "保存",
    "control_type": "ButtonControl",
    "automation_id": "",
    "class_name": "",
    "role": "button"
  },
  "fallback_capture_id": "cap-20260423-001",
  "include_candidates": true
}
```

### 6.5.3 输出结构建议

```json
{
  "ok": true,
  "tool": "ui_match",
  "message": "ok",
  "data": {
    "status": "matched",
    "source": "uia",
    "best_match": {
      "name": "保存",
      "control_type": "ButtonControl",
      "bounds": {"x": 1014, "y": 768, "width": 90, "height": 30},
      "automation_id": "1",
      "class_name": "Button",
      "confidence": 0.97
    },
    "candidates": [...],
    "metadata": {
      "window_handle": 123456,
      "fallback_used": false
    }
  },
  "error": null
}
```

### 6.5.4 实现策略

- 新增 `UIMatchService`
- 复用 `Perception.tree_nodes`
- 支持：
  - 精确匹配
  - 模糊名称匹配
  - role/control_type 过滤
  - automation_id/class_name 过滤
- 当 UIA 不稳定时，可联动 `vision_locate` 做 fallback

### 6.5.5 关键设计点

- `ui_match` 应作为动作前验证工具，而不是仅服务调试
- 匹配结果可供 `input_click`、`input_type` 前置确认
- 未来可扩展为“结构 diff”能力

---

## 6.6 长任务恢复设计

## 6.6.1 目标

实现任务在以下场景中的恢复能力：

- MCP 客户端断连
- server 进程重启
- 单步动作失败后从最近 checkpoint 恢复
- 用户中断后保留已知上下文

### 6.6.2 当前问题

当前 `TaskStore` 只有内存态：

- 进程退出即丢失
- 没有 checkpoint
- 没有动作回放
- 没有恢复策略

### 6.6.3 设计方案

引入三层结构：

- `PersistentTaskStore`
  - 持久化 task record
- `CheckpointStore`
  - 持久化关键观察结果和动作前后状态
- `TaskReplayEngine`
  - 基于 checkpoint 决定恢复、跳过、重试、重做

### 6.6.4 建议数据结构

任务主记录：

```json
{
  "task_id": "task-001",
  "goal": "打开记事本并输入文本",
  "status": "executing",
  "step_index": 1,
  "retries": 0,
  "last_action": {...},
  "last_error": null,
  "updated_at": "2026-04-23T12:00:00Z"
}
```

checkpoint 记录：

```json
{
  "task_id": "task-001",
  "step_index": 1,
  "phase": "before_action",
  "snapshot_ref": "cap-20260423-001",
  "active_window": {...},
  "focused_control": {...},
  "planned_action": {...},
  "verification": null
}
```

### 6.6.5 恢复策略

- `resume_safe`
  - 仅从 verify 阶段失败回到观察阶段
- `resume_with_reobserve`
  - 重新截图/OCR/UIA，重新计算目标
- `resume_with_replay`
  - 在目标仍可确认时重放动作
- `manual_intervention_required`
  - 上下文不可信时要求人工确认

### 6.6.6 存储介质建议

- Phase 2 可采用本地 JSONL / SQLite
- 推荐优先 SQLite：
  - 更适合 checkpoint 与任务查询
  - 更利于后续审计扩展

---

## 6.7 跨应用协同设计

## 6.7.1 目标

让桌面 agent 能稳定处理“应用 A 读取 -> 中间标准化 -> 应用 B 写入/操作”的流程。

### 6.7.2 协同对象

- 剪贴板
- 文件
- 窗口与前台焦点
- 进程与应用生命周期
- capture 与 OCR 中间结果

### 6.7.3 新增模块

- `workflow/artifacts.py`
  - 定义跨步骤共享产物
- `workflow/bridge.py`
  - 剪贴板、文件、窗口上下文桥接
- `workflow/coordinator.py`
  - 协调多个 app step

### 6.7.4 标准产物结构

```json
{
  "artifact_id": "artifact-001",
  "type": "text|file|table|image|window_ref",
  "source_tool": "ocr_extract",
  "source_app": "Browser",
  "payload": {...},
  "created_at": "2026-04-23T12:00:00Z"
}
```

### 6.7.5 协同工作流最小闭环

1. 从源应用采集状态
2. 提取目标数据
3. 归档为 artifact
4. 切换到目标应用
5. 执行动作
6. 验证目标应用结果

### 6.7.6 Phase 2 最小场景建议

- 浏览器文本复制 -> 记事本输入
- 文件下载 -> 本地文件检测 -> 应用打开
- OCR 结果 -> 窗口切换 -> 表单输入

---

## 6.8 一键安装器设计

## 6.8.1 目标

降低项目部署门槛，使新环境可以完成：

- Python 环境检查
- 依赖安装
- `Windows-MCP-main` 路径配置
- OCR 依赖检查
- 健康检查

### 6.8.2 组成

- `installer/probe.py`
  - 环境探测
- `installer/bootstrap.py`
  - 安装流程
- `installer/healthcheck.py`
  - 启动后检查

### 6.8.3 检查项目

- Python 版本
- Windows 版本
- `Windows-MCP-main` 路径是否存在
- UIA 依赖是否可用
- 截图能力是否可用
- OCR 引擎是否可用
- `desktop-agent-dev` 是否可启动

### 6.8.4 交付形式

- PowerShell 安装脚本
- Python healthcheck 脚本
- `dev/README.md` 增补安装说明

---

## 7. 接口设计建议

## 7.1 服务注入

建议在 `mcp_server.py` 的 `AppServices` 中新增：

```python
vision: VisionService
recovery: RecoveryService
workflow: WorkflowCoordinator
installer: InstallerService | None
```

## 7.2 工具与服务映射

| 工具 | 服务 | 说明 |
|---|---|---|
| `vision_capture` | `VisionCaptureService` | 图像采集与缓存 |
| `ocr_extract` | `OCRService` | OCR 抽取 |
| `vision_locate` | `VisionLocateService` | 视觉定位 |
| `ui_match` | `UIMatchService` | UIA 结构匹配 |
| `task_plan` | `Planner + RecoveryService` | 规划后立刻落库 |
| `task_state` | `PersistentTaskStore` | 查询实时任务状态 |
| `task_resume` | `TaskReplayEngine` | 第二阶段新增 |
| `workflow_run` | `WorkflowCoordinator` | 第二阶段新增 |

## 7.3 新增工具建议

除四个 TODO 工具转正外，建议第二阶段新增两个工具：

- `task_resume`
  - 从 checkpoint 恢复任务
- `workflow_run`
  - 运行跨应用工作流

这两个工具能把第二阶段的“恢复”和“协同”显式暴露出来。

---

## 8. 开发任务清单

## 8.1 任务分组

### A. 视觉基础设施

- [ ] 新增 `vision/models.py`，定义 capture/OCR/locate/match 统一数据结构
- [ ] 新增 `vision/cache.py`，管理 capture 缓存目录与 capture_id
- [ ] 新增 `vision/capture.py`
- [ ] 新增 `vision/ocr.py`
- [ ] 新增 `vision/locate.py`
- [ ] 新增 `vision/ui_match.py`
- [ ] 在 `mcp_server.py` 注入 `VisionService`

### B. 四个 TODO 工具落地

- [ ] 将 `tool_specs/vision_tools.py` 从 placeholder 改为真实服务调用
- [ ] 保留 `not_implemented` 兼容分支，仅在依赖未安装或引擎不可用时返回
- [ ] 为四个工具补充参数 schema
- [ ] 为四个工具补充真实 output example

### C. 长任务恢复

- [ ] 将 `TaskStore` 从内存态拆为接口层
- [ ] 新增 `recovery/store.py`
- [ ] 新增 `recovery/checkpoints.py`
- [ ] 新增 `recovery/replayer.py`
- [ ] 新增 `task_resume` 工具
- [ ] 将 `Executor` 的关键动作接入 checkpoint

### D. 跨应用协同

- [ ] 新增 `workflow/artifacts.py`
- [ ] 新增 `workflow/bridge.py`
- [ ] 新增 `workflow/coordinator.py`
- [ ] 实现最小 artifact store
- [ ] 实现跨应用三类最小示例流程

### E. 一键安装器

- [ ] 新增 `installer/probe.py`
- [ ] 新增 `installer/bootstrap.py`
- [ ] 新增 `installer/healthcheck.py`
- [ ] 新增 PowerShell 安装脚本
- [ ] 更新 `dev/README.md`

### F. 文档与测试

- [ ] 补 Phase 2 测试计划文档
- [ ] 补 Phase 2 集成 runbook
- [ ] 补 Phase 2 checklist
- [ ] 建立脚本化回归测试入口

---

## 8.2 推荐开发顺序

### 第一批：接口与基础设施

1. 统一视觉数据结构
2. 统一任务持久化接口
3. `VisionService` / `RecoveryService` 注入

### 第二批：最小可用能力

1. `vision_capture`
2. `ocr_extract`
3. checkpoint 持久化
4. `task_resume`

### 第三批：增强能力

1. `vision_locate`
2. `ui_match`
3. `workflow_run`

### 第四批：工程化

1. 安装器
2. 健康检查
3. 完整回归

---

## 9. 测试计划

## 9.1 测试原则

- 每个模块开发完成后立刻测试
- 先接口测试，再服务测试，再工具测试，再真实桌面集成测试
- 优先验证“失败时是否可解释、可恢复”

## 9.2 模块测试清单

### `vision_capture`

- [ ] 全屏采集
- [ ] 活动窗口采集
- [ ] 区域采集
- [ ] 多显示器采集
- [ ] 持久化缓存生成

### `ocr_extract`

- [ ] 英文 OCR
- [ ] 中文 OCR
- [ ] 中英混合 OCR
- [ ] 区域 OCR
- [ ] OCR 失败与空结果

### `vision_locate`

- [ ] 基于文本定位
- [ ] 基于 template 定位
- [ ] OCR + role 混合定位
- [ ] 多候选返回
- [ ] 低置信度场景

### `ui_match`

- [ ] 通过 name 匹配
- [ ] 通过 control_type 匹配
- [ ] 通过 automation_id 匹配
- [ ] UIA 失败 fallback 到视觉定位

### 恢复能力

- [ ] 任务创建后持久化
- [ ] 动作前 checkpoint
- [ ] 动作后 checkpoint
- [ ] server 重启后恢复
- [ ] verify 失败后重新观察恢复

### 跨应用协同

- [ ] 浏览器 -> 记事本
- [ ] 文件下载 -> 打开
- [ ] OCR -> 输入框填充

### 安装器

- [ ] 干净环境安装
- [ ] 缺依赖探测
- [ ] OCR 引擎缺失提示
- [ ] 健康检查结果输出

## 9.3 Phase 2 验收标准

- 四个 TODO 工具不再返回固定 placeholder
- 至少一条长任务可跨进程恢复
- 至少两条跨应用流程可稳定跑通
- 新环境能通过一键安装与健康检查完成启动
- 所有新增能力都具备失败说明与降级路径

---

## 10. 风险与缓解

## 10.1 技术风险

- OCR 引擎在不同机器上的安装差异
- 多显示器/DPI 导致视觉坐标偏移
- UIA 与视觉结果不一致
- 任务恢复时上下文已变化

### 缓解方式

- 统一 capture 坐标系与 display metadata
- 所有视觉结果都带 `bounds` 与 `display_id`
- 恢复前默认重新观察
- UIA/视觉双源交叉验证

## 10.2 工程风险

- 第二阶段内容跨度大，容易边做边散
- `executor.py` 已较重，继续堆逻辑会失控

### 缓解方式

- 坚持服务层拆分
- 通过新增模块而不是继续加大单文件复杂度
- 每完成一项能力同步补测试与文档

---

## 11. 推荐交付物列表

第二阶段建议最终交付以下文件：

- `dev/docs/phase2-development-design.md`
- `dev/docs/phase2-test-plan.md`
- `dev/docs/phase2-runbook.md`
- `dev/docs/phase2-integration-checklist.md`
- `dev/scripts/run_phase2_tests.py`
- `dev/scripts/install_phase2.ps1`

---

## 12. 结论

从当前仓库状态看，第二阶段的真实重点不是“继续补几个工具”，而是把现有桌面执行骨架升级成真正具备视觉感知、恢复、协同和交付能力的平台。

具体落地路径建议为：

1. 先补统一服务层与数据结构
2. 再让四个 TODO 工具转正
3. 再补任务恢复与跨应用协同
4. 最后补安装器、runbook 和脚本化回归

这样可以最大限度复用 `Windows-MCP-main` 的成熟后端，同时保持 `dev/` 作为主平台的独立演进能力。
