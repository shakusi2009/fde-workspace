module.exports = {
  testDir: __dirname,
  testMatch: 'car-agent.e2e.spec.js',
  timeout: 30000,
  use: {
    headless: true,
  },
}
