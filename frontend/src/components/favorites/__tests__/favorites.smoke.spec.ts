/**
 * Vitest executes every file in this directory, but the smoke suite relies on
 * Playwright's test runner. Importing `@playwright/test` while Vitest is
 * bundling would explode, so we gate all dynamic loading behind the runtime
 * environment check. During Vitest runs we register a skipped placeholder so
 * the file shows up in reports without forcing a hard failure. Playwright picks
 * up the same file and executes the real suite.
 */
const isVitestEnvironment =
  typeof process !== "undefined" && Boolean(process.env.VITEST);

const playwrightModuleId = "@playwright/test";

if (isVitestEnvironment) {
  void import("vitest").then(({ describe }) => {
    describe.skip("Favorites dashboard Playwright smoke suite", () => {
      /* Vitest placeholder: real coverage executes in Playwright */
    });
  });
} else {
  const register = async () => {
    const { expect, test } = await import(playwrightModuleId);

    test.describe("Favorites dashboard", () => {
      test("renders the heading and collections column", async ({ page }) => {
        await page.goto("/favorites");
        await expect(
          page.getByRole("heading", { name: /Favorites dashboard/i }),
        ).toBeVisible();
        await expect(page.getByText(/Collections/i)).toBeVisible();
      });
    });
  };

  void register().catch((error: unknown) => {
    // eslint-disable-next-line no-console -- surfaced during CLI execution for visibility.
    console.warn(
      "Playwright smoke suite could not be registered; ensure devDependencies include @playwright/test.",
      error,
    );
  });
}
