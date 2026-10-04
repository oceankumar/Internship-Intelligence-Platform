import { NextRequest, NextResponse } from "next/server";

export async function workspaceAccess(request: NextRequest) {
  const host = request.headers.get("host") || "";
  const allowed = (
    process.env.ALLOWED_HOSTS || "localhost:3000,127.0.0.1:3000"
  ).split(",");
  if (!allowed.includes(host)) {
    return NextResponse.json(
      { error: { message: "Workspace host is not allowed" } },
      { status: 403 },
    );
  }
  const local = /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host);
  const password = process.env.WORKSPACE_PASSWORD;
  if (!local && !password) {
    return NextResponse.json(
      {
        error: {
          message: "Configure private workspace access before remote use",
        },
      },
      { status: 503 },
    );
  }
  if (password) {
    let credentials = "";
    try {
      credentials = atob(
        (request.headers.get("authorization") || "").replace(/^Basic /, ""),
      );
    } catch {
      /* Invalid credentials remain empty. */
    }
    const expected = (process.env.WORKSPACE_USER || "owner") + ":" + password;
    const hash = async (value: string) =>
      new Uint8Array(
        await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
      );
    const received = await hash(credentials),
      correct = await hash(expected);
    let difference = 0;
    for (let i = 0; i < correct.length; i++)
      difference |= correct[i] ^ received[i];
    if (difference !== 0)
      return new NextResponse("Private workspace", {
        status: 401,
        headers: {
          "WWW-Authenticate":
            'Basic realm="Internship Intelligence", charset="UTF-8"',
        },
      });
  }
  return null;
}
