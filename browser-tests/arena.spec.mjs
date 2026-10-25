import { test, expect, devices } from "@playwright/test";
const iphone = devices["iPhone 13"];

test("desktop homepage has help, training access, and watch-only controls", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");

  // The removed spell gallery should stay removed.
  await expect(page.locator(".spell-card")).toHaveCount(0);

  // The How to Play section should still work.
  await expect(page.locator("#spells details.help")).toHaveCount(1);
  await page.locator("#spells summary").click();
  await expect(page.locator("#spells details.help")).toHaveAttribute(
    "open",
    "",
  );

  // Training Grounds should remain directly accessible.
  await expect(
    page.locator('.training-entry a[href="/practice"]'),
  ).toBeVisible();

  // Computers should only spectate.
  await expect(page.locator("#createTab")).toBeHidden();
  await expect(page.locator("#submit")).toHaveText("Watch room ↗");

  // No JavaScript errors should occur.
  expect(errors).toEqual([]);
});

test("mobile player creation works and desktop override links only spectate", async ({
  browser,
  page,
  request,
}) => {
  const mobile = await browser.newContext({
    ...iphone,
    baseURL: "http://127.0.0.1:8765",
  });
  const phone = await mobile.newPage();
  await phone.goto("/");
  await expect(phone.locator("#createTab")).toBeVisible();
  expect(
    await phone.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await phone.locator("#name").fill("Test Mage");
  await phone.locator("#submit").click();
  await expect(phone).toHaveURL(/\/phone\?room=/);
  await expect(phone.locator(".training")).toBeVisible();
  const room = new URL(phone.url()).searchParams.get("room");
  await page.goto("/phone?player=1&room=" + room);
  await expect(page).toHaveURL("/arena?room=" + room);
  await expect(page.locator(".mage-label")).toHaveCount(1);
  const info = await request.get("/api/rooms/" + room);
  expect((await info.json()).players).toBe(1);
  await mobile.close();
});

test("3D demo renders four mages and keeps a single canvas through live spells", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/arena?demo=1");
  await expect(page.locator("#arenaViewport canvas")).toHaveCount(1);
  await expect(page.locator(".mage-label")).toHaveCount(4);
  await expect(page.locator("#sceneStatus")).toBeHidden();
  await expect(page.locator(".feed")).toContainText("ward cast", {
    timeout: 10000,
  });
  await expect(page.locator("#arenaViewport canvas")).toHaveCount(1);
  await page.locator("#sceneMotion").click();
  await expect(page.locator("#sceneMotion")).toHaveText("Play animation");
  await page.locator("#sceneMotion").click();
  await expect(page.locator("#sceneMotion")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(errors).toEqual([]);
});

test("reduced motion starts paused and mobile arena fits viewport", async ({
  browser,
}) => {
  const context = await browser.newContext({
    ...iphone,
    baseURL: "http://127.0.0.1:8765",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto("/arena?demo=1");
  await expect(page.locator(".mage-label")).toHaveCount(4);
  await expect(page.locator("#sceneMotion")).toHaveText("Play animation");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await context.close();
});

test("unsupported WebGL keeps live scores and demo feed", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...args) {
      if (type.startsWith("webgl")) return null;
      return original.call(this, type, ...args);
    };
  });
  await page.goto("/arena?demo=1");
  await expect(page.locator("#sceneStatus")).toContainText("3D is unavailable");
  await expect(page.locator(".fighter")).toHaveCount(4);
  await expect(page.locator("#sceneMotion")).toBeDisabled();
});
