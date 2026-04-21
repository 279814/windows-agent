# Windows Desktop Agent Platform Dev Workspace

This `dev/` workspace is the isolated development area for the Windows-compatible MCP desktop agent platform.

## Global Development Rule

本项目采用模块化开发，先明确具体架构、技术实现和每个模块在架构中的位置和作用，再进行单个模块开发。模块之间尽量解耦。注意每个小模块开发完成后，都要进行实际测试，确保正常运行，防止项目后期崩溃。

## Development Stages

- Stage 0: Workspace setup and architecture baselining
- Stage 1: MCP server skeleton + perception + executor primitives
- Stage 2: Planner + task orchestration + state management
- Stage 3: Safety gate + audit + recovery
- Stage 4: Cross-application workflow support

## Working Rules

- Do not modify `Windows-MCP-main` directly.
- If upstream code is needed, copy it into `dev/` and adapt there.
- Every module must have an interface first, implementation second, then an actual test.
- Keep modules small, focused, and independently testable.
- Prefer stable, observable, and reversible changes.
