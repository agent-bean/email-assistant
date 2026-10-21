import type { paths } from './schema';

type Health = paths['/health']['get']['responses'][200]['content']['application/json'];

export async function getHealth(signal: AbortSignal): Promise<Health> {
  const response = await fetch('/api/health', { signal });
  if (!response.ok) throw new Error('API unavailable');
  return response.json() as Promise<Health>;
}
