"use client";
import { useState } from "react";
import { ChevronDown, Home, FileText, History, Users, LayoutDashboard, Calendar, Wallet } from "lucide-react";

function Section({
  label, icon, children, defaultOpen = false,
}: {
  label: string; icon: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card !p-0 overflow-hidden">
      <button type="button" onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors">
        <div className="flex items-center gap-2.5 text-sm font-semibold" style={{ color: "#18211C" }}>
          {icon} {label}
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`} style={{ color: "#9CA3AF" }} />
      </button>
      {open && (
        <div className="px-5 pb-5 pt-1 space-y-3 text-sm leading-relaxed" style={{ color: "#3F4A42" }}>
          {children}
        </div>
      )}
    </div>
  );
}

export default function NoticeView() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold" style={{ color: "#18211C" }}>Notice d&apos;utilisation</h2>
        <p className="text-sm mt-1" style={{ color: "#7C857F" }}>
          Le fonctionnement de l&apos;application, section par section.
        </p>
      </div>

      <div className="rounded-xl px-4 py-3 text-sm flex items-start gap-2" style={{ backgroundColor: "#FEF3C7", color: "#92400E" }}>
        <Wallet className="w-4 h-4 mt-0.5 shrink-0" />
        <span>
          <strong>À venir :</strong> une limite d&apos;usage IA par mois et par utilisateur est à l&apos;étude,
          équivalente à 10&nbsp;€ — soit, selon le type d&apos;échange avec l&apos;IA, entre environ
          700&nbsp;000 tokens (si c&apos;est surtout du texte généré, le plus coûteux) et 3,6&nbsp;millions
          de tokens (si c&apos;est surtout du texte lu par l&apos;IA, le moins coûteux). Elle n&apos;est pas
          encore active — cette notice sera mise à jour le jour de son activation.
        </span>
      </div>

      <Section label="Page d'accueil — créer un document" icon={<Home className="w-4 h-4" style={{ color: "#14532D" }} />} defaultOpen>
        <p>
          C&apos;est ici que tout commence. En haut, on choisit le <strong>modèle</strong> du devis (Moderne ou Pro)
          et si on veut générer un <strong>devis</strong> ou une <strong>facture</strong>.
        </p>
        <p>
          On peut aussi <strong>importer un document existant</strong> (bouton « Importer un devis existant ») :
          l&apos;app relit un PDF ou un Word déjà fait et le retranscrit dans son propre format.
        </p>
        <p>
          Dans la case <strong>« Description du chantier »</strong>, on décrit le chantier le plus précisément
          possible — plus c&apos;est détaillé, meilleur sera le résultat généré. Des prestations types sont
          proposées en raccourci pour aller plus vite.
        </p>
        <p>
          En dessous, plusieurs onglets dépliables (Entreprise, Numérotation, Client, Mes prix habituels,
          Paramètres du document...) permettent de compléter les informations du devis. Deux sont
          <strong> obligatoires</strong> : <strong>Entreprise</strong> (hors champs marqués facultatifs) et
          <strong> Client</strong>. Les autres sont optionnels.
        </p>
        <p>
          Une fois tout rempli, on clique sur <strong>« Générer le document »</strong>.
        </p>
      </Section>

      <Section label="Document généré — modifier, exporter, envoyer" icon={<FileText className="w-4 h-4" style={{ color: "#14532D" }} />}>
        <p>
          Une fois le document généré, <strong>tout est modifiable</strong> directement à l&apos;écran : lignes,
          prix, quantités, mentions, lots... Sur téléphone, il est conseillé de <strong>passer l&apos;écran en
          mode paysage</strong> pour voir toutes les colonnes et défiler plus facilement.
        </p>
        <p>
          On peut à tout moment basculer entre <strong>devis</strong> et <strong>facture</strong>, convertir un
          devis déjà envoyé en <strong>facture d&apos;acompte</strong> en un clic, modifier la date et le titre du
          fichier, puis <strong>télécharger en PDF ou en Word</strong>.
        </p>
        <p>
          En cliquant sur <strong>« Marquer envoyé »</strong>, de nouveaux boutons apparaissent : on peut copier
          le <strong>lien de signature électronique</strong> et l&apos;envoyer au client. Une fois que le client a
          signé, sa signature apparaît directement sur le document téléchargé.
        </p>
      </Section>

      <Section label="Historique" icon={<History className="w-4 h-4" style={{ color: "#14532D" }} />}>
        <p>
          Tous les documents déjà créés, classés en deux onglets <strong>Devis</strong> et <strong>Facture</strong>.
          Un clic sur un document permet de le rouvrir, le modifier, changer son statut, le dupliquer ou le
          supprimer.
        </p>
      </Section>

      <Section label="Clients" icon={<Users className="w-4 h-4" style={{ color: "#14532D" }} />}>
        <p>
          La liste de tous les clients, avec pour chacun les différents documents déjà réalisés — pratique pour
          retrouver l&apos;historique d&apos;un chantier ou d&apos;un client en particulier.
        </p>
      </Section>

      <Section label="Dashboard" icon={<LayoutDashboard className="w-4 h-4" style={{ color: "#14532D" }} />}>
        <p>
          Des graphiques pour visualiser d&apos;un coup d&apos;œil l&apos;état de l&apos;entreprise (chiffre
          d&apos;affaires par mois, répartition des statuts des documents...).
        </p>
      </Section>

      <Section label="Calendrier" icon={<Calendar className="w-4 h-4" style={{ color: "#14532D" }} />}>
        <p>
          Un calendrier partagé : le bouton <strong>« Nouvel événement »</strong> permet d&apos;en créer un
          facilement (titre, description, horaires, créateur). Trois vues disponibles : <strong>Mois</strong>,
          <strong> Semaine</strong> et <strong>Jour</strong>.
        </p>
      </Section>
    </div>
  );
}
