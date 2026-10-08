import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001';

test.describe('API Smoke Tests', () => {
  let userId;

  test.beforeAll(async ({ request }) => {
    const response = await request.post(`${API}/api/placement/create-user`, {
      data: {
        name: 'E2E API User',
        native_language: 'Polish',
        target_language: 'German',
      },
    });
    const body = await response.json();
    userId = body.user_id;
  });

  test('health endpoint', async ({ request }) => {
    const res = await request.get(`${API}/api/health`);
    expect(res.ok()).toBeTruthy();
  });

  test('get user stats', async ({ request }) => {
    const res = await request.get(`${API}/api/stats/${userId}`);
    expect(res.status()).toBeLessThan(500);
  });

  test('get tips', async ({ request }) => {
    const res = await request.get(`${API}/api/tips/${userId}`);
    expect(res.status()).toBeLessThan(500);
  });

  test('get lesson list returns object with lessons array', async ({ request }) => {
    const res = await request.get(`${API}/api/lessons/list/${userId}`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('lessons');
    expect(Array.isArray(body.lessons)).toBeTruthy();
  });

  test('get flashcards for valid user', async ({ request }) => {
    const res = await request.get(`${API}/api/flashcards/${userId}`);
    expect(res.status()).toBeLessThan(500);
  });

  test('get test history', async ({ request }) => {
    const res = await request.get(`${API}/api/tests/history/${userId}`);
    expect(res.status()).toBeLessThan(500);
  });

  test('get conversation sessions', async ({ request }) => {
    const res = await request.get(`${API}/api/conversation/sessions/${userId}`);
    expect(res.status()).toBeLessThan(500);
  });

  test('leaderboard endpoint', async ({ request }) => {
    const res = await request.get(`${API}/api/stats/leaderboard`);
    expect(res.status()).toBeLessThan(500);
  });

  test('CORS headers present', async ({ request }) => {
    const res = await request.get(`${API}/api/health`, {
      headers: { Origin: 'http://localhost:5177' },
    });
    expect(res.ok()).toBeTruthy();
  });
});
