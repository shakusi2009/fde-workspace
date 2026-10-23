# VLM Task Type And Input Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add task type and task input fields to VLM task creation while recording creation time at save.

**Architecture:** Add nullable `task_input TEXT` for existing-row compatibility, but require it for new tasks. The selected type filters prompt templates in Vue; FastAPI validates the payload and the repository confirms the selected open prompt has the same type before inserting with `CURRENT_TIMESTAMP`.

**Tech Stack:** MySQL RDS, FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Add `task_input` to RDS

1. Add `task_input TEXT NULL` to `vlm_tasks_list`.
2. Verify existing row count and column definition.

### Task 2: Extend API tests and models

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`
- Modify: `ai-vlm/backend/app/schemas.py`

1. Require `task_type` as `label` or `dig`.
2. Require non-empty `task_input`.
3. Test trimmed payload mapping and type mismatch errors.

### Task 3: Implement transactional creation

**Files:**
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`

1. Add `task_input` to task selects.
2. Validate the selected prompt is open and matches `task_type`.
3. Insert `task_input` and use `CURRENT_TIMESTAMP` for `create_time`.

### Task 4: Update task creation UI

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmTaskListView.vue`

1. Add task type segmented selection.
2. Filter prompt templates by selected type.
3. Add required task input textarea.
4. Submit type, prompt, input, and remarks.

### Task 5: Verify

1. Run backend tests, production build, and diff checks.
2. Restart services.
3. Create a temporary task through the authenticated gateway.
4. Verify type, input, prompt, and creation timestamp, then clean up.
