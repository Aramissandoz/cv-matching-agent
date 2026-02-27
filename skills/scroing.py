import argparse
import json
import logging
import os
import sys
import re
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# Prompt optimisé pour le scoring décimal (0.0 - 1.0) et l'analyse critique
SCORING_PROMPT = """Tu es Zepeck-Judge, un expert en recrutement technique spécialisé en IA (Machine Learning) et Fiannce quantitative.
Ton rôle est d'évaluer la pertinence d'une offre d'emploi par rapport au profil d'un candidat.

Produis un JSON de scoring STRICT avec des valeurs décimales (float) entre 0.0 et 1.0 :

{
  "score_global": 0.0-1.0,
  "match_technique": 0.0-1.0,
  "match_secteur": 0.0-1.0,
  "points_forts": ["liste des 3 principaux points de match"],
  "points_manquants": ["liste des technos ou skills manquants critiques"],
  "verdict": "RECOMMANDÉ | POTENTIEL | RISQUÉ | ÉCARTÉ",
  "commentaire_synthetique": "1 phrase expliquant le score"
}

Règles de scoring (Sois impitoyable) :
1. Score de 0.8+ si l'offre demande des compétences pointues (ML Ops, Quant, LLM) correspondant aux frameworks du CV (PyTorch, Docker, etc.).
2. Pénalité de -0.4 sur le score_global si la durée du stage est incompatible (ex: Offre 6 mois alors que le candidat cherche 2 mois).
3. Si le poste est trop "Business" ou "Support" sans composante Engineering/Maths, le score technique ne doit pas dépasser 0.3.
4. Un score de 1.0 est réservé à un 'Perfect Match' (Stack + Durée + Localisation).
"""

def calculate_score(cv_data: Dict[str, Any], job_description: str) -> Dict[str, Any]:
    """Appel au LLM (LLM-as-a-Judge) pour comparer le CV et l'offre."""
    api_url = os.getenv("LLM_API_URL", "http://localhost:11434/v1")
    api_key = os.getenv("LLM_API_KEY", "ollama")
    model = os.getenv("LLM_MODEL", "llama3.1:8b")

    client = OpenAI(base_url=api_url, api_key=api_key)

    prompt_user = f"""
    ### DONNÉES DU CANDIDAT (CV PARSÉ) :
    {json.dumps(cv_data, ensure_ascii=False)}

    ### DESCRIPTION DE L'OFFRE RÉCUPÉRÉE :
    {job_description}

    Réalise l'analyse de matching et renvoie le JSON (scores entre 0.0 et 1.0) :
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": prompt_user},
            ],
            temperature=0, # Zéro pour une constance maximale des scores
        )
        raw_result = response.choices[0].message.content
        
        # Extraction robuste du bloc JSON
        match = re.search(r"\{.*\}", raw_result, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {"error": "Le LLM n'a pas renvoyé un format JSON valide."}
    except Exception as e:
        logger.error(f"Erreur lors du scoring : {e}")
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Scoring sémantique CV/Offre (Échelle 0-1)")
    parser.add_argument("cv_json_path", help="Chemin vers le JSON du CV (parsing.py)")
    parser.add_argument("job_text_path", help="Chemin vers le texte de l'offre (web_fetch)")
    
    args = parser.parse_args()

    try:
        # Lecture des fichiers
        with open(args.cv_json_path, 'r', encoding='utf-8') as f:
            cv_data = json.load(f)

        with open(args.job_text_path, 'r', encoding='utf-8') as f:
            job_text = f.read()

        # Calcul du matching
        result = calculate_score(cv_data, job_text)
        
        # Sortie standard pour capture par l'agent
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        logger.error(f"Fichier introuvable : {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur d'exécution : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()