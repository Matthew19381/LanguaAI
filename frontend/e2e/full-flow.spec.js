import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001';

test.describe('Full User Flow', () => {
  test('complete user journey: create → home → navigate', async ({ page, request }) => {
    const userRes = await request.post(`${API}/api/placement/create-user`, {
      data: {
        name: 'E2E Flow User',
        native_language: 'Polish',
        target_language: 'German',
      },
    });
    expect(userRes.ok()).toBeTruthy();
    const { user_id } = await userRes.json();

    // Load home page with user
    await page.goto(`http://localhost:5177/?userId=${user_id}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveTitle(/LinguaAI/i);

    // Verify stats load (may be 500 for fresh user with no data, but should not crash)
    const statsRes = await request.get(`${API}/api/stats/${user_id}`);
    expect(statsRes.status()).toBeLessThan(500);

    // Navigate to different pages via direct URL
    const pages = ['/lesson', '/flashcards', '/stats', '/conversation', '/news'];
    for (const path of pages) {
      await page.goto(`http://localhost:5177${path}?userId=${user_id}`);
      await page.waitForLoadState('domcontentloaded');
      const bodyText = await page.textContent('body');
      expect(bodyText.length).toBeGreaterThan(20);
    }
  });

  test('user can switch between pages without errors', async ({ page, request }) => {
    const userRes = await request.post(`${API}/api/placement/create-user`, {
      data: {
        name: 'E2E Switch User',
        native_language: 'Polish',
        target_language: 'English',
      },
    });
    const { user_id } = await userRes.json();

    await page.goto(`http://localhost:5177/?userId=${user_id}`);
    await page.waitForLoadState('domcontentloaded');

    const paths = ['/stats', '/flashcards', '/lesson'];
    for (const path of paths) {
      await page.goto(`http://localhost:5177${path}?userId=${user_id}`);
      await page.waitForLoadState('domcontentloaded');
    }

    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(20);
  });

  test('multiple users can coexist', async ({ request }) => {
    const users = [];
    for (let i = 0; i < 3; i++) {
      const res = await request.post(`${API}/api/placement/create-user`, {
        data: {
          name: `Multi User ${i}`,
          native_language: 'Polish',
          target_language: 'German',
        },
      });
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      users.push(body.user_id);
    }

    // All users should have unique IDs
    const uniqueIds = new Set(users);
    expect(uniqueIds.size).toBe(3);

    // Each should have their own stats (may be 500 for fresh users, but not crash)
    for (const uid of users) {
      const statsRes = await request.get(`${API}/api/stats/${uid}`);
      expect(statsRes.status()).toBeLessThan(500);
    }
  });
});
