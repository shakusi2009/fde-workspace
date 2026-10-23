# TOS Private URL Signing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert a public Beijing TOS object URL into a one-hour private-network pre-signed GET URL from the task list.

**Architecture:** FastAPI validates and parses the public URL, then uses the official TOS SDK with server-only environment credentials and the `tos-cn-beijing.ivolces.com` endpoint. The authenticated Vue dialog calls the signing API and displays the result without exposing credentials.

**Tech Stack:** FastAPI, Volcengine TOS Python SDK, Pydantic, pytest, Vue 3, TypeScript, Element Plus.

---

### Task 1: Add configuration and SDK

**Files:**
- Modify: `.env`
- Modify: `ai-vlm/backend/app/config.py`
- Modify: `ai-vlm/backend/requirements.txt`

1. Add empty `TOS_ACCESS_KEY` and `TOS_SECRET_KEY`.
2. Add typed settings and a configured-state property.
3. Pin and install `tos==2.9.3`.

### Task 2: Add failing signing tests

**Files:**
- Create: `ai-vlm/backend/tests/test_tos_service.py`
- Modify: `ai-vlm/backend/tests/test_api.py`

1. Test virtual-host and path-style Beijing TOS URL parsing.
2. Reject non-HTTPS, non-Beijing, empty-object, and malformed URLs.
3. Test successful endpoint response and configuration/error mapping.

### Task 3: Implement signing backend

**Files:**
- Create: `ai-vlm/backend/app/services/tos_service.py`
- Modify: `ai-vlm/backend/app/schemas.py`
- Modify: `ai-vlm/backend/app/main.py`

1. Parse bucket and decoded object key safely.
2. Create `TosClientV2` with private endpoint and Beijing region.
3. Generate a GET pre-signed URL with 3600-second expiry.
4. Expose authenticated `POST /api/vlm/tos/private-sign`.

### Task 4: Implement the task-list dialog

**Files:**
- Modify: `src/services/vlm.ts`
- Modify: `src/views/vlm/VlmTaskListView.vue`
- Modify: `src/styles.css`

1. Add the TOS私有签名 button after refresh.
2. Add a 1024-character source URL field and explanatory caption.
3. Add the 生成 action and read-only conversion result.
4. Handle loading, validation, and backend errors.

### Task 5: Verify

1. Run backend tests, frontend production build, and diff checks.
2. Restart services.
3. Verify the dialog and empty-credential error.
4. Leave credentials empty for the user to fill.
