import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));

/** @type {import("next").NextConfig} */
const nextConfig = {
  // The app has its own lockfile inside the client package
  outputFileTracingRoot: root,
  turbopack: { root },
};

export default nextConfig;
