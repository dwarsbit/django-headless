import { DjangoRestClient } from "@django-headless/client";

import type { Models } from "./headless";

export const api = new DjangoRestClient<Models>({
  baseUrl: process.env.API_URL as string,
  secretKey: process.env.API_SECRET_KEY,
});
