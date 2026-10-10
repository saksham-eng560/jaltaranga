import { expect, test } from '@playwright/test';

test('command view uses one replay step and labels fixture provenance', async ({ page }) => {
  await page.goto('/command');
  await expect(page.getByRole('heading', { name: 'Flood response command' })).toBeVisible();
  await expect(page.getByText(/routing, road and shelter examples are synthetic/)).toBeVisible();
  await expect(page.locator('.route-line-primary')).toBeVisible();
  await expect(page.getByText('No forecast issuance is available at this replay time.')).toBeVisible();
  await expect(page.getByText(/No flood polygon is published for this timestamp/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve & send' })).toBeDisabled();
  await page.getByRole('slider', { name: 'Replay timestamp' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/at=.*%2B05%3A30/i);
  await expect(page.getByText('No road status artifact is available for this replay step.')).toBeVisible();
});

test('colony pack survives offline cold reload', async ({ page, context }) => {
  await page.goto('/colony/DEL-YP-04');
  await expect(page.getByRole('heading', { name: 'आपके परिवार के लिए रास्ता' })).toBeVisible();
  await expect(page.locator('.resident-save')).toBeEnabled();
  await page.locator('.resident-save').click();
  await expect(page.locator('.save-confirmation')).toContainText('इस डिवाइस पर सहेजा गया');
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText('OFFLINE PACK')).toBeVisible();
  await expect(page.locator('.resident-footer-note a[href="tel:1077"]')).toBeVisible();
  await expect(page.getByText(/Saved plan is over two hours old/)).toHaveCount(0);
  await expect(page.getByText(/Loaded from this device/)).toHaveCount(0);
  await context.setOffline(false);
});

test('report screen keeps delivery pending without the write API', async ({ page }) => {
  await page.goto('/report');
  await expect(page.getByRole('heading', { name: 'Report a local condition' })).toBeVisible();
  await expect(page.getByText('Report API not configured')).toBeVisible();
  await page.getByLabel(/Water depth/).fill('45');
  await page.getByRole('button', { name: 'Submit observation' }).click();
  await expect(page.getByText(/Report saved in the local queue/)).toBeVisible();
  await expect(page.getByText('Waiting for API confirmation')).toBeVisible();
});
