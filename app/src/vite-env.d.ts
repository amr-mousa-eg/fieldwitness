/// <reference types="vite/client" />

/** "fixtures" = SYNTHETIC demo data (dev server only); "packs" = real field packs. */
declare const __FW_DATA_MODE__: "fixtures" | "packs";

/** Service worker cache version stamped per production build. */
declare const __FW_CACHE_VERSION__: string;
