import { test, expect } from "@playwright/test";

test.describe("Core routes", () => {
  test("should display the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("should display the jobs page", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page).toHaveURL(/jobs/);
  });

  test("should display the new job form", async ({ page }) => {
    await page.goto("/jobs/new");
    await expect(page).toHaveURL(/jobs\/new/);
  });

  test("should display the library page", async ({ page }) => {
    await page.goto("/library");
    await expect(page).toHaveURL(/library/);
  });

  test("should display the upload page", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/);
  });

  test("should navigate to files page", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });
});
