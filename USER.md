# USER.md - Profil Utilisateur (Template)

## 👤 Identification du Candidat
- **Source de Vérité** : Les informations de ce profil doivent être extraites dynamiquement du fichier présent dans `data/` (PDF ou JSON généré).
- **Nom/Prénom** : [Extrait dynamiquement par parsing.py].

## 🎯 Cibles de Recherche (À configurer par l'utilisateur)
_L'utilisateur doit éditer cette section pour définir ses objectifs._
- **Métiers visés** : Liste des intitulés de postes (ex: ML Ops, Data Scientist, Quant).
- **Type de contrat** : Stage, Alternance, CDI.
- **Durée & Période** : Préciser les dates de disponibilité (ex: 2 mois, Été 2026).
- **Localisation** : Villes cibles ou préférence pour le Remote.

## 🛠️ Préférences Techniques
- **Stack Prioritaire** : Frameworks ou langages sur lesquels l'agent doit mettre l'accent (ex: PyTorch, Rust).
- **Seuil de Matching** : Score minimal (ex: 75%) pour qu'une offre soit considérée comme pertinente.

---
_Note pour l'Agent : Si ce fichier est vierge, base tes recherches exclusivement sur l'analyse de `data/cv_parsed.json` produite par le skill de parsing._