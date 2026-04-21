# Stage 1 Development Plan

## Goal
Build the first runnable skeleton of the Windows-compatible MCP desktop agent platform inside `dev/`, using `uv` for project management and execution.

## Scope
Stage 1 focuses on the minimum architecture required for later modular development:

1. MCP server bootstrap
2. Perception primitives
3. Executor primitives
4. Task planning interfaces
5. Safety gate interfaces
6. Actual tests for each module

## Module Layout

### `desktop_agent_dev.server`
Owns the MCP server bootstrap and tool registration.

### `desktop_agent_dev.perception`
Owns desktop observation primitives such as screenshot, window snapshot, and text extraction.

### `desktop_agent_dev.executor`
Owns the action layer for click, type, shortcut, and app control.

### `desktop_agent_dev.planner`
Owns task decomposition and plan representation.

### `desktop_agent_dev.safety`
Owns policy checks and confirmations.

### `desktop_agent_dev.state`
Owns task state and checkpoints.

## Development Order

1. Create the package skeleton.
2. Define module interfaces first.
3. Implement stubbed but runnable module behavior.
4. Add tests for each module.
5. Run tests and fix issues.

## Acceptance Criteria

- The dev workspace installs and runs with `uv`.
- The package exposes a runnable entry point.
- Core modules import successfully.
- Tests pass for the initial skeleton.
- The implementation remains isolated from `Windows-MCP-main`.
