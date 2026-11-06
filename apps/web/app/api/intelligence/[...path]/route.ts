import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

const ALLOWED_ENDPOINTS = new Set(["documents/ocr", "speech/transcriptions"]);
const MAX_REQUEST_BYTES = 26 * 1024 * 1024;

export async function POST(request: NextRequest, context: RouteContext) {
  const apiOrigin = process.env.ORIOM7_API_URL;
  if (!apiOrigin) {
    return NextResponse.json({ error: "ORIOM7_API_URL is not configured." }, { status: 503 });
  }

  const { path } = await context.params;
  const endpoint = path.join("/");
  if (!ALLOWED_ENDPOINTS.has(endpoint)) {
    return NextResponse.json({ error: "Unknown intelligence endpoint." }, { status: 404 });
  }

  const authorization = request.headers.get("authorization") || "";
  if (!authorization.startsWith("Bearer oriom_live_")) {
    return NextResponse.json({ error: "A valid ORIOM7 developer API key is required." }, { status: 401 });
  }

  const declaredLength = Number(request.headers.get("content-length") || 0);
  if (declaredLength > MAX_REQUEST_BYTES) {
    return NextResponse.json({ error: "Upload exceeds the 26 MB request limit." }, { status: 413 });
  }

  const contentType = request.headers.get("content-type") || "";
  if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
    return NextResponse.json({ error: "Upload must use multipart form data." }, { status: 415 });
  }

  const body = new Uint8Array(await request.arrayBuffer());
  if (body.byteLength > MAX_REQUEST_BYTES) {
    return NextResponse.json({ error: "Upload exceeds the 26 MB request limit." }, { status: 413 });
  }

  try {
    const upstream = await fetch(new URL(`/v1/${endpoint}`, apiOrigin), {
      method: "POST",
      headers: {
        Authorization: authorization,
        Accept: "application/json",
        "Content-Type": contentType,
      },
      body,
      cache: "no-store",
      redirect: "error",
    });
    const payload = await upstream.json().catch(() => ({ error: "ORIOM7 returned an invalid response." }));
    return NextResponse.json(payload, {
      status: upstream.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "ORIOM7 document or speech service is unavailable." }, { status: 502 });
  }
}
