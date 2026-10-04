import { NextRequest, NextResponse } from "next/server";
import { workspaceAccess } from "../../../lib/server-access";
import { allowedHost, backendUrl } from "../../../lib/service-url";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const denied = await workspaceAccess(request);
  if (denied) return denied;
  if (process.env.PUBLIC_DEMO_MODE === "true" && request.method !== "GET")
    return NextResponse.json({error:{message:"Public demo is read-only"}}, {status:403});
  const origin = request.headers.get("origin");
  const host = request.headers.get("host") || "";
  if (!allowedHost(host)) {
    return NextResponse.json(
      { error: { message: "Workspace host is not allowed" } },
      { status: 403 },
    );
  }
  let sameOrigin = !origin;
  try {
    sameOrigin = !origin || new URL(origin).host === host;
  } catch {
    sameOrigin = false;
  }
  if (!sameOrigin) {
    return NextResponse.json(
      { error: { message: "Origin is not allowed" } },
      { status: 403 },
    );
  }
  const { path } = await context.params;
  const base = backendUrl();
  const headers: Record<string, string> = {};
  if (request.headers.get("content-type"))
    headers["Content-Type"] = request.headers.get("content-type")!;
  if (process.env.API_TOKEN)
    headers.Authorization = "Bearer " + process.env.API_TOKEN;
  const chunks: Uint8Array[] = [];
  let length = 0;
  if (request.body) {
    const reader = request.body.getReader();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > 2_000_000) {
        await reader.cancel();
        return NextResponse.json(
          { error: { message: "File must be smaller than 2 MB" } },
          { status: 413 },
        );
      }
      chunks.push(value);
    }
  }
  try {
    const response = await fetch(
      base +
        "/api/" +
        path.map(encodeURIComponent).join("/") +
        request.nextUrl.search,
      {
        method: request.method,
        headers,
        body: length ? Buffer.concat(chunks) : undefined,
        cache: "no-store",
        signal: AbortSignal.timeout(180000),
      },
    );
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") || "application/json",
        ...(response.headers.get("content-disposition")
          ? {
              "Content-Disposition": response.headers.get(
                "content-disposition",
              )!,
            }
          : {}),
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          message:
            "The discovery service is unavailable. Start the backend and retry.",
        },
      },
      { status: 502 },
    );
  }
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
};
