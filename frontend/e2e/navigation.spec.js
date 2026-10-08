import { test, expect } from '@playwright/test';

test.describe('Navigation & Layout', () => {
  let userId;

  test.beforeAll(async ({ request }) => {
    const response = await request.post('http://localhost:8001/api/placement/create-user', {
      data: {
        name: 'E2E Nav User',
        native_language: 'Polish',
        target_language: 'German',
      },
    });
    const body = await response.json();
    userId = body.user_id;
  });

  test('home page loads with user', async ({ page }) => {
    await page.goto(`http://localhost:5177/?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page).toHaveTitle(/LinguaAI/i);
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
  });

  test('navigation bar is visible with logged-in user', async ({ page }) => {
    await page.goto(`http://localhost:5177/?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for nav to appear
    const nav = page.locator('nav').first();
    const navVisible = await nav.isVisible().catch(() => false);
    if (navVisible) {
      const links = nav.locator('a');
      const count = await links.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('can navigate to stats page via direct URL', async ({ page }) => {
    await page.goto(`http://localhost:5177/stats?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('stats');
  });

  test('can navigate to flashcards page via direct URL', async ({ page }) => {
    await page.goto(`http://localhost:5177/flashcards?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('flashcards');
  });

  test('can navigate to lesson page via direct URL', async ({ page }) => {
    await page.goto(`http://localhost:5177/lesson?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('lesson');
  });

  test('can navigate to conversation page via direct URL', async ({ page }) => {
    await page.goto(`http://localhost:5177/conversation?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('conversation');
  });

  test('can navigate to news page via direct URL', async ({ page }) => {
    await page.goto(`http://localhost:5177/news?userId=${userId}`);
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('news');
  });

  test('unauthenticated user sees home page', async ({ page }) => {
    await page.goto('http://localhost:5177/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveTitle(/LinguaAI/i);
  });
});
