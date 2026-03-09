# Nexa Node Runtime Architecture

## Overview

NodeExecutionRuntime is a dependency-based execution engine.

## Execution Flow

1. Initialize working context
2. Load compiled resource graph
3. Determine executable resources
4. Create execution waves
5. Run resources in parallel
6. Update context
7. Resolve final output

## Key Components

Working Context

Compiled Resource Graph

Wave Scheduler

Provider Executor

Plugin Executor

Final Output Resolver

## Parallel Execution

Resources in the same wave must not write to the same context key.