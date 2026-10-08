import { test, expect } from '@playwright/test';

test.describe('Basic App Loading', () => {
  test('homepage loads and shows LinguaAI title', async ({ page }) => {
    await page.goto('http://localhost:5177/');
    await expect(page).toHaveTitle(/LinguaAI/i);
  });

  test('homepage has body content', async ({ page }) => {
    await page.goto('http://localhost:5177/');
    await page.waitForLoadState('networkidle');
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test('placement page is accessible', async ({ page }) => {
    await page.goto('http://localhost:5177/placement');
    await page.waitForLoadState('networkidle');
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test('404 for unknown routes', async ({ page }) => {
    const response = await page.goto('http://localhost:5177/nonexistent-page');
    // React Router should still serve the app (SPA fallback)
    expect(response.status()).toBeLessThan(500);
  });

  test('no console errors on homepage', async ({ page }) => {
    const errors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    await page.goto('http://localhost:5177/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Filter out known non-critical errors
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('net::ERR') && !e.includes('404')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
