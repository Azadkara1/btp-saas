/**
 * Client API — toutes les fonctions d'appel au backend FastAPI.
 * Centralisé ici pour faciliter l'ajout d'auth (Étape 2) et le mock en tests.
 */
import { QuoteRequest, QuoteResponse, Devis } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Génère un devis à partir d'une description textuelle.
 */
export async function generateQuote(request: QuoteRequest): Promise<QuoteResponse> {
  const response = await fetch(`${API_URL}/quotes/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erreur réseau" }));
    return { success: false, error: error.detail || "Erreur inconnue" };
  }

  return response.json();
}

/**
 * Exporte un devis ou une facture en Word (.docx) et déclenche le téléchargement.
 */
export async function exportToWord(
  devis: Devis,
  documentType: "devis" | "facture" = "devis",
  withTva: boolean = true,
  documentDate?: string,
): Promise<void> {
  const response = await fetch(`${API_URL}/word/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      devis,
      document_type: documentType,
      with_tva: withTva,
      document_date: documentDate ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail?.detail || `Erreur ${response.status}`);
  }

  const buf = await response.arrayBuffer();
  const blob = new Blob([buf], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  document.body.appendChild(a);
  a.href = url;
  a.download = `${documentType}.docx`;
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 1000);
}

/**
 * Exporte un devis ou une facture en PDF et déclenche le téléchargement.
 */
export async function exportToPdf(
  devis: Devis,
  documentType: "devis" | "facture" = "devis",
  withTva: boolean = true,
  documentDate?: string,
): Promise<void> {
  const response = await fetch(`${API_URL}/pdf/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      devis,
      document_type: documentType,
      with_tva: withTva,
      document_date: documentDate ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail?.detail || `Erreur ${response.status}`);
  }

  // Force octet-stream pour éviter que Chrome ouvre son lecteur PDF intégré
  const buf = await response.arrayBuffer();
  const blob = new Blob([buf], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  document.body.appendChild(a);
  a.href = url;
  a.download = `${documentType}.pdf`;
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 1000);
}
