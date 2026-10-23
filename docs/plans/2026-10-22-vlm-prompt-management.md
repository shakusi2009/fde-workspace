# VLM Prompt Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a VLM prompt management module that displays every `vlm_prompt` record as a read-only card.

**Architecture:** Extend the existing VLM repository and service with a prompt list query ordered by latest update. Return a typed API model with `vlm_type` translated through `TASK_TYPE_LABELS`, then render a responsive Vue card grid with open and closed visual states.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, pytest, Vue 3, TypeScript, Element Plus, CSS.

---

### Task 1: Define and test the prompt API contract

**Files:**
- Modify: `ai-vlm/backend/tests/test_api.py`
- Modify: `ai-vlm/backend/app/schemas.py`

1. Add a test with open and closed prompt rows.
2. Assert field mapping, type localization, ordering contract, and datetime serialization.
3. Assert repository failures return HTTP 503.
4. Run `npm run vlm:test` and confirm the new tests fail before implementation.

### Task 2: Implement the RDS prompt query

**Files:**
- Modify: `ai-vlm/backend/app/repositories/vlm_task_repository.py`
- Modify: `ai-vlm/backend/app/services/vlm_service.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Select `id`, `title`, `vlm_type`, `content`, `is_closed`, `update_date`, and `create_by` from `vlm_prompt`.
2. Order by `update_date DESC, id DESC`.
3. Reuse `TASK_TYPE_LABELS` when mapping `vlm_type`.
4. Expose `GET /api/vlm/prompts` and translate repository failures to HTTP 503.
5. Run `npm run vlm:test`.

### Task 3: Add navigation and the prompt card page

**Files:**
- Modify: `src/router.ts`
- Modify: `src/layout/AppLayout.vue`
- Modify: `src/services/vlm.ts`
- Create: `src/views/vlm/VlmPromptManagementView.vue`
- Modify: `src/styles.css`

1. Add desktop and mobile navigation entries for `/vlm/prompts`.
2. Add the TypeScript API contract and fetch function.
3. Render responsive cards with title, type, content, status, update time, and creator.
4. Show blue open status, gray closed status, loading, refresh, error, and empty states.
5. Run `npm run build`.

### Task 4: Verify

1. Restart the services.
2. Verify `/api/vlm/prompts` against the live RDS table.
3. Verify route, navigation, empty state, and responsive layout in the browser.
