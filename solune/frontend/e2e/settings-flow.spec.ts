import { test, expect } from './authenticated-fixtures';

test.describe('Settings Flow', () => {
  test('saves AI settings changes and restores them after reload', async ({ page }) => {
    await page.goto('/settings');

    const temperatureSlider = page.locator('#primary-temperature');
    await expect(temperatureSlider).toHaveValue('0.7');

    await temperatureSlider.focus();
    for (let index = 0; index < 4; index += 1) {
      await page.keyboard.press('ArrowRight');
    }

    await expect(temperatureSlider).toHaveValue('1.1');
    await expect(page.getByText('Temperature: 1.1')).toBeVisible();

    const saveButton = page.getByRole('button', { name: 'Save' });
    await expect(saveButton).toBeEnabled();
    await saveButton.click();

    await expect(page.getByText('Saved!')).toBeVisible();

    await page.reload();

    await expect(page.getByText('Temperature: 1.1')).toBeVisible();
    await expect(page.locator('#primary-temperature')).toHaveValue('1.1');
  });
});
