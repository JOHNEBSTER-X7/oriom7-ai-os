import { NextRequest, NextResponse } from "next/server";

const apiOrigin = process.env.ORIOM7_API_URL;

export async function forwardDeveloperRequest(request: NextRequest, path: string[], method: string) {
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const headers = new Headers({ accept: "application/json" });
  for (const name of ["cookie", "authorization", "content-type"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const body = ["POST", "PUT", "PATCH"].includes(method) ? await request.text() : undefined;
  try {
    const upstream = await fetch(new URL(`/v1/developer/${path.join("/")}`, apiOrigin), { method, headers, body, cache: "no-store" });
    const payload = await upstream.json().catch(() => ({}));
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: "ORIOM7 API is unavailable." }, { status: 502 });
  }
}
