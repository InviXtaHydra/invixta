import { defineConfig, devices } from '@playwright/test'

// Runs against the full Docker Compose stack (frontend + backend + PostgreSQL), see "Testing" in the README.
// E2E_REAL_LLM=1: the backend uses the real local model in Ollama, which needs more time per answer.
const realModel = Boolean(process.env.E2E_REAL_LLM)

export default defineConfig({
  testDir: './e2e',
  timeout: realModel ? 240_000 : 60_000,
  expect: { timeout: realModel ? 120_000 : 20_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
