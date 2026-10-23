const { test, expect } = require('@playwright/test')

test('car agent prototype works in both directions', async ({ page }) => {
  const consoleErrors = []
  const requestFailures = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('requestfailed', (request) => {
    requestFailures.push(`${request.method()} ${request.url()}`)
  })

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('http://127.0.0.1:3001/agents')

  if (page.url().includes('/login')) {
    const captcha = (await page.locator('.captcha-code span').textContent()).trim()
    await page.getByPlaceholder('请输入账号').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234!')
    await page.getByPlaceholder('4 位验证码').fill(captcha)
    await page.getByRole('button', { name: '验证并进入' }).click()
  }

  await expect(page).toHaveURL(/\/agents$/)
  await expect(page.getByRole('heading', { name: '车端Agent', exact: true })).toBeVisible()

  await page.getByPlaceholder('搜索姓名或 VIN 码').click()
  const ownerOption = page.locator('.el-select-dropdown__item:visible').first()
  await expect(ownerOption).toBeVisible()
  await ownerOption.click()
  await expect(page.locator('.vehicle-profile strong').first()).not.toHaveText('--')

  const modelInput = page.getByPlaceholder('选择模型 ID')
  if (!(await modelInput.inputValue())) {
    await modelInput.click()
    const modelOption = page.locator('.el-select-dropdown__item:visible').first()
    await expect(modelOption).toBeVisible()
    await modelOption.click()
  }

  const vehiclePrompt = page.getByPlaceholder(/输入车端任务/)
  await vehiclePrompt.fill('分析当前车辆状态并生成出行建议')
  await page.getByRole('button', { name: '发送至云端' }).click()
  await expect(page.getByText('协作完成', { exact: true })).toBeVisible({ timeout: 8000 })
  await expect(page.locator('.vehicle-panel .output-copy')).toContainText('演示结果')
  await expect(page.locator('.cloud-panel .output-copy')).toContainText('演示结果')
  await page.screenshot({ path: '/tmp/car-agent-desktop.png', fullPage: true })

  await page.getByRole('button', { name: '重置会话' }).click()
  await expect(page.getByText('等待指令', { exact: true })).toBeVisible()

  const cloudPrompt = page.getByPlaceholder(/输入云端任务/)
  await cloudPrompt.fill('向车辆下发下一次保养检查指令')
  await page.getByRole('button', { name: '下发至车端' }).click()
  await expect(page.getByText('协作完成', { exact: true })).toBeVisible({ timeout: 8000 })
  await expect(page.locator('.vehicle-panel .output-copy')).toContainText('演示结果')
  await expect(page.locator('.cloud-panel .output-copy')).toContainText('演示结果')

  await page.getByRole('button', { name: '重置会话' }).click()
  await vehiclePrompt.fill('验证重置是否取消延迟写入')
  await page.getByRole('button', { name: '发送至云端' }).click()
  await page.getByRole('button', { name: '重置会话' }).click()
  await page.waitForTimeout(1800)
  await expect(page.getByText('等待指令', { exact: true })).toBeVisible()
  await expect(page.locator('.vehicle-panel .output-copy')).toHaveText('等待车端 Agent 输出')
  await expect(page.locator('.cloud-panel .output-copy')).toHaveText('等待备车 Agent 输出')

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.mobile-flow')).toBeVisible()
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth)
  await page.screenshot({ path: '/tmp/car-agent-mobile.png', fullPage: true })

  expect(consoleErrors).toEqual([])
  expect(requestFailures).toEqual([])
})
