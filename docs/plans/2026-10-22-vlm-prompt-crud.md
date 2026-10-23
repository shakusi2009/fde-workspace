# VLM Prompt CRUD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add create, edit, and delete workflows to VLM prompt management.

**Architecture:** The Node gateway authenticates VLM write requests and injects the current username for prompt creation. FastAPI validates payloads and delegates parameterized transactional writes to the existing RDS repository; Vue uses one dialog for create/edit and a confirmed delete action.

**Tech Stack:** Express, FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Add backend mutation tests

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Test POST payload validation and successful creation.
2. Test PUT update and DELETE removal.
3. Test missing records return 404 and repository errors return 503.
4. Run `npm run vlm:test` and confirm failures before implementation.

### Task 2: Implement transactional RDS mutations

**Files:**
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Add validated create and update models.
2. Insert with database-generated create/update timestamps.
3. Update editable fields and refresh `update_date`.
4. Delete by ID and distinguish not-found records.
5. Add POST, PUT, and DELETE routes with correct status codes.

### Task 3: Enable authenticated gateway writes

**Files:**
- Modify: `server/index.ts`
- Modify: `src/api.ts`

1. Parse JSON before the VLM proxy.
2. Keep GET behavior unchanged.
3. Authenticate POST, PUT, and DELETE requests.
4. Inject `create_by` from the authenticated username for POST.
5. Forward method, JSON body, and backend error details.

### Task 4: Add frontend CRUD controls

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmPromptManagementView.vue`
- Modify: `src/styles.css`

1. Add create, update, and delete service functions.
2. Add the 新增 button and shared create/edit dialog.
3. Add icon-only edit/delete controls with tooltips.
4. Add validation, save loading state, success/error messages, and delete confirmation.

### Task 5: Verify end to end

1. Run backend tests, production build, dependency audit, and diff checks.
2. Restart services.
3. Create, edit, and delete a temporary prompt through the UI.
4. Confirm the RDS table returns to its original state.
