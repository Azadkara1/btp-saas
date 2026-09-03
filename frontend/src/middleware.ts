import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Ne rien mettre entre createServerClient et getUser() — règle Supabase SSR
  const { data: { user } } = await supabase.auth.getUser()

  const path = request.nextUrl.pathname
  // /devis/[token] : page publique de signature électronique (Batch 12 T3) —
  // consultée par le CLIENT de l'artisan, jamais connecté à l'app. Ne jamais
  // la protéger par l'auth sous peine de rediriger tout visiteur vers /login.
  const isPublicPath = path.startsWith('/login') || path.startsWith('/auth') || path.startsWith('/devis/')

  if (!user && !isPublicPath) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
