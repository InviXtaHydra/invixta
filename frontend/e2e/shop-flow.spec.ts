// The shop end to end: browse → print a shirt → cart → sign in → checkout → TestPay → order → ask the bot.
import { expect, test } from '@playwright/test'

test('a guest buys a printed shirt, pays with TestPay and asks the assistant about the order', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('navigation', { name: 'Shop' }).getByRole('link', { name: 'Home shirts' }).click()
  await expect(page.getByRole('heading', { name: 'Home shirts' })).toBeVisible()
  await page.getByRole('link', { name: 'FC Dijkstad Home Shirt 26/27' }).click()

  // Choose a size that is in stock and print a name and number.
  const size = page.locator('input[name="size"]:not([disabled])').first()
  await size.check({ force: true })
  await page.getByLabel('Name').fill('kopbal')
  await page.getByLabel('Number').fill('9')
  await expect(page.getByRole('img', { name: /back/ })).toContainText('KOPBAL')
  await page.getByRole('button', { name: /Add to cart, €84\.95/ }).click()

  const drawer = page.getByRole('dialog', { name: /Your cart/ })
  await expect(drawer).toContainText('printed: KOPBAL 9')
  await drawer.getByRole('link', { name: 'Checkout' }).click()

  // Checkout needs an account: sign in, and the guest cart comes along.
  await page.getByLabel('Email').fill('emma.devries@example.com')
  await page.getByLabel('Password').fill('Password123!')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(/\/checkout$/)
  await expect(page.getByText('KOPBAL 9')).toBeVisible()

  await page.getByLabel('Street and house number').fill('Lindelaan 12')
  await page.getByLabel('Postcode').fill('3511 AB')
  await page.getByLabel('City').fill('Utrecht')
  await page.getByRole('radio', { name: /iDEAL/ }).check()
  await page.getByRole('button', { name: /Place order/ }).click()

  // The simulated payment provider.
  await expect(page.getByText('TestPay')).toBeVisible()
  await page.getByRole('button', { name: 'Approve payment' }).click()
  await expect(page.getByText('Thanks for your order!')).toBeVisible()
  await expect(page.getByText('Processing', { exact: true })).toBeVisible()
  await expect(page.getByText('printed: KOPBAL 9')).toBeVisible()
  const orderNumber = page.url().match(/orders\/(\d+)/)![1]

  // Ask the support assistant in the shop's chat widget.
  await page.goto('/')
  await page.getByRole('button', { name: /Questions\? Ask us|Open the support chat/ }).click()
  await page.getByRole('textbox', { name: 'Message' }).fill(`What is the status of order ${orderNumber}?`)
  await page.keyboard.press('Enter')
  const answer = page.getByRole('region', { name: 'Support chat' }).getByRole('article').last()
  await expect(answer.getByText('Order database')).toBeVisible()
  await expect(answer.getByText(`Order #${orderNumber}: processing`)).toBeVisible()
  await expect(answer.getByText(/Answered in/)).toBeVisible()
})

test('the catalogue filters by club and size', async ({ page }) => {
  await page.goto('/shop?team=polder-united')
  await expect(page.getByRole('heading', { level: 1, name: 'Polder United' })).toBeVisible()
  const cards = page.getByRole('article')
  await expect(cards.first()).toBeVisible()
  for (const name of await cards.getByRole('link').allTextContents()) expect(name).toContain('Polder United')
  await page.getByRole('button', { name: 'XL', exact: true }).click()
  await expect(page).toHaveURL(/size=XL/)
})
