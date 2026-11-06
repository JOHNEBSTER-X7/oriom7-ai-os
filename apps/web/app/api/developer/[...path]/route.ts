import { NextRequest } from "next/server";
import { forwardDeveloperRequest } from "../forward";

type Context = { params: Promise<{ path: string[] }> };
async function handler(request: NextRequest, context: Context) { const { path } = await context.params; return forwardDeveloperRequest(request, path, request.method); }
export const GET = handler;
export const POST = handler;
export const DELETE = handler;
