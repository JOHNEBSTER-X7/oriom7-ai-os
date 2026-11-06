import { NextRequest } from "next/server";
import { forwardAccountRequest } from "../forward";
type Context={params:Promise<{path:string[]}>};
async function handle(request:NextRequest,context:Context){const {path}=await context.params;return forwardAccountRequest(request,path,request.method);}
export const GET=handle;
export const POST=handle;
export const PATCH=handle;
