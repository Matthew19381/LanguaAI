import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    timeout: 60000,
    retries: 1,
    fullyParallel: false,
    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5177',
        reuseExistingServer: true,
        timeout: 30000,
    },
    use: {
        baseURL: 'http://localhost:5177',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
});
