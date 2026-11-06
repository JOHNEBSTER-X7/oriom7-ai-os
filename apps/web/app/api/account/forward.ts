import { NextRequest, NextResponse } from "next/server";
const apiOrigin=process.env.ORIOM7_API_URL;
export async function forwardAccountRequest(request:NextRequest,path:string[],method:string){
 if(!apiOrigin)return NextResponse.json({error:"ORIOM7_API_URL is not configured."},{status:503});
 const headers=new Headers({accept:"application/json"});
 const incoming=request.headers.get("authorization");
 const apiKey=incoming?.startsWith("Bearer oriom_live_")?incoming:null;
 const sessionToken=request.cookies.get("oriom7_access_token")?.value;
 if(apiKey)headers.set("authorization",apiKey);
 else if(sessionToken)headers.set("authorization",`Bearer ${sessionToken}`);
 const identityToken=request.cookies.get("oriom7_id_token")?.value;
 if(identityToken)headers.set("x-oriom7-id-token",identityToken);
 const contentType=request.headers.get("content-type");if(contentType)headers.set("content-type",contentType);
 const body=["POST","PUT","PATCH"].includes(method)?await request.text():undefined;
 try{
  const upstream=await fetch(new URL(`/v1/account/${path.map(encodeURIComponent).join("/")}`,apiOrigin),{method,headers,body,cache:"no-store"});
  const payload=await upstream.json().catch(()=>({}));
  return NextResponse.json(payload,{status:upstream.status});
 }catch{return NextResponse.json({error:"ORIOM7 API is unavailable."},{status:502});}
}
