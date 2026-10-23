# VLM Model Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SQLite-backed model ID management to the VLM overview page.

**Architecture:** The existing Node service owns the SQLite database and exposes authenticated CRUD endpoints. The Vue overview opens a model-list dialog with a single model ID data column and an operation column; create and edit use a focused form dialog.

**Tech Stack:** Express, better-sqlite3, Vue 3, TypeScript, Element Plus.

---

### Task 1: Create the SQLite table

**File:** `server/db.ts`

1. Create `vlm_models` with an internal primary key, unique non-empty `model_id`, and audit timestamps.
2. Verify table structure in `data/fde.sqlite`.

### Task 2: Add authenticated CRUD endpoints

**File:** `server/index.ts`

1. Add list, create, update, and delete routes.
2. Trim model IDs, enforce required and 255-character limits.
3. Return clear duplicate and not-found errors.

### Task 3: Add frontend service contracts

**File:** `src/services/vlm.ts`

1. Add the model record type.
2. Add CRUD API functions.

### Task 4: Build model management dialogs

**Files:**
- Modify: `src/views/vlm/VlmOverviewView.vue`
- Modify: `src/styles.css`

1. Add 模型管理 immediately before 刷新.
2. Add a model-list dialog with 模型 ID and operation columns.
3. Add create/edit form dialog and delete confirmation.
4. Handle loading, validation, duplicate errors, and responsive layout.

### Task 5: Verify

1. Run production build and diff checks.
2. Restart services to initialize the table.
3. Exercise authenticated create, list, update, and delete endpoints.
4. Verify temporary data is removed.
