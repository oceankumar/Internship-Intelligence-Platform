import { NextRequest, NextResponse } from "next/server";
import { workspaceAccess } from "./lib/server-access";

export async function middleware(request: NextRequest) {
  return (await workspaceAccess(request)) || NextResponse.next();
}
export const config = {
  runtime: "nodejs",
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
