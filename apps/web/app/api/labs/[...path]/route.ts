import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  const base = "/v1/labs/";
  if (path === "projects" || path === "equipment" || path === "equipment/summary") return base + path + search;
  if (/^inventory\/(items|suppliers|requisitions|purchase-orders|receipts|lots|movements|summary)$/i.test(path)) return base + path + search;
  if (/^inventory\/lots\/[0-9a-f-]{36}\/inspection$/i.test(path)) return base + path + search;
  if (/^inventory\/items\/[0-9a-f-]{36}\/issues$/i.test(path)) return base + path + search;
  if (/^quality\/(inspections|nonconformances|capa|compliance-documents|analytics)$/i.test(path)) return base + path + search;
  if (/^quality\/capa\/[0-9a-f-]{36}(\/events)?$/i.test(path)) return base + path + search;
  if (/^quality\/compliance-documents\/[0-9a-f-]{36}\/review$/i.test(path)) return base + path + search;
  if (/^finance\/(cost-centres|budgets|grants|transactions|depreciation|analytics)$/i.test(path)) return base + path + search;
  if (/^projects\/[0-9a-f-]{36}$/i.test(path)) return base + path + search;
  if (/^projects\/[0-9a-f-]{36}\/(experiments|notebook)$/i.test(path)) return base + path + search;
  if (/^experiments\/[0-9a-f-]{36}(\/events)?$/i.test(path)) return base + path + search;
  if (/^equipment\/[0-9a-f-]{36}$/i.test(path)) return base + path + search;
  if (/^equipment\/[0-9a-f-]{36}\/(calibrations|maintenance|bookings)$/i.test(path)) return base + path + search;
  if (/^equipment\/bookings\/[0-9a-f-]{36}$/i.test(path)) return base + path + search;
  return null;
}

async function forward(request: NextRequest, context: RouteContext, method: "GET" | "POST" | "PATCH") {
  const apiOrigin = process.env.ORIOM7_API_URL;
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const params = await context.params;
  const target = targetPath(params.path, request.nextUrl.search);
  if (!target) return NextResponse.json({ error: "Unknown laboratory endpoint." }, { status: 404 });

  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  const authorization = request.headers.get("authorization");
  if (cookie) headers.set("cookie", cookie);
  if (authorization) headers.set("authorization", authorization);
  const body = method === "GET" ? undefined : await request.text();
  if (body !== undefined) headers.set("content-type", "application/json");

  try {
    const upstream = await fetch(new URL(target, apiOrigin), { method, headers, body, cache: "no-store" });
    const payload = await upstream.json().catch(() => ({ error: "Invalid API response." }));
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: "ORIOM7 API is unavailable." }, { status: 502 });
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return forward(request, context, "GET");
}
export async function POST(request: NextRequest, context: RouteContext) {
  return forward(request, context, "POST");
}
export async function PATCH(request: NextRequest, context: RouteContext) {
  return forward(request, context, "PATCH");
}
