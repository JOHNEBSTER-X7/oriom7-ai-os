import { NextRequest, NextResponse } from "next/server";
import { createRemoteJWKSet, jwtVerify } from "jose";
export const runtime="nodejs";
function clearFlowCookies(response:NextResponse){for(const name of ["oriom7_oidc_state","oriom7_oidc_nonce","oriom7_oidc_verifier"])response.cookies.set(name,"",{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:0});}
function fail(message:string,status=400){const response=NextResponse.json({error:message},{status});clearFlowCookies(response);return response;}
export async function GET(request:NextRequest){
 const params=request.nextUrl.searchParams;
 if(params.get("error"))return fail("The identity provider did not complete sign-in.");
 const code=params.get("code"),state=params.get("state");
 const expectedState=request.cookies.get("oriom7_oidc_state")?.value;
 const nonce=request.cookies.get("oriom7_oidc_nonce")?.value;
 const verifier=request.cookies.get("oriom7_oidc_verifier")?.value;
 if(!code||!state||!expectedState||state!==expectedState||!nonce||!verifier)return fail("The sign-in session expired or could not be verified. Please try again.");
 const tokenEndpoint=process.env.ORIOM7_OIDC_TOKEN_ENDPOINT,clientId=process.env.ORIOM7_OIDC_CLIENT_ID;
 const clientSecret=process.env.ORIOM7_OIDC_CLIENT_SECRET,redirectUri=process.env.ORIOM7_OIDC_REDIRECT_URI;
 const issuer=process.env.ORIOM7_OIDC_ISSUER,jwksUrl=process.env.ORIOM7_OIDC_JWKS_URL,audience=process.env.ORIOM7_OIDC_AUDIENCE;
 if(!tokenEndpoint||!clientId||!clientSecret||!redirectUri||!issuer||!jwksUrl||!audience)return fail("OIDC sign-in is not configured.",503);
 try{
  const form=new URLSearchParams({grant_type:"authorization_code",code,redirect_uri:redirectUri,client_id:clientId,client_secret:clientSecret,code_verifier:verifier});
  const tokenResponse=await fetch(tokenEndpoint,{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded",accept:"application/json"},body:form,cache:"no-store"});
  if(!tokenResponse.ok)return fail("The identity provider rejected the authorization code.");
  const tokens=await tokenResponse.json() as {access_token?:string;id_token?:string;token_type?:string;expires_in?:number};
  if(!tokens.access_token||!tokens.id_token||tokens.token_type?.toLowerCase()!=="bearer")return fail("The identity provider did not return the required tokens.");
  const jwks=createRemoteJWKSet(new URL(jwksUrl));
  const idResult=await jwtVerify(tokens.id_token,jwks,{issuer,audience:clientId});
  if(idResult.protectedHeader.alg!=="RS256")return fail("The identity provider must use RS256 token signatures.");
  if(idResult.payload.nonce!==nonce)return fail("The identity-provider nonce did not match.");
  const accessResult=await jwtVerify(tokens.access_token,jwks,{issuer,audience});
  if(accessResult.protectedHeader.alg!=="RS256")return fail("The API access token must use RS256 token signatures.");
  const maxAge=Math.max(60,Math.min(Number(tokens.expires_in)||300,3600));
  const response=NextResponse.redirect(new URL("/account",request.url));
  response.cookies.set("oriom7_access_token",tokens.access_token,{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge});
  clearFlowCookies(response);
  return response;
 }catch{return fail("The identity token or API access token could not be verified.");}
}
