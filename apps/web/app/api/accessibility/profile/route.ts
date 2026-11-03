import { NextRequest, NextResponse } from "next/server";

const apiOrigin = process.env.ORIOM7_API_URL;

async function forward(request: NextRequest, method: string) {
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  const authorization = request.headers.get("authorization");
  if (cookie) headers.set("cookie", cookie);
  if (authorization) headers.set("authorization", authorization);
  let body: string | undefined;
  if (method === "PUT") {
    headers.set("content-type", "application/json");
    body = await request.text();
  }
  try {
    const upstream = await fetch(new URL("/v1/accessibility/profile", apiOrigin), {
      method, headers, body, cache: "no-store",
    });
    if (upstream.status === 204) return new NextResponse(null, { status: 204 });
    const payload = await upstream.json().catch(() => ({ error: "Invalid API response." }));
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: "ORIOM7 API is unavailable." }, { status: 502 });
  }
}

export async function GET(request: NextRequest) { return forward(request, "GET"); }
export async function PUT(request: NextRequest) { return forward(request, "PUT"); }
export async function DELETE(request: NextRequest) { return forward(request, "DELETE"); }
