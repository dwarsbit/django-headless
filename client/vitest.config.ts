import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // The end-to-end tests need a server: npm run e2e
    include: ["test/**/*.test.ts"],
  },
});
