import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.API_URL ?? 'http://127.0.0.1:8000'

// 프록시가 재구성하는 응답에서 제거해야 하는 hop-by-hop / 길이 관련 헤더
const STRIP_RESPONSE_HEADERS = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']

export const maxDuration = 60

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const url = `${BACKEND}/api/${path.join('/')}${req.nextUrl.search}`

  const headers = new Headers(req.headers)
  headers.delete('host')
  headers.delete('content-length')

  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
      // @ts-expect-error duplex required for streaming body
      duplex: 'half',
    })

    const outHeaders = new Headers(res.headers)
    for (const h of STRIP_RESPONSE_HEADERS) outHeaders.delete(h)

    return new NextResponse(req.method === 'HEAD' ? null : res.body, {
      status: res.status,
      headers: outHeaders,
    })
  } catch {
    return NextResponse.json({ detail: 'backend unavailable' }, { status: 502 })
  }
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy
export const HEAD = proxy
export const OPTIONS = proxy
