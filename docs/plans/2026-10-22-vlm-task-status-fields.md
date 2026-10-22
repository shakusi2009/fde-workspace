# VLM Task Status Fields Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add task status and task end time to the VLM task list.

**Architecture:** Extend the existing RDS projection and API model with `task_status` and nullable `updated_at`. Keep the numeric status code in the API and map it to localized labels and Element Plus tag styles in the Vue view.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Extend API contract tests

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Add `task_status` and `update_time` to mocked database rows.
2. Assert the API returns the numeric status and nullable end time.
3. Run `npm run vlm:test` and confirm the contract test fails before implementation.

### Task 2: Extend backend query and response

**Files:**
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`

1. Add `task_status` and `update_time` to the task query projection.
2. Add `task_status` and nullable `updated_at` to `VlmTask`.
3. Map database values into the response model.
4. Run `npm run vlm:test`.

### Task 3: Extend the task table

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmTaskListView.vue`

1. Extend the TypeScript task model.
2. Render status codes as 未开始, 进行中, or 已完成.
3. Render `updated_at` as the task end time and show `--` when absent.
4. Run `npm run build`.

### Task 4: Verify real data

1. Restart the services.
2. Query the task API and verify both fields.
3. Open the task list and verify the two new columns render correctly.
