const { test, expect } = require('@playwright/test');

const cases = [
  {
    name: 'components-default',
    path: '/__internal__/design-system/components/?tenant=default',
    waitFor: 'text=Components',
    projects: ['chromium'],
  },
  {
    name: 'forms-default',
    path: '/__internal__/design-system/forms/?tenant=default',
    waitFor: 'text=Forms',
    projects: ['chromium'],
  },
  {
    name: 'ecommerce-default',
    path: '/__internal__/design-system/ecommerce/?tenant=default',
    waitFor: 'text=Ecommerce',
    projects: ['chromium'],
  },
  {
    name: 'ecommerce-storefront',
    path: '/__internal__/design-system/ecommerce/?tenant=storefront',
    waitFor: 'text=Ecommerce',
    projects: ['chromium', 'tablet'],
  },
  {
    name: 'pages-default',
    path: '/__internal__/design-system/pages/?tenant=default',
    waitFor: 'text=Page Templates',
    projects: ['chromium', 'tablet'],
    fullPage: false,
  },
  {
    name: 'pages-default-customer-area-preview',
    path: '/__internal__/design-system/pages/?tenant=default',
    waitFor: 'text=Customer Area Page Templates',
    scrollTo: 'text=Customer Area Page Templates',
    projects: ['chromium'],
    fullPage: false,
  },
  {
    name: 'pages-default-auth-account-preview',
    path: '/__internal__/design-system/pages/?tenant=default',
    waitFor: 'text=Auth / Account Page Templates',
    scrollTo: 'text=Auth / Account Page Templates',
    projects: ['chromium'],
    fullPage: false,
  },
  {
    name: 'pages-storefront-preview',
    path: '/__internal__/design-system/pages/?tenant=storefront',
    waitFor: 'text=Page Templates',
    scrollTo: 'text=Storefront Page Templates',
    projects: ['chromium'],
    fullPage: false,
  },
  {
    name: 'pages-demo-admin-products-orders-customers-preview',
    path: '/__internal__/design-system/pages/?tenant=demo',
    waitFor: 'text=Admin Page Templates',
    scrollTo: 'text=Product Management Flow',
    projects: ['chromium'],
    fullPage: false,
  },
  {
    name: 'pages-nike-preview',
    path: '/__internal__/design-system/pages/?tenant=nike',
    waitFor: 'text=Page Templates',
    scrollTo: 'text=Checkout Page Template',
    projects: ['chromium'],
    fullPage: false,
  },
];

for (const item of cases) {
  test(`showcase snapshot: ${item.name}`, async ({ page }) => {
    test.skip(item.projects && !item.projects.includes(test.info().project.name), `Case not enabled for ${test.info().project.name}`);
    await page.goto(item.path, { waitUntil: 'networkidle' });
    await page.locator('body').evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('body')).toContainText(/Tenant:/);
    await page.waitForSelector(item.waitFor);
    if (item.scrollTo) {
      await page.locator(item.scrollTo).scrollIntoViewIfNeeded();
      await page.waitForTimeout(250);
    }
    await expect(page).toHaveScreenshot(`${item.name}.png`, { fullPage: item.fullPage ?? true });
  });
}
