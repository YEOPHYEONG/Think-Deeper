import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { prompt } = await req.json();
  return NextResponse.json({ reply: `Echo: ${prompt}` });
}
