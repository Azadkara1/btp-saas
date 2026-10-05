"use client";
import { useState, useEffect, useMemo } from "react";
import { ChevronLeft, ChevronRight, Plus, X, Loader2, Trash2, CalendarDays } from "lucide-react";
import {
  format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addMonths, subMonths,
  addWeeks, subWeeks, addDays, subDays, eachDayOfInterval, isSameDay, isSameMonth,
  isToday, parseISO, startOfDay, endOfDay,
} from "date-fns";
import { fr } from "date-fns/locale";
import { Evenement, EvenementCreate } from "@/lib/types";
import { listEvenements, createEvenement, updateEvenement, deleteEvenement } from "@/lib/api";

type Mode = "mois" | "semaine" | "jour";

// Dernier créateur utilisé + liste des créateurs déjà vus — cache navigateur
// uniquement (pas d'endpoint dédié côté backend), lu en useEffect uniquement
// (jamais dans un useState lazy initializer — piège SSR documenté dans CLAUDE.md).
const LS_DERNIER = "calendrier_dernier_createur";
const LS_CONNUS = "calendrier_createurs_connus";

const CREATEUR_COLORS = ["#14532D", "#1D4ED8", "#B45309", "#7C3AED", "#DB2777", "#0D9488", "#B91C1C", "#475569"];

function colorForCreateur(nom: string): string {
  let hash = 0;
  for (let i = 0; i < nom.length; i++) hash = (hash * 31 + nom.charCodeAt(i)) >>> 0;
  return CREATEUR_COLORS[hash % CREATEUR_COLORS.length];
}

function capFirst(s: string): string {
  return s.length ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function toDateInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function periodeTitle(mode: Mode, anchor: Date): string {
  if (mode === "mois") return capFirst(format(anchor, "LLLL yyyy", { locale: fr }));
  if (mode === "jour") return capFirst(format(anchor, "EEEE d LLLL", { locale: fr }));
  const start = startOfWeek(anchor, { weekStartsOn: 1 });
  const end = endOfWeek(anchor, { weekStartsOn: 1 });
  const texte = start.getMonth() === end.getMonth()
    ? `${format(start, "d")} – ${format(end, "d LLLL", { locale: fr })}`
    : `${format(start, "d LLLL", { locale: fr })} – ${format(end, "d LLLL", { locale: fr })}`;
  return capFirst(texte);
}

export default function CalendrierView() {
  const [mode, setMode] = useState<Mode>("mois");
  const [anchor, setAnchor] = useState<Date>(new Date());
  const [events, setEvents] = useState<Evenement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const [modalState, setModalState] = useState<{ event?: Evenement; defaultDate: Date } | null>(null);
  const [lastCreateur, setLastCreateur] = useState("");
  const [createeursConnus, setCreateeursConnus] = useState<string[]>([]);

  useEffect(() => {
    try {
      setLastCreateur(localStorage.getItem(LS_DERNIER) || "");
      const raw = localStorage.getItem(LS_CONNUS);
      if (raw) setCreateeursConnus(JSON.parse(raw));
    } catch { /* localStorage indisponible — dégradation silencieuse */ }
  }, []);

  const range = useMemo(() => {
    if (mode === "mois") {
      return {
        start: startOfWeek(startOfMonth(anchor), { weekStartsOn: 1 }),
        end: endOfWeek(endOfMonth(anchor), { weekStartsOn: 1 }),
      };
    }
    if (mode === "semaine") {
      return { start: startOfWeek(anchor, { weekStartsOn: 1 }), end: endOfWeek(anchor, { weekStartsOn: 1 }) };
    }
    return { start: anchor, end: anchor };
  }, [mode, anchor]);

  const loadEvents = () => {
    setLoading(true);
    setError(null);
    listEvenements(startOfDay(range.start).toISOString(), endOfDay(range.end).toISOString())
      .then(setEvents)
      .catch(e => setError(e instanceof Error ? e.message : "Erreur lors du chargement"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.start.getTime(), range.end.getTime()]);

  const joursGrille = useMemo(() => eachDayOfInterval({ start: range.start, end: range.end }), [range.start, range.end]);

  function eventsForDay(day: Date): Evenement[] {
    const debutJour = startOfDay(day);
    const finJour = endOfDay(day);
    return events
      .filter(e => parseISO(e.date_debut) <= finJour && parseISO(e.date_fin) >= debutJour)
      .sort((a, b) => {
        if (a.toute_la_journee !== b.toute_la_journee) return a.toute_la_journee ? -1 : 1;
        return a.date_debut.localeCompare(b.date_debut);
      });
  }

  const goPrev = () => setAnchor(prev => mode === "mois" ? subMonths(prev, 1) : mode === "semaine" ? subWeeks(prev, 1) : subDays(prev, 1));
  const goNext = () => setAnchor(prev => mode === "mois" ? addMonths(prev, 1) : mode === "semaine" ? addWeeks(prev, 1) : addDays(prev, 1));
  const goToday = () => { setAnchor(new Date()); setSelectedDay(null); };

  const openCreateModal = (defaultDate: Date) => setModalState({ defaultDate });
  const openEditModal = (event: Evenement) => setModalState({ event, defaultDate: parseISO(event.date_debut) });

  const handleSaved = (creePar: string) => {
    setModalState(null);
    try {
      localStorage.setItem(LS_DERNIER, creePar);
      const next = [creePar, ...createeursConnus.filter(n => n !== creePar)].slice(0, 20);
      localStorage.setItem(LS_CONNUS, JSON.stringify(next));
      setCreateeursConnus(next);
    } catch { /* localStorage indisponible — dégradation silencieuse */ }
    loadEvents();
  };

  function renderEventsList(dayEvents: Evenement[]) {
    if (dayEvents.length === 0) {
      return <p className="text-xs italic px-1" style={{ color: "#9CA3AF" }}>Aucun événement</p>;
    }
    return (
      <div className="space-y-1.5">
        {dayEvents.map(e => (
          <button key={e.id} onClick={() => openEditModal(e)}
            className="w-full flex items-center gap-2.5 rounded-xl p-2.5 text-left transition-all hover:shadow-sm"
            style={{ border: "0.5px solid rgba(20,83,45,0.12)", backgroundColor: "white" }}>
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: colorForCreateur(e.cree_par) }} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate" style={{ color: "#18211C" }}>{e.titre}</p>
              <p className="text-xs truncate" style={{ color: "#7C857F" }}>
                {e.toute_la_journee ? "Toute la journée" : `${format(parseISO(e.date_debut), "HH:mm")} – ${format(parseISO(e.date_fin), "HH:mm")}`}
                {" · par "}{e.cree_par}
              </p>
            </div>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>{periodeTitle(mode, anchor)}</h2>
        <button onClick={() => openCreateModal(selectedDay ?? anchor)} className="btn-primary flex items-center gap-1.5 text-sm">
          <Plus className="w-4 h-4" /> Événement
        </button>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-1">
          <button onClick={goPrev} title="Période précédente"
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors" style={{ color: "#5A635D" }}>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button onClick={goToday}
            className="text-xs font-medium rounded-lg px-3 py-2 transition-colors bg-white"
            style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
            Aujourd&apos;hui
          </button>
          <button onClick={goNext} title="Période suivante"
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors" style={{ color: "#5A635D" }}>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="flex gap-1">
          {(["mois", "semaine", "jour"] as const).map(m => (
            <button key={m} onClick={() => { setMode(m); setSelectedDay(null); }}
              className="text-xs font-medium rounded-lg px-3 py-2 transition-colors capitalize"
              style={mode === m
                ? { backgroundColor: "#14532D", color: "white" }
                : { border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D", backgroundColor: "white" }}>
              {m}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-2" style={{ borderColor: "#14532D", borderTopColor: "transparent" }} />
        </div>
      ) : mode === "mois" ? (
        <div className="space-y-4">
          <div>
            <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium mb-1" style={{ color: "#7C857F" }}>
              {["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"].map(j => <div key={j}>{j}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {joursGrille.map(day => {
                const dayEvents = eventsForDay(day);
                const inMonth = isSameMonth(day, anchor);
                const selected = selectedDay && isSameDay(day, selectedDay);
                return (
                  <button key={day.toISOString()} onClick={() => setSelectedDay(day)}
                    className="aspect-square rounded-xl flex flex-col items-center justify-start p-1 pt-1.5 gap-1 transition-colors"
                    style={{
                      backgroundColor: selected ? "#E3EDE6" : "white",
                      border: isToday(day) ? "1.5px solid #14532D" : "0.5px solid rgba(20,83,45,0.1)",
                      opacity: inMonth ? 1 : 0.4,
                    }}>
                    <span className="text-xs font-medium" style={{ color: "#18211C" }}>{format(day, "d")}</span>
                    <div className="flex gap-0.5 flex-wrap justify-center">
                      {dayEvents.slice(0, 4).map(e => (
                        <span key={e.id} className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colorForCreateur(e.cree_par) }} />
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {selectedDay && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold" style={{ color: "#18211C" }}>
                {capFirst(format(selectedDay, "EEEE d LLLL", { locale: fr }))}
              </h3>
              {renderEventsList(eventsForDay(selectedDay))}
            </div>
          )}
        </div>
      ) : mode === "semaine" ? (
        <div className="space-y-5">
          {joursGrille.map(day => (
            <div key={day.toISOString()} className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold" style={{ color: isToday(day) ? "#14532D" : "#18211C" }}>
                  {capFirst(format(day, "EEEE d LLLL", { locale: fr }))}
                </h3>
                <button onClick={() => openCreateModal(day)} title="Ajouter un événement ce jour"
                  className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors" style={{ color: "#5A635D" }}>
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
              {renderEventsList(eventsForDay(day))}
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">{renderEventsList(eventsForDay(anchor))}</div>
      )}

      {events.length === 0 && !loading && !error && (
        <div className="text-center py-10 space-y-2">
          <CalendarDays className="w-8 h-8 mx-auto" style={{ color: "#C3CCC5" }} />
          <p className="text-sm" style={{ color: "#7C857F" }}>Aucun événement sur cette période</p>
        </div>
      )}

      {modalState && (
        <EvenementModal
          event={modalState.event}
          defaultDate={modalState.defaultDate}
          createeursConnus={createeursConnus}
          lastCreateur={lastCreateur}
          onClose={() => setModalState(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}

// ── Modale de création / édition ──────────────────────────────────

interface EvenementModalProps {
  event?: Evenement;
  defaultDate: Date;
  createeursConnus: string[];
  lastCreateur: string;
  onClose: () => void;
  onSaved: (creePar: string) => void;
}

function EvenementModal({ event, defaultDate, createeursConnus, lastCreateur, onClose, onSaved }: EvenementModalProps) {
  const initDebut = event ? parseISO(event.date_debut) : defaultDate;
  const initFin = event ? parseISO(event.date_fin) : new Date(defaultDate.getTime() + 60 * 60 * 1000);

  const [titre, setTitre] = useState(event?.titre ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  // Piège booléen Pydantic/React (CLAUDE.md) : toujours ?? false, jamais undefined.
  const [touteLaJournee, setTouteLaJournee] = useState(event?.toute_la_journee ?? false);
  const [creePar, setCreePar] = useState(event?.cree_par ?? lastCreateur ?? "");
  const [dateDebut, setDateDebut] = useState(toDateInputValue(initDebut));
  const [heureDebut, setHeureDebut] = useState(format(initDebut, "HH:mm"));
  const [dateFin, setDateFin] = useState(toDateInputValue(initFin));
  const [heureFin, setHeureFin] = useState(format(initFin, "HH:mm"));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!titre.trim()) { setError("Le titre est obligatoire."); return; }
    if (!creePar.trim()) { setError("Le nom du créateur (\"Créé par\") est obligatoire."); return; }

    const debut = touteLaJournee ? new Date(`${dateDebut}T00:00:00`) : new Date(`${dateDebut}T${heureDebut}:00`);
    const fin = touteLaJournee ? new Date(`${dateFin}T23:59:59`) : new Date(`${dateFin}T${heureFin}:00`);
    if (fin < debut) { setError("La fin doit être postérieure ou égale au début."); return; }

    setSaving(true);
    setError(null);
    const payload: EvenementCreate = {
      titre: titre.trim(),
      description: description.trim() || null,
      date_debut: debut.toISOString(),
      date_fin: fin.toISOString(),
      toute_la_journee: touteLaJournee,
      cree_par: creePar.trim(),
    };
    try {
      if (event) {
        await updateEvenement(event.id, payload);
      } else {
        await createEvenement(payload);
      }
      onSaved(creePar.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'enregistrement");
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!event) return;
    if (!window.confirm(`Supprimer « ${event.titre} » ? Cette action est irréversible.`)) return;
    setSaving(true);
    setError(null);
    try {
      await deleteEvenement(event.id);
      onSaved(creePar.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center" style={{ backgroundColor: "rgba(24,33,28,0.45)" }}>
      <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-md max-h-[92vh] overflow-y-auto p-6 space-y-4"
        style={{ boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold" style={{ color: "#18211C" }}>
            {event ? "Modifier l'événement" : "Nouvel événement"}
          </h3>
          <button onClick={onClose} disabled={saving}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-40" style={{ color: "#7C857F" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>Titre</label>
          <input type="text" value={titre} onChange={e => setTitre(e.target.value)} maxLength={120}
            placeholder="Ex. Chantier Dupont" className="input-field" autoFocus disabled={saving} />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>Description (optionnel)</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} rows={3}
            className="input-field resize-none text-sm" disabled={saving} />
        </div>

        <label className="flex items-center gap-2 text-sm" style={{ color: "#5A635D" }}>
          <input type="checkbox" checked={touteLaJournee} onChange={e => setTouteLaJournee(e.target.checked)} disabled={saving} />
          Toute la journée
        </label>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "#5A635D" }}>Début</label>
            <input type="date" value={dateDebut} onChange={e => setDateDebut(e.target.value)} className="input-field text-sm" disabled={saving} />
            {!touteLaJournee && (
              <input type="time" value={heureDebut} onChange={e => setHeureDebut(e.target.value)} className="input-field text-sm mt-1.5" disabled={saving} />
            )}
          </div>
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "#5A635D" }}>Fin</label>
            <input type="date" value={dateFin} onChange={e => setDateFin(e.target.value)} className="input-field text-sm" disabled={saving} />
            {!touteLaJournee && (
              <input type="time" value={heureFin} onChange={e => setHeureFin(e.target.value)} className="input-field text-sm mt-1.5" disabled={saving} />
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "#5A635D" }}>Créé par</label>
          <input type="text" value={creePar} onChange={e => setCreePar(e.target.value)} maxLength={80}
            list="createeurs-connus" placeholder="Ex. Karim" className="input-field" disabled={saving} />
          <datalist id="createeurs-connus">
            {createeursConnus.map(c => <option key={c} value={c} />)}
          </datalist>
        </div>

        {error && (
          <div className="rounded-xl px-3 py-2 text-sm" style={{ backgroundColor: "#FEF2F2", color: "#B91C1C" }}>
            ⚠ {error}
          </div>
        )}

        <div className="flex items-center justify-between gap-2 pt-2">
          {event ? (
            <button onClick={handleDelete} disabled={saving}
              className="flex items-center gap-1.5 text-sm rounded-xl px-3 py-2.5 transition-colors disabled:opacity-50"
              style={{ color: "#B91C1C" }}>
              <Trash2 className="w-4 h-4" /> Supprimer
            </button>
          ) : <span />}
          <div className="flex items-center gap-2">
            <button onClick={onClose} disabled={saving}
              className="text-sm rounded-xl px-4 py-2.5 transition-colors bg-white disabled:opacity-50"
              style={{ border: "0.5px solid rgba(20,83,45,0.15)", color: "#5A635D" }}>
              Annuler
            </button>
            <button onClick={handleSubmit} disabled={saving} className="btn-primary flex items-center gap-2">
              {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Enregistrement…</> : "Enregistrer"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
