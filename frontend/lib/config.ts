/**
 * Application config for Saarthi AI frontend.
 * Resolves the backend URL dynamically from environment variables.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://saarthi-ai-ztrc.onrender.com";
