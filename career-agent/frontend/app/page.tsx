async function getBackendHealth() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!res.ok) return { status: "unreachable" };
    return res.json();
  } catch {
    return { status: "unreachable" };
  }
}

export default async function HomePage() {
  const health = await getBackendHealth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold">Career Agent</h1>
      <p className="text-sm opacity-70">
        Backend status: {health.status ?? "unknown"}
      </p>
    </main>
  );
}
