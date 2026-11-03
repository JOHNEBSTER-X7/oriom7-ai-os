import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

function upstreamPath(segments: string[], search: string) {
  const path = segments.join("/");
  if (path === "search") return "/v1/search";
  if (path === "assistant") return "/v1/assistant/responses";
  if (path === "agent-runs") return `/v1/research/agents/runs${search}`;
  if (path === "agent-schedules") return `/v1/research/agents/schedules${search}`;
  const schedule = path.match(/^agent-schedules\/([0-9a-f-]{36})$/i);
  if (schedule) return `/v1/research/agents/schedules/${schedule[1]}${search}`;
  const agentRun = path.match(/^agent-runs\/([0-9a-f-]{36})$/i);
  if (agentRun) return `/v1/research/agents/runs/${agentRun[1]}${search}`;
  if (path === "entities") return `/v1/knowledge/entities${search}`;
  if (path === "review-queue") return `/v1/knowledge/assertions/review-queue${search}`;
  const entity = path.match(/^entities\/([0-9a-f-]{36})$/i);
  if (entity) return `/v1/knowledge/entities/${entity[1]}${search}`;
  const paths = path.match(/^entities\/([0-9a-f-]{36})\/paths$/i);
  if (paths) return `/v1/knowledge/entities/${paths[1]}/paths${search}`;
  const review = path.match(/^assertions\/([0-9a-f-]{36})\/review$/i);
  if (review) return `/v1/knowledge/assertions/${review[1]}/review`;
  return null;
}

async function forward(request: NextRequest, context: RouteContext, method: "GET" | "POST" | "PATCH") {
  const apiOrigin = process.env.ORIOM7_API_URL;
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const { path } = await context.params;
  const target = upstreamPath(path, request.nextUrl.search);
  if (!target) return NextResponse.json({ error: "Unknown research endpoint." }, { status: 404 });

  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  const authorization = request.headers.get("authorization");
  if (cookie) headers.set("cookie", cookie);
  if (authorization) headers.set("authorization", authorization);
  const body = method === "GET" ? undefined : await request.text();
  if (body !== undefined) headers.set("content-type", "application/json");
  if (method === "POST" && path.includes("/review")) {
    const reviewToken = process.env.ORIOM7_GRAPH_REVIEW_TOKEN;
    if (!reviewToken) return NextResponse.json({ error: "Graph review is not configured on the server." }, { status: 503 });
    headers.set("X-ORIOM7-GRAPH-REVIEW-TOKEN", reviewToken);
  }

  try {
    const upstream = await fetch(new URL(target, apiOrigin), {
      method, headers, body, cache: "no-store",
    });
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
