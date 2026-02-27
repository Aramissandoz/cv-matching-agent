import argparse
import json
import logging
import os
import sys
import re
from pathlib import Path
from typing import Optional

import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

CV_PARSING_PROMPT = """Tu es un modèle spécialisé dans l'analyse de CV techniques à haute valeur ajoutée,
couvrant les domaines suivants :
- Intelligence Artificielle (IA), Machine Learning (ML), Deep Learning (DL)
- Data Science, Data Engineering, MLOps, LLMOps
- Finance Quantitative : quant researcher, quant developer, quant analyst, structuration, risk quant
- Finance de Marché : trading, sales, market making, asset management, dérivés, fixed income, equities

Tu reçois TOUJOURS en entrée du texte brut extrait d'un PDF.
Ce texte peut contenir des sauts de ligne, des sections désordonnées, des colonnes mélangées ou des formats irréguliers.
Ton rôle est d'extraire les informations essentielles et de produire un JSON STRICT, SANS commentaire, SANS texte autour, SANS explication.

Analyse le CV et renvoie un JSON avec les champs suivants :

{
  "name": "prénom et nom du candidat si disponible",
  "contact": {
    "email": "email si disponible",
    "phone": "téléphone si disponible",
    "linkedin": "URL LinkedIn si disponible",
    "github": "URL GitHub ou portfolio si disponible"
  },
  "location": "ville, pays ou remote si mentionné",
  "contract_type": "stage | alternance | junior | fin d'étude | senior | CDI | CDD | freelance | inconnu",
  "education_level": "niveau d'étude le plus élevé (ex: Licence 3, Master 1, Master 2, Ingénieur, Doctorat, MBA)",
  "education": [
    {
      "degree": "nom du diplôme ou programme",
      "school": "nom de l'école ou université",
      "field": "domaine d'étude (ex: Mathématiques Appliquées, Informatique, Finance...)",
      "year": "année d'obtention ou prévue si disponible"
    }
  ],
  "experience": [
    {
      "title": "intitulé du poste",
      "company": "nom de l'entreprise",
      "sector": "secteur (ex: hedge fund, banque d'investissement, startup IA, fintech, GAFAM...)",
      "duration": "durée si mentionnée",
      "description": "brève description des missions si disponible",
      "skills": ["liste des compétences et technologies utilisées dans ce poste"]
    }
  ],
  "technical_stack": {
    "languages": ["Python", "C++", "R", "Julia", "MATLAB", "SQL", "Rust", "Java", "..."],
    "ml_dl_frameworks": ["PyTorch", "TensorFlow", "JAX", "Keras", "Scikit-learn", "XGBoost", "LightGBM", "Hugging Face", "LangChain", "..."],
    "quant_finance_tools": ["Bloomberg", "Reuters/Refinitiv", "QuantLib", "Pandas", "NumPy", "SciPy", "statsmodels", "backtrader", "zipline", "..."],
    "data_infra": ["Spark", "Kafka", "Airflow", "dbt", "Snowflake", "BigQuery", "Redshift", "..."],
    "mlops_devops": ["Docker", "Kubernetes", "MLflow", "Weights & Biases", "GitHub Actions", "Terraform", "Ray", "..."],
    "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "..."],
    "other": ["tout outil ou technologie ne rentrant pas dans les catégories ci-dessus"]
  },
  "quant_finance_skills": {
    "pricing_models": ["Black-Scholes", "Monte Carlo", "HJM", "Heston", "SABR", "LSM", "..."],
    "asset_classes": ["equities", "fixed income", "FX", "commodities", "dérivés", "credit", "rates", "..."],
    "strategies": ["arbitrage statistique", "market making", "HFT", "momentum", "mean reversion", "factor investing", "..."],
    "risk_management": ["VaR", "CVaR", "stress testing", "Greeks", "hedging", "..."],
    "regulation": ["Bâle III/IV", "MiFID II", "IFRS 9", "FRTB", "..."]
  },
  "ai_ml_skills": {
    "domains": ["NLP", "computer vision", "RL", "time series", "forecasting", "generative AI", "LLM fine-tuning", "..."],
    "methods": ["transformers", "LSTM", "GNN", "diffusion models", "RAG", "RLHF", "..."],
    "research": ["publications", "thèse", "Kaggle", "projets open source notables"]
  },
  "mandatory_skills": ["compétences clairement exigées ou fortement mises en avant par le candidat"],
  "optional_skills": ["compétences secondaires ou mentionnées ponctuellement"],
  "keywords": ["mots-clés importants du CV pour le matching sémantique"],
  "mission_type": "data | machine learning | deep learning | NLP | computer vision | quant research | quant dev | risk | trading | asset management | software | MLOps | autre",
  "start_date": "date de disponibilité si mentionnée",
  "internship_duration": "durée du stage ou de la mission si mentionnée",
  "salary_expectation": "salaire ou fourchette si mentionnée",
  "languages": {
    "Français": "natif | courant | intermédiaire | débutant | inconnu",
    "Anglais": "natif | courant | intermédiaire | débutant | inconnu",
    "Autres": "langue : niveau"
  },
  "work_mode": "remote | hybride | sur site | inconnu",
  "mobility": "national | international | région spécifique | inconnu",
  "certifications": ["CFA", "FRM", "AWS", "Google Cloud", "certifications Coursera/Deeplearning.ai", "..."],
  "notable_projects": [
    {
      "name": "nom du projet",
      "description": "description courte",
      "technologies": ["liste des technologies"],
      "link": "lien si disponible"
    }
  ],
  "soft_skills": ["leadership", "esprit d'équipe", "autonomie", "communication", "..."],
  "profile_summary": "synthèse en 2-3 phrases du profil global du candidat, son positionnement et sa valeur ajoutée"
}

Règles strictes :
- Si une information n'est pas trouvée, mets la valeur "inconnu" pour les chaînes, [] pour les listes, {} pour les objets.
- Ne jamais inventer d'informations.
- Ne jamais ajouter de texte hors du JSON.
- Le JSON doit être valide et parsable par json.loads() en Python.
- Les compétences techniques doivent être normalisées avec leur casing standard (ex: "PyTorch", "TensorFlow", "C++", "SQL").
- Pour les profils quant, identifier précisément les asset classes et méthodes de pricing utilisées.
- Pour les profils ML/DL, identifier précisément les architectures et frameworks utilisés.
- Le champ profile_summary est OBLIGATOIRE et doit toujours être renseigné.

Renvoie UNIQUEMENT le JSON final. Aucun texte avant ou après.
"""

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrait le texte brut d'un fichier PDF en utilisant pdfplumber.

    Args:
        pdf_path: Chemin vers le fichier PDF.

    Returns:
        Texte brut extrait du PDF.

    Raises:
        FileNotFoundError: Si le fichier PDF n'existe pas.
        ValueError: Si le PDF est vide ou illisible.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier PDF introuvable : {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Le fichier doit être un PDF : {pdf_path}")

    logger.info(f"Extraction du texte depuis : {pdf_path}")
    full_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("Le PDF ne contient aucune page.")

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text.append(page_text)
                    logger.debug(f"  Page {i + 1} : {len(page_text)} caractères extraits.")
                else:
                    logger.warning(f"  Page {i + 1} : aucun texte extrait (possible image/scan).")

    except Exception as e:
        raise ValueError(f"Erreur lors de la lecture du PDF : {e}") from e

    text = "\n\n".join(full_text).strip()

    if not text:
        raise ValueError(
            "Aucun texte n'a pu être extrait du PDF. "
            "Le document est peut-être un scan (image) sans OCR."
        )

    logger.info(f"Texte extrait : {len(text)} caractères sur {len(full_text)} page(s).")
    return text


def analyze_cv_with_llm(
    text: str,
    api_url: str = "http://localhost:11434/v1",
    model: str = "llama3.1:8b",
    api_key: str = "ollama",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """
    Envoie le texte brut du CV au LLM (Llama-3.1-8B) et retourne un dict structuré.

    Compatible avec :
    - Ollama (serveur local)       : http://localhost:11434/v1
    - LM Studio (serveur local)    : http://localhost:1234/v1
    - Together AI / Groq / etc.    : adapter api_url et api_key
    - OpenAI-compatible API

    Args:
        text:        Texte brut du CV.
        api_url:     URL de base de l'API LLM (compatible OpenAI).
        model:       Identifiant du modèle à utiliser.
        api_key:     Clé API (peut être un placeholder pour les serveurs locaux).
        temperature: Température pour la génération (bas = déterministe).
        max_tokens:  Nombre maximal de tokens dans la réponse.

    Returns:
        Dictionnaire Python issu du JSON retourné par le LLM.

    Raises:
        RuntimeError: En cas d'échec de l'appel LLM ou de parsing du JSON.
    """
    # Récupération des credentials depuis l'environnement si disponibles
    api_key = os.getenv("LLM_API_KEY", api_key)
    api_url = os.getenv("LLM_API_URL", api_url)
    model = os.getenv("LLM_MODEL", model)

    logger.info(f"Appel LLM : modèle={model} | url={api_url}")

    client = OpenAI(base_url=api_url, api_key=api_key)

    user_message = f"""Voici le texte brut extrait d'un CV :

---
{text}
---

Analyse ce CV et renvoie UNIQUEMENT le JSON structuré demandé."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CV_PARSING_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'appel au LLM ({api_url}) : {e}") from e

    raw_output = response.choices[0].message.content
    if not raw_output:
        raise RuntimeError("Le LLM a retourné une réponse vide.")

    logger.debug(f"Réponse brute du LLM ({len(raw_output)} chars) :\n{raw_output[:500]}...")

    # Extraction du JSON même si le LLM a ajouté du texte autour
    parsed = _extract_json_from_llm_output(raw_output)
    return parsed


def _extract_json_from_llm_output(raw: str) -> dict:
    """
    Tente d'extraire un objet JSON valide depuis la sortie brute du LLM.
    Gère les cas où le modèle encadre le JSON avec ```json ... ``` ou du texte.

    Args:
        raw: Sortie brute du LLM.

    Returns:
        Dictionnaire Python.

    Raises:
        ValueError: Si aucun JSON valide ne peut être extrait.
    """
    # Tentative 1 : parsing direct
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Tentative 2 : extraction depuis un bloc ```json ... ```
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Tentative 3 : extraction du premier objet JSON { ... } dans le texte
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Impossible d'extraire un JSON valide depuis la réponse du LLM.\n"
        f"Début de la réponse : {raw[:300]}"
    )


def validate_json(data: dict) -> dict:
    """
    Valide et complète le JSON retourné par le LLM.
    S'assure que les champs critiques pour le matching sont présents.

    Args:
        data: Dictionnaire à valider.

    Returns:
        Dictionnaire validé et complété.

    Raises:
        ValueError: Si le JSON est structurellement invalide.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Le JSON retourné n'est pas un objet : {type(data)}")

    # Champs obligatoires de premier niveau
    required_fields = {
        "name": "inconnu",
        "contact": {},
        "location": "inconnu",
        "contract_type": "inconnu",
        "education_level": "inconnu",
        "education": [],
        "experience": [],
        "technical_stack": {},
        "quant_finance_skills": {},
        "ai_ml_skills": {},
        "mandatory_skills": [],
        "optional_skills": [],
        "keywords": [],
        "mission_type": "inconnu",
        "start_date": "inconnu",
        "internship_duration": "inconnu",
        "salary_expectation": "inconnu",
        "languages": {},
        "work_mode": "inconnu",
        "mobility": "inconnu",
        "certifications": [],
        "notable_projects": [],
        "soft_skills": [],
        "profile_summary": "inconnu",
    }

    missing_fields = []
    for field, default in required_fields.items():
        if field not in data:
            data[field] = default
            missing_fields.append(field)

    if missing_fields:
        logger.warning(
            f"Champs manquants complétés avec valeur par défaut : {missing_fields}"
        )

    # Validation des types pour les champs critiques
    list_fields = [
        "education", "experience", "mandatory_skills", "optional_skills",
        "keywords", "certifications", "notable_projects", "soft_skills",
    ]
    for field in list_fields:
        if not isinstance(data.get(field), list):
            logger.warning(f"Champ '{field}' n'est pas une liste — correction appliquée.")
            data[field] = []

    # Validation des sous-objets
    dict_fields = ["contact", "technical_stack", "quant_finance_skills", "ai_ml_skills", "languages"]
    for field in dict_fields:
        if not isinstance(data.get(field), dict):
            logger.warning(f"Champ '{field}' n'est pas un objet — correction appliquée.")
            data[field] = {}

    logger.info("Validation JSON : OK")
    return data


def main():
    """
    Point d'entrée principal. Orchestre extraction PDF → LLM → validation → output.
    """
    parser = argparse.ArgumentParser(
        description="Module de parsing de CV — Agent CV-Matching (OpenClaw)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python parsing.py mon_cv.pdf
  python parsing.py mon_cv.pdf --api-url http://localhost:11434/v1 --model llama3.1:8b
  python parsing.py mon_cv.pdf --api-url https://api.groq.com/openai/v1 --model llama-3.1-8b-instant --api-key sk-...
  python parsing.py mon_cv.pdf --output result.json
        """,
    )
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF du CV.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("LLM_API_URL", "http://localhost:11434/v1"),
        help="URL de l'API LLM compatible OpenAI (défaut : Ollama local).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "llama3.1:8b"),
        help="Identifiant du modèle LLM à utiliser.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_API_KEY", "ollama"),
        help="Clé API (utiliser 'ollama' pour Ollama local).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Température de génération (défaut : 0.1).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Nombre maximal de tokens dans la réponse (défaut : 4096).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Chemin vers un fichier de sortie JSON (optionnel).",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Active les logs de débogage."
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # --- Étape 1 : Extraction PDF ---
    try:
        raw_text = extract_text_from_pdf(args.pdf_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Extraction PDF échouée : {e}")
        sys.exit(1)

    # --- Étape 2 : Analyse LLM ---
    try:
        parsed_data = analyze_cv_with_llm(
            text=raw_text,
            api_url=args.api_url,
            model=args.model,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except (RuntimeError, ValueError) as e:
        logger.error(f"Analyse LLM échouée : {e}")
        sys.exit(2)

    # --- Étape 3 : Validation ---
    try:
        validated_data = validate_json(parsed_data)
    except ValueError as e:
        logger.error(f"Validation JSON échouée : {e}")
        sys.exit(3)

    # --- Étape 4 : Output ---
    output_json = json.dumps(validated_data, ensure_ascii=False, indent=2)

    # Affichage sur stdout (pour OpenClaw ou pipeline)
    print(output_json)

    # Sauvegarde optionnelle dans un fichier
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json, encoding="utf-8")
        logger.info(f"Résultat sauvegardé dans : {args.output}")

    return validated_data

if __name__ == "__main__":
    main()