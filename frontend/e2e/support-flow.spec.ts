// End to end: browser → nginx → FastAPI → agent → tools → PostgreSQL, and back as a streamed answer.
// Needs the seeded demo data and the indexed sample documents (see README, "End-to-end tests").
import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'Password123!'

async function signIn(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login/)
  await page.goto('/dashboard') // the account and support pages
}

const nav = (page: Page, name: string) => page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name, exact: true })

async function ask(page: Page, question: string) {
  const input = page.getByRole('textbox', { name: 'Message' })
  await input.fill(question)
  await input.press('Enter')
}

test('customer asks about an order: the agent calls the order tool and answers from the database', async ({ page }) => {
  await signIn(page, 'emma.devries@example.com')

  // Read a shipped order and its tracking number from the orders page (data from PostgreSQL).
  await nav(page, 'Orders').click()
  await page.getByLabel('Filter by status').selectOption('shipped')
  await expect(page.locator('[aria-busy="false"]').getByRole('row').nth(1)).toContainText('Shipped')
  const firstOrder = page.getByRole('row').nth(1).getByRole('link')
  const orderLabel = (await firstOrder.textContent())!.trim() // "#10014"
  const orderNumber = orderLabel.slice(1)
  await firstOrder.click()
  const tracking = (await page.getByText('Tracking number').locator('xpath=following-sibling::dd').textContent())!.trim()

  // Ask the assistant about it.
  await nav(page, 'AI assistant').click()
  await ask(page, `Where is my order ${orderLabel}?`)

  const answer = page.getByRole('article').last()
  await expect(answer.getByText('Order database')).toBeVisible() // the tool ran…
  await expect(answer.getByText(`Order #${orderNumber}: shipped`)).toBeVisible() // …and found the order
  await expect(answer.getByText(/Answered in/)).toBeVisible()
  await expect(answer).toContainText(/shipped/i)
  await expect(answer).toContainText(tracking)

  // The conversation is stored: after a reload it's still there, with the tool call.
  await expect(page).toHaveURL(/\/chat\/\d+$/)
  await page.reload()
  await expect(page.getByRole('article').last().getByText(`Order #${orderNumber}: shipped`)).toBeVisible()
})

test('policy question: the agent searches the knowledge base and shows its sources', async ({ page }) => {
  await signIn(page, 'emma.devries@example.com')
  await nav(page, 'AI assistant').click()
  await page.getByRole('link', { name: 'New conversation' }).first().click()
  await ask(page, 'How many days do I have to return a product?')

  const answer = page.getByRole('article').last()
  await expect(answer.getByText('Knowledge base')).toBeVisible()
  await expect(answer.getByText(/Answered in/)).toBeVisible()
  await expect(answer.getByText('Sources')).toBeVisible()
  await expect(answer.getByText('Return Policy.pdf').first()).toBeVisible()
  await expect(answer).toContainText('30 days')
})

test("a customer can't see another customer's order through the assistant", async ({ page }) => {
  await signIn(page, 'emma.devries@example.com')
  await page.goto('/orders')
  await expect(page.locator('[aria-busy="false"]')).toBeVisible()
  const own = new Set((await page.getByRole('row').getByRole('link').allTextContents()).map((t) => t.trim().slice(1)))
  const someoneElses = Array.from({ length: 20 }, (_, i) => String(10001 + i)).find((n) => !own.has(n))!

  await page.goto(`/orders/${someoneElses}`)
  await expect(page.getByRole('alert')).toContainText(/not found/i) // the REST API refuses…

  await nav(page, 'AI assistant').click()
  await page.getByRole('link', { name: 'New conversation' }).first().click()
  await ask(page, `What is the status of order ${someoneElses}?`)
  const answer = page.getByRole('article').last()
  await expect(answer.getByText(/Answered in/)).toBeVisible()
  await expect(answer).toContainText(/not found|couldn't find|can't find|could not find/i) // …and so does the agent's tool
})

test('admin sees the knowledge base and the metrics', async ({ page }) => {
  await signIn(page, 'admin@kopbal.shop')
  await nav(page, 'Knowledge base').click()
  await expect(page.getByText('Return Policy.pdf')).toBeVisible()
  await expect(page.getByText(/\d+ documents, \d+ chunks/)).toBeVisible()

  await nav(page, 'Metrics').click()
  await expect(page.getByText('Questions answered', { exact: true })).toBeVisible()
  await expect(page.getByText('Knowledge-base searches')).toBeVisible()
})

test('support agent changes the status of a ticket', async ({ page }) => {
  await signIn(page, 'agent@kopbal.shop')
  await page.goto('/tickets?status=open')
  await expect(page.locator('[aria-busy="false"]')).toBeVisible()
  await page.getByRole('main').getByRole('listitem').getByRole('link').first().click()
  await expect(page).toHaveURL(/\/tickets\/\d+$/)
  await page.getByLabel('Status', { exact: true }).selectOption('in_progress')
  await expect(page.getByRole('status').filter({ hasText: /Ticket #\d+ updated/ })).toBeVisible()
  await expect(page.getByRole('main').locator('header').getByText('In progress')).toBeVisible()
})
