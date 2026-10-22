# VLM Task List Accuracy And Spacing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Display stored decimal accuracy values as percentages and make all task table rows evenly spaced.

**Architecture:** Keep the backend and API contract unchanged. Apply percentage conversion in one frontend formatter and scope fixed row height and padding styles to `.vlm-task-table`.

**Tech Stack:** Vue 3, TypeScript, Element Plus, CSS.

---

### Task 1: Correct accuracy display

**Files:**
- Modify: `src/views/vlm/VlmTaskListView.vue`

1. Add a formatter that returns `--` for null values.
2. Multiply numeric values by 100 and format with at most two decimal places.
3. Use the formatter in the accuracy column.

### Task 2: Normalize row spacing

**Files:**
- Modify: `src/styles.css`

1. Give VLM task table body rows a stable height.
2. Apply equal vertical cell padding without changing other tables.

### Task 3: Verify

1. Run `npm run build`.
2. Restart the services.
3. Verify real values such as `0.92` display as `92%`.
4. Inspect rendered row heights in the browser and confirm they are equal.
