import { useEffect, useState } from 'react';
import { getHealth } from './api/client';

export function App() {
  const [state, setState] = useState<'loading' | 'ok' | 'unavailable'>('loading');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    getHealth(controller.signal).then(() => setState('ok'), () => setState('unavailable'));
    return () => { clearTimeout(timer); controller.abort(); };
  }, [attempt]);
  return <main>
    <p className="eyebrow">Local workspace</p>
    <h1>Email Assistant</h1>
    <p>Application foundation. Email and calendar features are not enabled yet.</p>
    <section aria-labelledby="api-title">
      <h2 id="api-title">API connection</h2>
      <p role="status" aria-live="polite">{
        state === 'loading' ? 'Checking API…' : state === 'ok' ? 'API is running.' : 'API unavailable. Start the backend and retry.'
      }</p>
      <button disabled={state === 'loading'} onClick={() => { setState('loading'); setAttempt(n => n + 1); }}>Check again</button>
    </section>
  </main>;
}
