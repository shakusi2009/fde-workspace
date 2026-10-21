import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import bcrypt from 'bcryptjs'
import Database from 'better-sqlite3'

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(currentDir, '..')
const dataDir = path.join(projectRoot, 'data')

fs.mkdirSync(dataDir, { recursive: true })

export const db = new Database(path.join(dataDir, 'fde.sqlite'))
db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

db.exec(`
  CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    permissions TEXT NOT NULL DEFAULT '[]',
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
  );
`)

const roleCount = db.prepare('SELECT COUNT(*) AS count FROM roles').get() as { count: number }

if (roleCount.count === 0) {
  const insertRole = db.prepare(`
    INSERT INTO roles (name, description, permissions, is_system)
    VALUES (?, ?, ?, ?)
  `)
  const seedRoles = db.transaction(() => {
    insertRole.run('超级管理员', '拥有平台全部功能和数据权限', JSON.stringify(['account_center', 'agent_center']), 1)
    insertRole.run('智能体开发者', '可访问智能体开发相关功能', JSON.stringify(['agent_center']), 0)
    insertRole.run('业务观察员', '可浏览智驾业务模块', JSON.stringify([]), 0)
  })
  seedRoles()
}

const adminRole = db.prepare('SELECT id FROM roles WHERE name = ?').get('超级管理员') as { id: number }
const adminExists = db.prepare('SELECT id FROM users WHERE username = ?').get('admin')

if (!adminExists) {
  db.prepare(`
    INSERT INTO users (username, display_name, email, password_hash, role_id, status)
    VALUES (?, ?, ?, ?, ?, 'active')
  `).run('admin', '系统管理员', 'admin@stephen.local', bcrypt.hashSync('Test1234!', 10), adminRole.id)
}

export function parsePermissions(value: string): string[] {
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function mapRole(row: Record<string, unknown>) {
  return {
    ...row,
    permissions: parsePermissions(String(row.permissions ?? '[]')),
    is_system: Boolean(row.is_system),
  }
}
