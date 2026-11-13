import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/experimentsimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/notebookimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}/events$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^equipment/${UUID}import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/experimentsimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/notebookimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}/events$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^equipment/${UUID}/(calibrations|maintenance|bookings)import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/experimentsimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/notebookimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}/events$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^equipment/bookings/${UUID}import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/experimentsimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^projects/${UUID}/notebookimport { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UUID = "[0-9a-f-]{36}";

function targetPath(segments: string[], search: string): string | null {
  const path = segments.join("/");
  if (path === "projects") return `/v1/labs/projects${search}`;
  if (path === "equipment") return `/v1/labs/equipment${search}`;
  if (new RegExp(`^projects/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}$`, "i").test(path)) return `/v1/labs/${path}${search}`;
  if (new RegExp(`^experiments/${UUID}/events$`, "i").test(path)) return `/v1/labs/${path}${search}`;
, "i").test(path)) return `/v1/labs/${path}${search}`;
  return null;
}

async function forward(request: NextRequest, context: RouteContext, method: "GET" | "POST" | "PATCH") {
  const apiOrigin = process.env.ORIOM7_API_URL;
  if (!apiOrigin) return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  const { path } = await context.params;
  const target = targetPath(path, request.nextUrl.search);
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
