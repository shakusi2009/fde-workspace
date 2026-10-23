# VLM Task Item List Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make each parent task ID open a paginated list of its `vlm_tasks_item` records.

**Architecture:** FastAPI exposes a nested read endpoint keyed by parent task ID. The repository verifies the active parent task, then counts and selects child rows with a fixed page size. Vue adds a detail route and renders every child-table field in a horizontally scrollable table.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Add task-item API tests

**File:** `ai-vlm/backend/tests/test_api.py`

1. Test all database fields map to the response contract.
2. Test fixed 10-row pagination.
3. Test parent-task not-found and repository failures.

### Task 2: Implement task-item query

**Files:**
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Verify the parent task exists and is not deleted.
2. Count and query `vlm_tasks_item` by `task_id`.
3. Return all ten item fields ordered by descending item ID.
4. Expose `GET /api/vlm/tasks/{task_id}/items?page=1`.

### Task 3: Add frontend route and service

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/router.ts`
- Modify: `src/layout/AppLayout.vue`

1. Add item/page types and request function.
2. Add `/vlm/tasks/:taskId/items`.
3. Keep the parent navigation active for child routes.
4. Rename the parent navigation/page label to 打标任务.

### Task 4: Build the item-list page

**Files:**
- Create: `src/views/vlm/VlmTaskItemListView.vue`
- Modify: `src/views/vlm/VlmTaskListView.vue`
- Modify: `src/styles.css`

1. Make task sequence values clickable.
2. Add a return action, task context, refresh, and pagination.
3. Display ID, task ID, model ID, input, token fields, status, and output log.
4. Add empty, loading, error, and responsive states.

### Task 5: Verify

1. Run backend tests, production build, and diff checks.
2. Restart services.
3. Verify the real API returns an empty page for an existing task.
4. Verify an unknown task returns 404.
