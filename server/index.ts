import crypto from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import bcrypt from 'bcryptjs'
import cors from 'cors'
import express, { type NextFunction, type Request, type Response } from 'express'
import { db, mapRole, parsePermissions } from './db.js'

type SessionUser = {
  id: number
  username: string
  display_name: string
  role_id: number
  role_name: string
  permissions: string[]
}

declare global {
  namespace Express {
    interface Request {
      user?: SessionUser
    }
  }
}

const app = express()
const port = Number(process.env.PORT ?? 3001)
const sessions = new Map<string, SessionUser>()
const captchas = new Map<string, { code: string; expiresAt: number }>()

app.use(cors())
app.use(express.json())
app.use('/api/vlm', (req, res, next) => {
  if (req.method === 'GET') {
    next()
    return
  }
  auth(req, res, next)
}, async (req, res) => {
  try {
    if (
      req.method === 'POST'
      && /^\/tasks\/\d+\/executions$/.test(req.path)
    ) {
      const modelId = typeof req.body?.model_id === 'string'
        ? req.body.model_id.trim()
        : ''
      const model = modelId
        ? db.prepare('SELECT id FROM vlm_models WHERE model_id = ?').get(modelId)
        : undefined
      if (!model) {
        res.status(400).json({ message: '请选择模型管理中存在的模型 ID' })
        return
      }
    }

    const target = new URL(`/api/vlm${req.url}`, 'http://127.0.0.1:8001')
    const payload = req.method === 'POST' && req.path === '/prompts'
      ? { ...req.body, create_by: req.user?.username }
      : req.body
    const response = await fetch(target, {
      method: req.method,
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
      },
      body: req.method === 'GET' || req.method === 'HEAD'
        ? undefined
        : JSON.stringify(payload),
    })
    const body = await response.text()
    res.status(response.status)
    res.type(response.headers.get('content-type') ?? 'application/json')
    res.send(body)
  } catch {
    res.status(503).json({ message: 'VLM 服务暂不可用，请确认 Python 服务已启动' })
  }
})

function getSessionUser(userId: number): SessionUser | undefined {
  const row = db.prepare(`
    SELECT u.id, u.username, u.display_name, u.role_id, r.name AS role_name, r.permissions
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE u.id = ? AND u.status = 'active'
  `).get(userId) as (Omit<SessionUser, 'permissions'> & { permissions: string }) | undefined

  if (!row) return undefined
  return { ...row, permissions: parsePermissions(row.permissions) }
}

function auth(req: Request, res: Response, next: NextFunction) {
  const token = req.header('authorization')?.replace(/^Bearer\s+/i, '')
  const user = token ? sessions.get(token) : undefined
  if (!user) {
    res.status(401).json({ message: '登录状态已失效，请重新登录' })
    return
  }
  const latestUser = getSessionUser(user.id)
  if (!latestUser) {
    sessions.delete(token!)
    res.status(401).json({ message: '当前账号已停用' })
    return
  }
  req.user = latestUser
  next()
}

function requirePermission(permission: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user?.permissions.includes(permission)) {
      res.status(403).json({ message: '当前角色无此模块访问权限' })
      return
    }
    next()
  }
}

app.get('/api/auth/captcha', (_req, res) => {
  const id = crypto.randomUUID()
  const code = String(Math.floor(1000 + Math.random() * 9000))
  captchas.set(id, { code, expiresAt: Date.now() + 5 * 60 * 1000 })
  res.json({ id, code })
})

app.post('/api/auth/login', (req, res) => {
  const { username, password, captchaId, captchaCode } = req.body ?? {}
  const captcha = captchas.get(String(captchaId))
  captchas.delete(String(captchaId))

  if (!captcha || captcha.expiresAt < Date.now() || captcha.code !== String(captchaCode).trim()) {
    res.status(400).json({ message: '验证码错误或已过期，请重新输入' })
    return
  }

  const row = db.prepare(`
    SELECT u.*, r.name AS role_name, r.permissions
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE u.username = ?
  `).get(String(username).trim()) as Record<string, unknown> | undefined

  if (!row || !bcrypt.compareSync(String(password), String(row.password_hash))) {
    res.status(401).json({ message: '账号或密码错误，请重新输入' })
    return
  }
  if (row.status !== 'active') {
    res.status(403).json({ message: '账号已停用，请联系管理员' })
    return
  }

  const token = crypto.randomBytes(32).toString('hex')
  const user = getSessionUser(Number(row.id))!
  sessions.set(token, user)
  res.json({ token, user })
})

app.post('/api/auth/logout', auth, (req, res) => {
  const token = req.header('authorization')?.replace(/^Bearer\s+/i, '')
  if (token) sessions.delete(token)
  res.json({ message: '已退出登录' })
})

app.get('/api/auth/me', auth, (req, res) => {
  res.json({ user: req.user })
})

app.get('/api/users', auth, requirePermission('account_center'), (_req, res) => {
  const users = db.prepare(`
    SELECT u.id, u.username, u.display_name, u.email, u.role_id, u.status,
           u.created_at, u.updated_at, r.name AS role_name
    FROM users u
    JOIN roles r ON r.id = u.role_id
    ORDER BY u.id ASC
  `).all()
  res.json(users)
})

app.post('/api/users', auth, requirePermission('account_center'), (req, res) => {
  const { username, display_name, email = '', password, role_id, status = 'active' } = req.body ?? {}
  if (!username || !display_name || !password || !role_id) {
    res.status(400).json({ message: '请完整填写用户信息' })
    return
  }
  try {
    const result = db.prepare(`
      INSERT INTO users (username, display_name, email, password_hash, role_id, status)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      String(username).trim(),
      String(display_name).trim(),
      String(email).trim(),
      bcrypt.hashSync(String(password), 10),
      Number(role_id),
      status === 'disabled' ? 'disabled' : 'active',
    )
    res.status(201).json({ id: result.lastInsertRowid, message: '用户创建成功' })
  } catch (error) {
    const message = error instanceof Error && error.message.includes('UNIQUE')
      ? '账号已存在'
      : '用户创建失败，请检查角色是否有效'
    res.status(400).json({ message })
  }
})

app.put('/api/users/:id', auth, requirePermission('account_center'), (req, res) => {
  const id = Number(req.params.id)
  const { display_name, email = '', password, role_id, status } = req.body ?? {}
  if (id === req.user?.id && status === 'disabled') {
    res.status(400).json({ message: '不能停用当前登录账号' })
    return
  }

  const updates = ['display_name = ?', 'email = ?', 'role_id = ?', 'status = ?', 'updated_at = CURRENT_TIMESTAMP']
  const values: unknown[] = [String(display_name).trim(), String(email).trim(), Number(role_id), status]
  if (password) {
    updates.splice(4, 0, 'password_hash = ?')
    values.push(bcrypt.hashSync(String(password), 10))
  }
  values.push(id)

  try {
    const result = db.prepare(`UPDATE users SET ${updates.join(', ')} WHERE id = ?`).run(...values)
    if (!result.changes) {
      res.status(404).json({ message: '用户不存在' })
      return
    }
    res.json({ message: '用户信息已更新' })
  } catch {
    res.status(400).json({ message: '用户更新失败，请检查输入' })
  }
})

app.delete('/api/users/:id', auth, requirePermission('account_center'), (req, res) => {
  const id = Number(req.params.id)
  if (id === req.user?.id) {
    res.status(400).json({ message: '不能删除当前登录账号' })
    return
  }
  const user = db.prepare('SELECT username FROM users WHERE id = ?').get(id) as { username: string } | undefined
  if (user?.username === 'admin') {
    res.status(400).json({ message: '超级管理员账号不可删除' })
    return
  }
  const result = db.prepare('DELETE FROM users WHERE id = ?').run(id)
  if (!result.changes) {
    res.status(404).json({ message: '用户不存在' })
    return
  }
  res.json({ message: '用户已删除' })
})

app.get('/api/roles', auth, requirePermission('account_center'), (_req, res) => {
  const roles = db.prepare(`
    SELECT r.*, COUNT(u.id) AS user_count
    FROM roles r
    LEFT JOIN users u ON u.role_id = r.id
    GROUP BY r.id
    ORDER BY r.id ASC
  `).all() as Record<string, unknown>[]
  res.json(roles.map(mapRole))
})

app.post('/api/roles', auth, requirePermission('account_center'), (req, res) => {
  const { name, description = '', permissions = [] } = req.body ?? {}
  if (!name) {
    res.status(400).json({ message: '请输入角色名称' })
    return
  }
  try {
    const result = db.prepare(`
      INSERT INTO roles (name, description, permissions)
      VALUES (?, ?, ?)
    `).run(String(name).trim(), String(description).trim(), JSON.stringify(permissions))
    res.status(201).json({ id: result.lastInsertRowid, message: '角色创建成功' })
  } catch {
    res.status(400).json({ message: '角色名称已存在' })
  }
})

app.put('/api/roles/:id', auth, requirePermission('account_center'), (req, res) => {
  const id = Number(req.params.id)
  const { name, description = '', permissions = [] } = req.body ?? {}
  const role = db.prepare('SELECT is_system FROM roles WHERE id = ?').get(id) as { is_system: number } | undefined
  if (!role) {
    res.status(404).json({ message: '角色不存在' })
    return
  }
  const effectivePermissions = role.is_system ? ['account_center', 'agent_center'] : permissions
  try {
    db.prepare(`
      UPDATE roles
      SET name = ?, description = ?, permissions = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).run(String(name).trim(), String(description).trim(), JSON.stringify(effectivePermissions), id)
    res.json({ message: '角色信息已更新' })
  } catch {
    res.status(400).json({ message: '角色名称已存在' })
  }
})

app.delete('/api/roles/:id', auth, requirePermission('account_center'), (req, res) => {
  const id = Number(req.params.id)
  const role = db.prepare(`
    SELECT r.is_system, COUNT(u.id) AS user_count
    FROM roles r LEFT JOIN users u ON u.role_id = r.id
    WHERE r.id = ? GROUP BY r.id
  `).get(id) as { is_system: number; user_count: number } | undefined
  if (!role) {
    res.status(404).json({ message: '角色不存在' })
    return
  }
  if (role.is_system) {
    res.status(400).json({ message: '系统角色不可删除' })
    return
  }
  if (role.user_count > 0) {
    res.status(400).json({ message: '该角色仍有关联用户，暂不可删除' })
    return
  }
  db.prepare('DELETE FROM roles WHERE id = ?').run(id)
  res.json({ message: '角色已删除' })
})

function parseModelId(value: unknown): { modelId?: string; error?: string } {
  const modelId = typeof value === 'string' ? value.trim() : ''
  if (!modelId) return { error: '请输入模型 ID' }
  if (modelId.length > 255) return { error: '模型 ID 不能超过 255 个字符' }
  return { modelId }
}

app.get('/api/vlm-models', auth, (_req, res) => {
  const models = db.prepare(`
    SELECT id, model_id, created_at, updated_at
    FROM vlm_models
    ORDER BY id ASC
  `).all()
  res.json(models)
})

app.post('/api/vlm-models', auth, (req, res) => {
  const parsed = parseModelId(req.body?.model_id)
  if (!parsed.modelId) {
    res.status(400).json({ message: parsed.error })
    return
  }

  try {
    const result = db.prepare(`
      INSERT INTO vlm_models (model_id)
      VALUES (?)
    `).run(parsed.modelId)
    res.status(201).json({
      id: Number(result.lastInsertRowid),
      message: '模型创建成功',
    })
  } catch (error) {
    const message = error instanceof Error && error.message.includes('UNIQUE')
      ? '模型 ID 已存在'
      : '模型创建失败'
    res.status(400).json({ message })
  }
})

app.put('/api/vlm-models/:id', auth, (req, res) => {
  const id = Number(req.params.id)
  const parsed = parseModelId(req.body?.model_id)
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ message: '模型记录 ID 无效' })
    return
  }
  if (!parsed.modelId) {
    res.status(400).json({ message: parsed.error })
    return
  }

  try {
    const result = db.prepare(`
      UPDATE vlm_models
      SET model_id = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).run(parsed.modelId, id)
    if (!result.changes) {
      res.status(404).json({ message: '模型不存在' })
      return
    }
    res.json({ message: '模型更新成功' })
  } catch (error) {
    const message = error instanceof Error && error.message.includes('UNIQUE')
      ? '模型 ID 已存在'
      : '模型更新失败'
    res.status(400).json({ message })
  }
})

app.delete('/api/vlm-models/:id', auth, (req, res) => {
  const id = Number(req.params.id)
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ message: '模型记录 ID 无效' })
    return
  }

  const result = db.prepare('DELETE FROM vlm_models WHERE id = ?').run(id)
  if (!result.changes) {
    res.status(404).json({ message: '模型不存在' })
    return
  }
  res.json({ message: '模型已删除' })
})

app.get('/api/overview', auth, (_req, res) => {
  const users = db.prepare('SELECT COUNT(*) AS total, SUM(status = ?) AS active FROM users').get('active')
  const roles = db.prepare('SELECT COUNT(*) AS total FROM roles').get()
  res.json({ users, roles, services: { online: 2, total: 2 } })
})

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.resolve(currentDir, '../dist')
app.use(express.static(distDir))
app.get('/{*path}', (_req, res) => res.sendFile(path.join(distDir, 'index.html')))

app.use((error: unknown, _req: Request, res: Response, _next: NextFunction) => {
  console.error(error)
  res.status(500).json({ message: '服务暂时不可用，请稍后重试' })
})

app.listen(port, () => {
  console.log(`FDE API listening on http://localhost:${port}`)
})
