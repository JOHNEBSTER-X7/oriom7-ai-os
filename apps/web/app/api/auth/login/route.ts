import { NextRequest, NextResponse } from "next/server";
import { createHash, randomBytes } from "node:crypto";
export const runtime="nodejs";
export async function GET(request:NextRequest){
 const endpoint=process.env.ORIOM7_OIDC_AUTHORIZATION_ENDPOINT;
 const clientId=process.env.ORIOM7_OIDC_CLIENT_ID;
 const redirectUri=process.env.ORIOM7_OIDC_REDIRECT_URI;
 const issuer=process.env.ORIOM7_OIDC_ISSUER;
 const audience=process.env.ORIOM7_OIDC_AUDIENCE;
 if(!endpoint||!clientId||!redirectUri||!issuer||!audience)return NextResponse.json({error:"OIDC sign-in is not configured."},{status:503});
 const state=randomBytes(32).toString("base64url"),nonce=randomBytes(32).toString("base64url");
 const verifier=randomBytes(48).toString("base64url");
 const challenge=createHash("sha256").update(verifier).digest("base64url");
 const url=new URL(endpoint);
 url.searchParams.set("response_type","code");url.searchParams.set("client_id",clientId);
 url.searchParams.set("redirect_uri",redirectUri);url.searchParams.set("scope",process.env.ORIOM7_OIDC_SCOPES||"openid profile email");
 url.searchParams.set("state",state);url.searchParams.set("nonce",nonce);
 url.searchParams.set("code_challenge",challenge);url.searchParams.set("code_challenge_method","S256");
 url.searchParams.set("audience",audience);
 const response=NextResponse.redirect(url);
 const secure=process.env.NODE_ENV==="production";
 for(const [name,value] of [["oriom7_oidc_state",state],["oriom7_oidc_nonce",nonce],["oriom7_oidc_verifier",verifier]] as const)
  response.cookies.set(name,value,{httpOnly:true,secure,sameSite:"lax",path:"/",maxAge:600});
 return response;
}
