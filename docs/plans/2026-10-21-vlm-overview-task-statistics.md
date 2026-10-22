# VLM Overview Task Statistics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Populate the VLM overview task total and seven-day task trend from non-deleted rows in `vlm_tasks_list`.

**Architecture:** Add one repository operation that returns the lifetime count and date-grouped counts for an explicit seven-day range. The service fills missing dates with zero and keeps the unfinished accuracy and token metrics unchanged.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, ECharts.

---

### Task 1: Add overview API coverage

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Mock the repository summary result with a lifetime total and sparse daily data.
2. Assert that the API returns seven ordered points, fills missing days with zero, and reports `data_status=ready`.
3. Assert repository failures return HTTP 503.
4. Run `npm run vlm:test` and confirm the new test fails before implementation.

### Task 2: Implement RDS aggregation

**Files:**
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Count rows from `vlm_tasks_list` where `COALESCE(is_deleted, 0) <> 1`.
2. Group the requested seven-day range by `DATE(create_time)` using inclusive start and exclusive end parameters.
3. Convert sparse grouped rows into seven chronological `TrendPoint` values.
4. Convert repository errors from the overview endpoint into HTTP 503.
5. Run `npm run vlm:test`.

### Task 3: Update overview state messaging

**Files:**
- Modify: `src/views/vlm/VlmOverviewView.vue`

1. Mark task statistics as connected while retaining pending copy for accuracy and token metrics.
2. Run `npm run build`.
3. Verify the task total and seven-day chart through the running application.

### Task 4: Final verification

1. Run `npm audit --omit=dev`.
2. Query `/api/vlm/overview` and compare its total with a direct read-only RDS count.
3. Verify the overview page in a browser and confirm no console or UI errors.
