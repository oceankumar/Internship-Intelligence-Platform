export function backendUrl(env: NodeJS.ProcessEnv = process.env) {
  return (env.BACKEND_URL || env.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function allowedHost(host: string) {
  const explicit = (process.env.ALLOWED_HOSTS || "localhost:3000,127.0.0.1:3000").split(",");
  const generated = [process.env.VERCEL_URL, process.env.VERCEL_PROJECT_PRODUCTION_URL, process.env.VERCEL_BRANCH_URL].filter(Boolean);
  return [...explicit, ...generated].includes(host);
}
