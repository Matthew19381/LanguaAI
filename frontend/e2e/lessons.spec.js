import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001';

test.describe('Lessons', () => {
  let userId;

  test.beforeAll(async ({ request }) => {
    const response = await request.post(`${API}/api/placement/create-user`, {
      data: {
        name: 'E2E Lesson User',
        native_language: 'Polish',
        target_language: 'German',
      },
    });
    const body = await response.json();
    userId = body.user_id;
  });

  test('lesson page loads for authenticated user', async ({ page }) => {
    await page.goto(`http://localhost:5177/lesson?userId=${userId}`);
    await page.waitForLoadState('networkidle');

    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test('can request new lesson generation', async ({ page }) => {
    await page.goto(`http://localhost:5177/lesson?userId=${userId}`);
    await page.waitForLoadState('networkidle');

    const genBtn = page.locator(
      'button:has-text("Generuj"), button:has-text("Generate"), button:has-text("Nowa lekcja"), button:has-text("Następna")'
    ).first();

    if (await genBtn.isVisible().catch(() => false)) {
      await genBtn.click();
      await page.waitForTimeout(5000);
      const bodyText = await page.textContent('body');
      expect(bodyText.length).toBeGreaterThan(50);
    }
  });

  test('lesson list returns lessons object', async ({ request }) => {
    const response = await request.get(`${API}/api/lessons/list/${userId}`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body).toHaveProperty('lessons');
    expect(Array.isArray(body.lessons)).toBeTruthy();
  });

  test('lesson list for non-existent user returns 404', async ({ request }) => {
    const response = await request.get(`${API}/api/lessons/list/999999`);
    expect(response.status()).toBe(404);
  });
});
