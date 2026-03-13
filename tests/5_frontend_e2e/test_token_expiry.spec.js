const { test, expect } = require('@playwright/test');

test('Frontend UI enforces authentication boundary', async ({ page }) => {
  await page.goto('/');
  
  await page.fill('#user', 'hacker');
  await page.fill('#pass', 'wrongpass');
  await page.click('#btn');
  await expect(page.locator('#msg')).toHaveText('Access Denied');

  await page.fill('#user', 'admin');
  await page.fill('#pass', process.env.ADMIN_PASSWORD || 'password123');
  await page.click('#btn');
  await expect(page.locator('#msg')).toHaveText('Token Received');
});
