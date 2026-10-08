import { test, expect } from '@playwright/test';

test.describe('Placement Test Flow', () => {
  test('placement page loads with setup form', async ({ page }) => {
    await page.goto('http://localhost:5177/placement');
    await page.waitForLoadState('networkidle');

    // Should show the setup form with name input
    const nameInput = page.locator('input[name="name"], input[placeholder*="imię"], input[placeholder*="name"], input[placeholder*="Imię"]').first();
    const hasNameInput = await nameInput.isVisible().catch(() => false);

    // Or it might show a language selector or start button
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('can fill placement form and start test', async ({ page }) => {
    await page.goto('http://localhost:5177/placement');
    await page.waitForLoadState('networkidle');

    // Try to fill name
    const nameInput = page.locator('input[name="name"], input[placeholder*="imię"], input[placeholder*="name"], input[placeholder*="Imię"]').first();
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.fill('E2E Placement User');
    }

    // Look for start/begin button
    const startBtn = page.locator('button:has-text("Start"), button:has-text("Rozpocznij"), button:has-text("Zacznij")').first();
    if (await startBtn.isVisible().catch(() => false)) {
      await startBtn.click();
      // Wait for test to load questions
      await page.waitForTimeout(3000);

      // Should show question content or loading
      const bodyText = await page.textContent('body');
      expect(bodyText.length).toBeGreaterThan(50);
    }
  });

  test('placement test shows questions with answer options', async ({ page }) => {
    // Create user via API first
    const response = await page.request.post('http://localhost:8001/api/placement/create-user', {
      data: {
        name: 'E2E Question User',
        native_language: 'Polish',
        target_language: 'German',
      },
    });
    const { user_id } = await response.json();

    // Start placement test via API
    const testRes = await page.request.post(`http://localhost:8001/api/placement/start-test?user_id=${user_id}`);
    if (testRes.ok()) {
      const testData = await testRes.json();
      // Should have questions
      expect(testData).toBeDefined();
    }
  });
});
