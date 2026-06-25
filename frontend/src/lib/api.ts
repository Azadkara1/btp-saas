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
 * Importe un devis/facture existant (PDF ou .docx) et retourne un Devis éditable.
 * Les champs artisan du document importé sont ignorés — on injecte le profil enregistré.
 */
export async function importQuote(
  file: File,
  artisanFields: Partial<QuoteRequest> & { modele?: string },
): Promise<QuoteResponse> {
  const formData = new FormData();
  formData.append("file", file);

  // Conversion data URL → base64 pur (même logique que doGenerate dans QuoteForm)
  const logoRaw = artisanFields.artisan_logo_base64 ?? "";
  const logoB64 = logoRaw.includes(",") ? logoRaw.split(",")[1] : logoRaw;

  const artisanKeys = [
    "artisan_nom", "artisan_siret", "artisan_iban", "artisan_bic",
    "artisan_adresse", "artisan_code_postal", "artisan_ville",
    "artisan_telephone", "artisan_email", "artisan_site_web",
  ] as const;

  for (const key of artisanKeys) {
    const val = artisanFields[key];
    if (val) formData.append(key, val);
  }
  if (logoB64) formData.append("artisan_logo_base64", logoB64);
  if (artisanFields.modele) formData.append("modele", artisanFields.modele);

  const response = await fetch(`${API_URL}/quotes/import`, {
    method: "POST",
    body: formData,
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
  filename?: string,
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
  a.download = filename ? `${filename}.docx` : `${documentType}.docx`;
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
  filename?: string,
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
  a.download = filename ? `${filename}.pdf` : `${documentType}.pdf`;
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 1000);
}
