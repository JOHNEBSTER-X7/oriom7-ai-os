import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const apiOrigin = process.env.ORIOM7_API_URL;
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const headers = new Headers({ "content-type": "application/json", accept: "application/json" });
  const cookie = request.headers.get("cookie");
  const authorization = request.headers.get("authorization");
  if (cookie) headers.set("cookie", cookie);
  if (authorization) headers.set("authorization", authorization);
  try {
    const upstream = await fetch(new URL("/v1/accessibility/resolve", apiOrigin), {
      method: "POST", headers, body: await request.text(), cache: "no-store",
    });
    const payload = await upstream.json().catch(() => ({ error: "Invalid API response." }));
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: "ORIOM7 API is unavailable." }, { status: 502 });
  }
}
