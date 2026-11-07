import { NextResponse } from "next/server";
export async function POST(request:Request){
 const response=NextResponse.redirect(new URL("/",request.url));
 for(const name of ["oriom7_access_token","oriom7_id_token"])response.cookies.set(name,"",{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:0});
 return response;
}
export async function GET(request:Request){return POST(request);}
