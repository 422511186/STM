import { test, expect } from '@playwright/test'

const BACKEND_URL = 'http://127.0.0.1:50051'
const DEFAULT_PASSWORD = 'admin'

test.describe('SSH Tunnel Manager E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage to ensure clean state
    await page.goto('/login')
    await page.evaluate(() => localStorage.clear())
  })

  test('1. Login page loads and shows password input', async ({ page }) => {
    await page.goto('/login')

    // Check page title
    await expect(page.getByText('SSH Tunnel Manager')).toBeVisible()

    // Check password input exists
    const passwordInput = page.getByPlaceholder('Enter your password')
    await expect(passwordInput).toBeVisible()
    await expect(passwordInput).toHaveAttribute('type', 'password')

    // Check login button exists
    const loginButton = page.getByRole('button', { name: 'Login' })
    await expect(loginButton).toBeVisible()
    await expect(loginButton).toBeDisabled() // Disabled when password is empty
  })

  test('2. Login with correct password redirects to tunnel list', async ({ page }) => {
    await page.goto('/login')

    // Enter correct password
    const passwordInput = page.getByPlaceholder('Enter your password')
    await passwordInput.fill(DEFAULT_PASSWORD)

    // Login button should be enabled now
    const loginButton = page.getByRole('button', { name: 'Login' })
    await expect(loginButton).toBeEnabled()

    // Submit login
    await loginButton.click()

    // Should redirect to tunnel list (/)
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('Tunnels')).toBeVisible()
  })

  test('3. Login with wrong password shows error', async ({ page }) => {
    await page.goto('/login')

    // Enter wrong password
    const passwordInput = page.getByPlaceholder('Enter your password')
    await passwordInput.fill('wrongpassword')

    // Submit login
    const loginButton = page.getByRole('button', { name: 'Login' })
    await loginButton.click()

    // Should show error message
    await expect(page.getByText('Invalid password')).toBeVisible()

    // Should still be on login page
    await expect(page).toHaveURL(/\/login/)
  })

  test('4. Tunnel list displays tunnels if configured', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('Enter your password').fill(DEFAULT_PASSWORD)
    await page.getByRole('button', { name: 'Login' }).click()

    // Wait for tunnel list to load
    await expect(page).toHaveURL(/\/$/)
    await page.waitForSelector('text=Tunnels', { timeout: 10000 })

    // Check for tunnel list content - either shows tunnels or "No tunnels configured"
    const tunnelContent = page.locator('body')
    const hasTunnels = await page.locator('[class*="TunnelCard"], [class*="tunnel"]').count() > 0
    const noTunnels = await page.getByText('No tunnels configured').isVisible()

    expect(hasTunnels || noTunnels).toBeTruthy()
  })

  test('5. Start/Stop buttons work if tunnels exist', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('Enter your password').fill(DEFAULT_PASSWORD)
    await page.getByRole('button', { name: 'Login' }).click()

    // Wait for tunnel list to load
    await expect(page).toHaveURL(/\/$/)
    await page.waitForSelector('text=Tunnels', { timeout: 10000 })

    // Look for Start or Stop buttons
    const startButton = page.locator('button[title="Start tunnel"]')
    const stopButton = page.locator('button[title="Stop tunnel"]')

    // Check if any tunnel buttons exist
    const startCount = await startButton.count()
    const stopCount = await stopButton.count()

    if (startCount === 0 && stopCount === 0) {
      // No tunnels - test passes as "no tunnels to test"
      test.skip('No tunnels available to test start/stop')
      return
    }

    // Test start button if present
    if (startCount > 0) {
      await startButton.first().click()
      // Should show connecting status
      await expect(page.getByText('Connecting')).toBeVisible({ timeout: 5000 })
    }

    // Test stop button if present
    if (stopCount > 0) {
      await stopButton.first().click()
      // Should update to inactive
      await page.waitForTimeout(2000)
    }
  })

  test('6. Config export triggers download', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('Enter your password').fill(DEFAULT_PASSWORD)
    await page.getByRole('button', { name: 'Login' }).click()

    // Wait for tunnel list
    await expect(page).toHaveURL(/\/$/)
    await page.waitForSelector('text=Tunnels', { timeout: 10000 })

    // Set up download promise before clicking
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 })

    // Click Export Config
    await page.getByText('Export Config').click()

    // Wait for download to start
    const download = await downloadPromise

    // Verify download filename
    expect(download.suggestedFilename()).toMatch(/config\.yaml/)
  })

  test('7. Config import shows confirmation dialog', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('Enter your password').fill(DEFAULT_PASSWORD)
    await page.getByRole('button', { name: 'Login' }).click()

    // Wait for tunnel list
    await expect(page).toHaveURL(/\/$/)
    await page.waitForSelector('text=Tunnels', { timeout: 10000 })

    // Click Import Config
    await page.getByText('Import Config').click()

    // Dialog should appear
    await expect(page.getByText('Import Configuration')).toBeVisible()
    await expect(page.getByText('This will replace your current configuration')).toBeVisible()

    // Cancel button should be present
    const cancelButton = page.getByRole('button', { name: 'Cancel' })
    await expect(cancelButton).toBeVisible()

    // Choose File button should be present
    const chooseFileButton = page.getByText('Choose File')
    await expect(chooseFileButton).toBeVisible()

    // Click cancel to close dialog
    await cancelButton.click()
    await expect(page.getByText('Import Configuration')).not.toBeVisible()
  })
})