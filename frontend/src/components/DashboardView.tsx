"use client";
import { useState, useEffect } from "react";
import { LayoutDashboard, TrendingUp, Clock, Wallet, Target, PiggyBank } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { DashboardStats } from "@/lib/types";
import { getDashboardStats } from "@/lib/api";

// Couleurs de statut — identiques à HistoriqueView.tsx / ClientsView.tsx / page.tsx (STATUT_BADGE)
const STATUT_COLOR: Record<string, { label: string; color: string }> = {
  brouillon: { label: "Brouillon", color: "#6B7280" },
  "envoyé":  { label: "Envoyé",    color: "#1D4ED8" },
  "signé":   { label: "Signé",     color: "#7C3AED" },
  "payé":    { label: "Payé",      color: "#14532D" },
  "refusé":  { label: "Refusé",    color: "#B91C1C" },
  "expiré":  { label: "Expiré",    color: "#4B5563" },
};

const MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

function fmtMoney(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + " €";
}

function fmtMoisLabel(mois: string): string {
  const [, m] = mois.split("-");
  const idx = parseInt(m, 10) - 1;
  return MOIS_COURT[idx] ?? mois;
}

function StatTile({ icon: Icon, label, value, sub }: { icon: typeof TrendingUp; label: string; value: string; sub?: string }) {
  return (
    <div className="card p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 rounded-lg" style={{ backgroundColor: "#E3EDE6" }}>
          <Icon className="w-3.5 h-3.5" style={{ color: "#14532D" }} />
        </div>
        <span className="text-xs font-medium" style={{ color: "#5A635D" }}>{label}</span>
      </div>
      <p className="text-xl sm:text-2xl font-bold" style={{ color: "#18211C" }}>{value}</p>
      {sub && <p className="text-xs mt-0.5" style={{ color: "#9CA3AF" }}>{sub}</p>}
    </div>
  );
}

function TooltipCa({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 text-xs bg-white shadow-md" style={{ border: "0.5px solid rgba(20,83,45,0.15)" }}>
      <p className="font-medium mb-0.5" style={{ color: "#18211C" }}>{label ? fmtMoisLabel(label) : ""}</p>
      <p style={{ color: "#14532D" }}>{fmtMoney(payload[0].value)}</p>
    </div>
  );
}

export default function DashboardView() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(e => setError(e instanceof Error ? e.message : "Erreur"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2"
          style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
        {error ?? "Erreur de chargement"}
      </div>
    );
  }

  const isEmpty = Object.keys(stats.repartition_statuts).length === 0;

  if (isEmpty) {
    return (
      <div className="text-center py-20 space-y-3">
        <LayoutDashboard className="w-10 h-10 mx-auto" style={{ color: "#C3CCC5" }} />
        <h2 className="text-lg font-bold" style={{ color: "#18211C" }}>Votre tableau de bord vous attend</h2>
        <p className="text-sm max-w-sm mx-auto" style={{ color: "#7C857F" }}>
          Générez votre premier devis pour voir apparaître ici votre chiffre d'affaires,
          votre taux de conversion et vos prestations les plus rentables.
        </p>
      </div>
    );
  }

  const repartitionData = Object.entries(stats.repartition_statuts)
    .map(([statut, count]) => ({
      name: STATUT_COLOR[statut]?.label ?? statut,
      value: count,
      color: STATUT_COLOR[statut]?.color ?? "#6B7280",
    }))
    .filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: "#18211C" }}>
        <LayoutDashboard className="w-5 h-5" style={{ color: "#14532D" }} /> Tableau de bord
      </h2>

      {/* KPI */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <StatTile icon={Target} label="CA signé" value={fmtMoney(stats.ca_signe)} />
        <StatTile icon={Clock} label="CA en attente" value={fmtMoney(stats.ca_en_attente)} sub="envoyé, non signé" />
        <StatTile icon={Wallet} label="CA encaissé" value={fmtMoney(stats.ca_encaisse)} />
        <StatTile icon={TrendingUp} label="Taux de conversion" value={`${stats.taux_conversion.toFixed(0)} %`} sub="devis → signé" />
        <StatTile icon={PiggyBank} label="Panier moyen" value={fmtMoney(stats.panier_moyen)} />
        <StatTile icon={Clock} label="Délai moyen signature"
          value={stats.delai_moyen_signature_jours != null ? `${stats.delai_moyen_signature_jours.toFixed(0)} j` : "—"} />
      </div>

      {/* Graphiques */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "#18211C" }}>CA des 12 derniers mois</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.ca_par_mois} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#F0F3F1" />
              <XAxis dataKey="mois" tickFormatter={fmtMoisLabel} tick={{ fontSize: 11, fill: "#7C857F" }}
                axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#7C857F" }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}`} width={40} />
              <Tooltip content={<TooltipCa />} cursor={{ fill: "rgba(20,83,45,0.06)" }} />
              <Bar dataKey="ca" fill="#14532D" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "#18211C" }}>Répartition par statut</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={repartitionData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                innerRadius={50} outerRadius={80} paddingAngle={2} stroke="#FFFFFF" strokeWidth={2}
                label={({ value }) => `${value}`} labelLine={false}>
                {repartitionData.map(d => <Cell key={d.name} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v, n) => [`${v} document${Number(v) > 1 ? "s" : ""}`, n]} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "#5A635D" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top prestations */}
      <div className="card">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "#18211C" }}>Top prestations par CA</h3>
        {stats.top_prestations.length === 0 ? (
          <p className="text-sm py-4 text-center" style={{ color: "#9CA3AF" }}>Aucune donnée pour l'instant</p>
        ) : (
          <div className="space-y-1.5">
            {stats.top_prestations.map((p, i) => (
              <div key={p.poste} className="flex items-center gap-3 py-1.5">
                <span className="text-xs font-mono w-5 shrink-0" style={{ color: "#9CA3AF" }}>{i + 1}</span>
                <span className="text-sm flex-1 min-w-0 truncate" style={{ color: "#18211C" }}>{p.poste}</span>
                <span className="text-sm font-semibold shrink-0" style={{ color: "#14532D" }}>{fmtMoney(p.ca)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
