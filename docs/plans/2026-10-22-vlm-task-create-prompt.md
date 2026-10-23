# VLM Task Prompt Association And Creation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Associate VLM tasks with prompt templates, display the prompt title, and support creating tasks.

**Architecture:** Add a nullable indexed foreign key from `vlm_tasks_list.prompt_id` to `vlm_prompt.id` so existing tasks remain valid. New tasks require an open prompt; the backend derives `vlm_type` from that prompt and initializes task runtime fields. The Vue task page loads prompts for a creation dialog and refreshes the paginated table after creation.

**Tech Stack:** MySQL RDS, FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Migrate the RDS schema

**Files:** RDS tables `vlm_tasks_list`, `vlm_prompt`

1. Add nullable `prompt_id INT` after `id`.
2. Add index `idx_vlm_tasks_prompt_id`.
3. Add foreign key `fk_vlm_tasks_prompt` with `ON DELETE RESTRICT`.
4. Verify the resulting table definition and preserve existing rows.

### Task 2: Add failing API tests

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Extend task list fixtures with prompt ID and title.
2. Test task creation derives type from an open prompt.
3. Test closed or missing prompts return a validation error.

### Task 3: Implement backend task creation

**Files:**
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Left join prompt titles in the paginated task query.
2. Add create payload and response fields.
3. Read and validate the selected prompt in the same transaction.
4. Insert a task with derived type, current creation time, zero metrics, and status 0.
5. Expose authenticated `POST /api/vlm/tasks`.

### Task 4: Implement the task creation UI

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmTaskListView.vue`
- Modify: `src/styles.css`

1. Add the prompt title column after sequence.
2. Add the 新增 button and a validated creation dialog.
3. List only open prompt templates.
4. Submit prompt ID and optional remarks, then refresh page one.

### Task 5: Verify

1. Run backend tests, frontend production build, and diff checks.
2. Restart services.
3. Create a temporary task through the UI and verify the prompt title.
4. Remove only the temporary task directly from RDS and confirm no residue.
