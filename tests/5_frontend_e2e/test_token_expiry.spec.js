// tests/5_frontend_e2e/test_token_expiry.spec.js
const { test, expect } = require('@playwright/test');

test('Frontend gracefully handles expired JWT token', async ({ page }) => {
  // 1. Navigate to the frontend application
  await page.goto('https://app.highassurance.dev/login');
  
  // 2. Simulate user login
  await page.fill('#username', 'test_user');
  await page.fill('#password', 'secure_password');
  await page.click('#login-btn');
  
  // 3. Verify successful login by checking for the dashboard element
  await expect(page.locator('#dashboard')).toBeVisible();

  // 4. SPACE-GRADE HACK: Manually manipulate the browser's LocalStorage 
  // to replace the valid token with an expired one (simulating 24 hours passing)
  await page.evaluate(() => {
    localStorage.setItem('jwt_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...EXPIRED_PAYLOAD');
  });

  // 5. User attempts to make a transfer with the expired token
  await page.click('#initiate-transfer-btn');

  // 6. THE ASSERTION: The frontend MUST intercept the 401 API response 
  // and redirect the user back to the login page immediately.
  await expect(page).toHaveURL('https://app.highassurance.dev/login?session=expired');
  
  // 7. Verify a user-friendly error message is displayed (No raw API errors!)
  await expect(page.locator('#error-toast')).toHaveText('Your session has expired. Please log in again.');
});
