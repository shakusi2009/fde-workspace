# VLM Task Edit And Delete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add task edit and soft-delete operations to the VLM task list.

**Architecture:** FastAPI validates editable business fields, while the RDS repository performs prompt/type validation and transactional updates. Deletes set `is_deleted=1`; existing list and overview queries already exclude deleted tasks. The Vue task dialog is reused for create and edit.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Add failing task mutation API tests

**File:** `ai-vlm/backend/tests/test_api.py`

1. Test update payload mapping and success.
2. Test update and delete not-found responses.
3. Test delete service invocation.

### Task 2: Implement backend update and soft delete

**Files:**
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Add an update model with task status 0/1/2.
2. Validate the prompt exists and matches task type.
3. Permit an existing closed prompt when it remains assigned.
4. Set end time on completion and clear it when reopened.
5. Soft-delete by setting `is_deleted=1`.

### Task 3: Add frontend task mutation services

**File:** `src/services/vlm.ts`

1. Add the update payload contract.
2. Add update and delete requests.

### Task 4: Add operations column and edit dialog

**File:** `src/views/vlm/VlmTaskListView.vue`

1. Add edit and delete icon actions.
2. Reuse the task form for create and edit.
3. Show task status during edit.
4. Confirm deletion and repair pagination after deleting the last page item.

### Task 5: Verify

1. Run backend tests, production build, and diff checks.
2. Restart services.
3. Create a temporary task, update it to completed, verify end time, soft-delete it, and verify it disappears.
