# VLM LangGraph Execution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute a selected parent VLM task through a single-role LangGraph agent and persist the result as a task item.

**Architecture:** FastAPI reads immutable execution context from RDS, invokes a one-node LangGraph using an Ark-compatible ChatOpenAI client, then inserts success/failure output and token usage into `vlm_tasks_item`. The Node gateway validates that the selected model exists in SQLite. Vue presents a modal with inherited context, model selection, execution result, and refreshes the item table.

**Tech Stack:** LangGraph, LangChain OpenAI, Volcengine Ark OpenAI-compatible API, FastAPI, PyMySQL, Express, SQLite, Vue 3, Element Plus.

---

### Task 1: Add agent configuration and dependencies

**Files:**
- Modify: `.env`
- Modify: `ai-vlm/backend/app/config.py`
- Modify: `ai-vlm/backend/requirements.txt`

1. Add an Ark-compatible Base URL setting.
2. Load API key and optional default model name from `.env`.
3. Install pinned LangGraph and LangChain OpenAI packages.

### Task 2: Add failing agent and API tests

**Files:**
- Create: `ai-vlm/backend/tests/test_agent_service.py`
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Test system/user message construction and token extraction.
2. Test missing API key.
3. Test execution-context response.
4. Test execution response and error mapping.

### Task 3: Implement LangGraph execution backend

**Files:**
- Create: `ai-vlm/backend/app/services/agent_service.py`
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Read task, prompt title/content, and task input from RDS.
2. Build a one-node LangGraph with system and human messages.
3. Invoke the selected model through Ark.
4. Persist item output, status, and token usage.
5. Return the inserted task item.

### Task 4: Validate model selection at the gateway

**File:** `server/index.ts`

1. Intercept execution POST requests.
2. Verify the requested model ID exists in SQLite.
3. Reject missing/unknown models before forwarding.

### Task 5: Build the execution dialog

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmTaskItemListView.vue`
- Modify: `src/styles.css`

1. Add 新增执行 immediately before 刷新列表.
2. Load inherited prompt and input plus SQLite model options.
3. Add read-only prompt/input/result areas and model selector.
4. Execute, display output, and refresh the item list.

### Task 6: Verify

1. Run unit tests, production build, and diff checks.
2. Restart services.
3. Verify context/model loading through the gateway.
4. Execute one temporary real Agent call when configuration is valid.
5. Verify RDS persistence, then clean up the temporary item.
