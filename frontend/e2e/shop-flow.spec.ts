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

test('the assistant offers a cancellation, and only the customer can confirm it', async ({ page }) => {
  // Buy something to cancel.
  await page.goto('/login')
  await page.getByLabel('Email').fill('emma.devries@example.com')
  await page.getByLabel('Password').fill('Password123!')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login/)
  await page.goto('/product/haven-rovers-away-26-27')
  await page.locator('input[name="size"]:not([disabled])').first().check({ force: true })
  await page.getByRole('button', { name: /Add to cart/ }).click()
  await page.getByRole('dialog').getByRole('link', { name: 'Checkout' }).click()
  await page.getByLabel('Street and house number').fill('Lindelaan 12')
  await page.getByLabel('Postcode').fill('3511 AB')
  await page.getByLabel('City').fill('Utrecht')
  await page.getByRole('button', { name: /Place order/ }).click()
  await page.getByRole('button', { name: 'Approve payment' }).click()
  await expect(page.getByText('Processing', { exact: true })).toBeVisible()
  const orderNumber = page.url().match(/orders\/(\d+)/)![1]

  await page.goto('/chat')
  await page.getByRole('textbox', { name: 'Message' }).fill(`Please cancel order ${orderNumber}`)
  await page.keyboard.press('Enter')
  const answer = page.getByRole('article').last()
  await expect(answer.getByText(`Order #${orderNumber} can be cancelled: waiting for your confirmation`)).toBeVisible()
  await expect(answer.getByText(/Answered in/)).toBeVisible()
  await expect(page).toHaveURL(/\/chat\/\d+$/)
  const conversationUrl = page.url()

  // Nothing happened yet: the agent can't cancel by itself.
  await page.goto(`/orders/${orderNumber}`)
  await expect(page.getByText('Processing', { exact: true })).toBeVisible()

  // The stored conversation still offers the button.
  await page.goto(conversationUrl)
  await page.getByRole('button', { name: `Cancel order #${orderNumber}` }).click()
  await page.getByRole('button', { name: 'Yes, cancel it' }).click()
  await expect(page.getByText(`Order #${orderNumber} is cancelled.`)).toBeVisible()
  await page.goto(`/orders/${orderNumber}`)
  await expect(page.getByText('Cancelled', { exact: true }).first()).toBeVisible()
})

test('an admin changes the stock of a size and the shop shows it', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('admin@kopbal.shop')
  await page.getByLabel('Password').fill('Password123!')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login/)
  await page.goto('/admin/products?q=Maasoever Scarf')
  const stock = page.getByLabel('Stock of Maasoever SC Scarf in size One size')
  await stock.fill('0')
  await stock.press('Enter')
  await expect(page.getByRole('status').filter({ hasText: 'One size: 0 in stock' })).toBeVisible()

  await page.goto('/product/maasoever-sc-scarf')
  await expect(page.getByRole('button', { name: 'Sold out' })).toBeDisabled()

  await page.goto('/admin/products?q=Maasoever Scarf')
  await page.getByLabel('Stock of Maasoever SC Scarf in size One size').fill('25')
  await page.getByLabel('Stock of Maasoever SC Scarf in size One size').press('Enter')
  await expect(page.getByRole('status').filter({ hasText: 'One size: 25 in stock' })).toBeVisible()
})
