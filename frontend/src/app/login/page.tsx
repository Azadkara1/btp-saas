"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { HardHat, Mail, Lock, ArrowRight, CheckCircle } from "lucide-react"
import { createClient } from "@/lib/supabase-client"

type Mode = "login" | "signup" | "check-email"

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode]         = useState<Mode>("login")
  const [email, setEmail]       = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const supabase = createClient()

    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) {
        setError("E-mail ou mot de passe incorrect.")
      } else {
        router.push("/")
        router.refresh()
      }
    } else {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/auth/confirm` },
      })
      if (error) {
        setError(error.message)
      } else {
        setMode("check-email")
      }
    }
    setLoading(false)
  }

  if (mode === "check-email") {
    return (
      <main className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#FAFAF7" }}>
        <div className="bg-white rounded-2xl p-8 max-w-sm w-full mx-4 text-center space-y-4"
          style={{ border: "0.5px solid rgba(20,83,45,0.12)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
          <div className="flex justify-center">
            <div className="p-3 rounded-2xl" style={{ backgroundColor: "#EDF5EF" }}>
              <CheckCircle className="w-8 h-8" style={{ color: "#14532D" }} />
            </div>
          </div>
          <h2 className="text-xl font-black" style={{ color: "#18211C" }}>Vérifiez votre e-mail</h2>
          <p className="text-sm" style={{ color: "#5A635D" }}>
            Un lien de confirmation a été envoyé à <strong>{email}</strong>.
            Cliquez dessus pour activer votre compte.
          </p>
          <button
            onClick={() => { setMode("login"); setPassword("") }}
            className="text-sm font-semibold"
            style={{ color: "#14532D" }}>
            ← Revenir à la connexion
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#FAFAF7" }}>
      <div className="bg-white rounded-2xl p-8 max-w-sm w-full mx-4 space-y-6"
        style={{ border: "0.5px solid rgba(20,83,45,0.12)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>

        <div className="flex items-center gap-3">
          <div className="text-white p-2 rounded-xl" style={{ backgroundColor: "#14532D" }}>
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-black leading-none" style={{ color: "#18211C" }}>DevisBTP</h1>
            <p className="text-xs" style={{ color: "#7C857F" }}>
              {mode === "login" ? "Connectez-vous à votre compte" : "Créez votre compte"}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold" style={{ color: "#5A635D" }}>E-mail</label>
            <div className="flex items-center gap-2 rounded-xl px-3 py-2.5"
              style={{ border: "0.5px solid rgba(20,83,45,0.2)" }}>
              <Mail className="w-4 h-4 shrink-0" style={{ color: "#7C857F" }} />
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                required placeholder="vous@exemple.com"
                className="flex-1 outline-none bg-transparent text-sm" style={{ color: "#18211C" }} />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold" style={{ color: "#5A635D" }}>Mot de passe</label>
            <div className="flex items-center gap-2 rounded-xl px-3 py-2.5"
              style={{ border: "0.5px solid rgba(20,83,45,0.2)" }}>
              <Lock className="w-4 h-4 shrink-0" style={{ color: "#7C857F" }} />
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                required minLength={6} placeholder="••••••••"
                className="flex-1 outline-none bg-transparent text-sm" style={{ color: "#18211C" }} />
            </div>
          </div>

          {error && (
            <p className="text-xs rounded-xl px-3 py-2"
              style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
              {error}
            </p>
          )}

          <button type="submit" disabled={loading}
            className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold text-white transition-opacity"
            style={{ backgroundColor: "#14532D", opacity: loading ? 0.6 : 1 }}>
            {loading ? "…" : mode === "login" ? "Se connecter" : "Créer le compte"}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <p className="text-center text-xs" style={{ color: "#7C857F" }}>
          {mode === "login" ? "Pas encore de compte ? " : "Déjà un compte ? "}
          <button
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null) }}
            className="font-semibold" style={{ color: "#14532D" }}>
            {mode === "login" ? "Créer un compte" : "Se connecter"}
          </button>
        </p>
      </div>
    </main>
  )
}
