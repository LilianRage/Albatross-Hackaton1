import requests
import json
import gradio as gr
import logging
import re

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = "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"
YOUR_SITE_URL = "votre-site.com"
YOUR_APP_NAME = "MonChatbot"

AIRTABLE_API_KEY = "patUUQ6NE9zUOqooM.ec8d096169d754852305c88c7966ad1f8a151f3bf015d39f80bb895bdad0e2f5"
AIRTABLE_BASE_ID = "appht9RdYAQVd32Py"
AIRTABLE_TABLE_NAME = "DescriptionsEtudiants"

competence_questions = [
    "Quelles sont vos compétences techniques ?",
    "Quelles sont vos compétences en communication ?",
    "Pouvez-vous me parler de vos expériences professionnelles ?",
    "Quelles sont vos compétences en gestion de projet ?"
]

def get_last_user_id():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Inscription_Etudiants"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "sort[0][field]": "ID_Etu",
        "sort[0][direction]": "desc",
        "maxRecords": 1
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if len(data['records']) > 0:
                last_record = data['records'][0]
                last_user_id = last_record['fields'].get('ID_Etu', 'Aucun ID trouvé')
                last_user_name = last_record['fields'].get('Nom', 'Aucun nom trouvé')
                return last_user_id, last_user_name
            else:
                return None, None
        else:
            logger.error(f"Erreur lors de la récupération des ID et du nom : {response.status_code} - {response.text}")
            return None, None

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations : {str(e)}")
        return None, None

def call_api_for_response_analysis(question, response):
    messages = [
        {
            "role": "system",
            "content": "Vous êtes un assistant IA expert en analyse de réponses. "
                    "Évaluez la réponse d'un utilisateur à une question sur ses compétences. "
                    "Renvoie le score de pertinence (0-100), le score de détail (0-100) et des suggestions pour améliorer la réponse. "
                    "Format de sortie : 'Score de pertinence, Score de détail, \"Suggestions\"'."
        },
        {
            "role": "user",
            "content": f"Question : {question}\nRéponse de l'utilisateur : {response}\n\n"
                    "Format de sortie attendu : 'Score de pertinence, Score de détail, \"Suggestions\"'."
        }
    ]

    try:
        api_response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )

        if api_response.status_code == 200:
            data = api_response.json()
            logger.info(f"Réponse de l'API : {data}")
            analysis = data['choices'][0]['message']['content']
            logger.info(f"Analyse brute de l'API : {analysis}")
            parsed_results = parse_analysis(analysis)
            return parsed_results

        else:
            logger.error(f"Erreur lors de l'analyse de la réponse : {api_response.status_code} - {api_response.text}")
            return {"error": f"Erreur lors de l'analyse de la réponse : {api_response.status_code} - {api_response.text}"}
    
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return {"error": f"Erreur: {str(e)}"}

def call_api_for_skill_assessment(responses):
    messages = [
        {"role": "system", "content": "Vous êtes un assistant IA qui évalue les compétences. Faites un bilan des compétences avec toutes les compétences, appliquez ceci à toutes les compétences de l'utilisateur. Évaluez-les en fonction de l'expérience de l'utilisateur, sans aucun autre commentaire, ni style dans le texte (pas de gras, pas de souligné, pas d'italique). Sous cette forme :\n- Compétence 1\n- Compétence 2\n- Compétence 3\n..."}
    ]

    for i, response in enumerate(responses):
        messages.append({"role": "user", "content": f"{competence_questions[i]} : {response}"})
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Erreur lors de l'appel à l'API : {response.status_code} - {response.text}"
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur: {str(e)}"

def get_enterprise_descriptions():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/DescriptionsEntreprises"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        descriptions = [(record['fields'].get('Nom', f"Entreprise {i+1}"), record['fields']['Description entreprises'], record['fields'].get('ID_Offre2')) for i, record in enumerate(data['records'])]
        return descriptions
    else:
        logger.error(f"Erreur lors de la récupération des descriptions d'entreprises : {response.status_code} - {response.text}")
        return []

def compare_skills_ai(student_skills, enterprise_skills):
    messages = [
        {"role": "system", "content": "Vous êtes un expert en recrutement chargé d'évaluer la correspondance entre les compétences d'un étudiant et celles requises par une entreprise. Votre tâche est d'analyser ces compétences et de fournir une valeur de correspondance entre l'étudiant et les différentes entreprise, je veux simplement la note global pour chaque entreprise. Tenez compte des compétences similaires ou complémentaires, pas seulement des correspondances exactes."},
        {"role": "user", "content": f"Compétences de l'étudiant :\n{student_skills}\n\nCompétences requises par l'entreprise :\n{enterprise_skills}\n\nVeuillez analyser ces compétences et fournir un chiffre entre 0 et 100 pour la correspondance entre l'etudiant et l'entreprise afin de voir le taux de compatibilité entre l'etudiants et les différentes entreprises. en détaille rien, juste la note global sans le détail. Ecrit que et uniquement le score, par exemple : 100 et pas : Score : 100, juste 100"}
    ]

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_analysis = data['choices'][0]['message']['content']
            try:
                score = int(ai_analysis.strip())
                return score
            except ValueError:
                logger.error(f"Erreur lors de la conversion du score : la réponse était '{ai_analysis}'")
                return "Erreur lors de l'analyse des compétences : score non valide."
        else:
            logger.error(f"Erreur lors de l'appel à l'API : {response.status_code} - {response.text}")
            return "Erreur lors de l'analyse des compétences."
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur lors de l'analyse des compétences : {str(e)}"

def upload_to_airtable(skill_assessment):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "fields": {
            "Description Compétences Etudiants": skill_assessment  
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return "Données envoyées avec succès."
        else:
            logger.error(f"Erreur lors de l'envoi : {response.status_code} - {response.text}")
            return f"Erreur lors de l'enregistrement : {response.status_code}"
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi : {str(e)}")
        return f"Erreur lors de l'enregistrement : {str(e)}"

def add_to_compatibility_table(student_id, skill_assessment, enterprise_skills, offer_id, compatibility_rate, student_name):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/TauxCompatibilité"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "fields": {
            "ID_Etu": student_id,
            "DescriptionEtu": skill_assessment,
            "ID_Offre": offer_id,
            "DescriptionOffre": enterprise_skills,
            "Taux de compatibilité" : compatibility_rate,
            "Nom": student_name
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            return "Données ajoutées avec succès !"
        else:
            logger.error(f"Erreur lors de l'ajout à la table de compatibilité : {response.status_code} - {response.text}")
            return f"Erreur lors de l'ajout à la table de compatibilité : {response.status_code}"
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout à Airtable : {str(e)}")
        return f"Erreur lors de l'ajout à Airtable : {str(e)}"

def parse_analysis(analysis):
    try:
        cleaned_analysis = re.sub(r'[^\d\s]', '', analysis)
        cleaned_analysis = cleaned_analysis.strip()

        numbers = re.findall(r'\d+', cleaned_analysis)

        if len(numbers) >= 2:
            pertinence = int(numbers[0])
            detail = int(numbers[1])
        else:
            pertinence = 0
            detail = 0

        last_number_index = cleaned_analysis.rfind(numbers[1])
        suggestions = analysis[last_number_index + len(numbers[1]):].strip() if last_number_index != -1 else ""
        
        return {
            "pertinence": pertinence,
            "detail": detail,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"Erreur lors du parsing de l'analyse: {str(e)}")
        return {"pertinence": 0, "detail": 0, "suggestions": ""}

def generate_follow_up_question(original_question, current_response, previous_response, suggestions):
    messages = [
        {"role": "system", "content": "Vous êtes un assistant IA expert en analyse de compétences. Votre tâche est de générer une question de suivi pertinente basée sur la question originale, la réponse actuelle de l'utilisateur, sa réponse précédente et les suggestions d'amélioration fournies."},
        {"role": "user", "content": f"Question originale : {original_question}\nRéponse actuelle : {current_response}\nSuggestions d'amélioration : {suggestions}\n\nVeuillez générer une question de suivi pertinente pour obtenir plus de détails ou de pertinence en fonction de ce qui à été dit, reprend les éléments de reponse de l'utilisateur pour lui poser une nouvelle question."}
    ]

    try:
        api_response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )
        
        if api_response.status_code == 200:
            data = api_response.json()
            follow_up_question = data['choices'][0]['message']['content']
            return follow_up_question
        else:
            return f"Pouvez-vous développer davantage votre réponse ? {suggestions}"
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la question de suivi: {str(e)}")
        return f"Pouvez-vous nous en dire plus sur {original_question.lower()} ?"
    
def manage_conversation_flow(question, response, history):
    analysis = call_api_for_response_analysis(question, response)
    current_question_index = 0
    
    if isinstance(analysis, dict) and "error" not in analysis:
        current_question_index = len(history) // 2

        if analysis["pertinence"] >= 70 or analysis["detail"] >= 70:
            if current_question_index < len(competence_questions) - 1:
                return competence_questions[current_question_index + 1], None
            else:
                all_responses = [item[0] for item in history[1::2]]
                skill_assessment = call_api_for_skill_assessment(all_responses)
                return f"Merci pour vos réponses ! Voici votre bilan de compétences :\n\n{skill_assessment}", skill_assessment
        else:
            follow_up_question = generate_follow_up_question(question, response, history[-3][0] if len(history) > 2 else "", analysis['suggestions'])
            return follow_up_question, None
    else:
        if current_question_index < len(competence_questions) - 1:
            return competence_questions[current_question_index + 1], None
        else:
            all_responses = [item[0] for item in history[1::2]]
            skill_assessment = call_api_for_skill_assessment(all_responses)
            return f"Désolé, nous avons rencontré un problème. Voici votre bilan basé sur les informations fournies :\n\n{skill_assessment}", skill_assessment

def submit_and_compare(skill_assessment_output):
    airtable_response = upload_to_airtable(skill_assessment_output)
    
    enterprise_descriptions = get_enterprise_descriptions()
    student_id, student_name = get_last_user_id()
    results = []
    
    for enterprise_name, enterprise_desc, offer_id in enterprise_descriptions:
        analysis = compare_skills_ai(skill_assessment_output, enterprise_desc)

        add_response = add_to_compatibility_table(student_id, skill_assessment_output, enterprise_desc, offer_id, analysis, student_name)
        
        results.append(f"Entreprise : {enterprise_name}\n{add_response}")

    output = "\n".join(results)
    return f"Résultat de l'enregistrement : {airtable_response}\n\n{output}"

def user(user_message, history):
    return "", history + [[user_message, None]]

def chatbot_response(message, history):
    if not history:
        # Première question
        return competence_questions[0], None
    elif len(history) == 1:
        # Première réponse de l'utilisateur
        return manage_conversation_flow(competence_questions[0], message, history)
    else:
        last_question = history[-2][1]  # La dernière question posée par le chatbot
        return manage_conversation_flow(last_question, message, history)
def bot(history):
    if history:
        bot_message, skill_assessment = chatbot_response(history[-1][0], history[:-1])
        history[-1][1] = bot_message
        return history, skill_assessment
    return [], None

def clear_chat():
    return [], None, None

def start_conversation():
    return [[None, competence_questions[0]]], None

def afficher_aide():
    return ("Pour construire votre bilan de compétences, veuillez répondre aux questions qui vous seront posées. "
            "N'hésitez pas à prendre votre temps et à relire chaque question si nécessaire. "
            "Si vous souhaitez refaire votre bilan, vous pouvez facilement effacer la conversation et recommencer.")

# Création du thème personnalisé
custom_theme = gr.themes.Base(
    primary_hue="blue",
    secondary_hue="purple",
    neutral_hue="gray",
    font=("Helvetica", "sans-serif"),
    font_mono=("Courier", "monospace"),
)

with gr.Blocks(theme=custom_theme) as demo:
    gr.Markdown("# Assistant d'évaluation des compétences")

    with gr.Accordion("Besoin d'aide ?", open=False):
        gr.Markdown(afficher_aide())
    
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Conversation", height=400)
            msg = gr.Textbox(
                label="Votre message",
                placeholder="Tapez votre message ici...",
                info="Décrivez vos compétences en détail"
            )
            clear = gr.Button("🚮 Effacer la conversation 🚮", variant="secondary")
        
        with gr.Column(scale=1):
            skill_assessment_output = gr.Textbox(
                label="Bilan des compétences",
                interactive=False,
                lines=10
            )
            submit_button = gr.Button("📤 Soumettre et comparer 📤", variant="primary")
            comparison_output = gr.Textbox(
                label="Résultat de la comparaison",
                interactive=False,
                lines=5
            )
            gr.Markdown(
                """<a href="https://votre-url-externe.com" target="_blank">
                <button style="width: 100%; padding: 10px; background-color: #C4DAFB; color: #3662E3; border: none; border-radius: 5px; font-family: 'Helvetica', sans-serif; font-weight: bold;">
                🔮 Voir offres 🔮
                </button>
                </a>""",
                elem_id="voir-offre-button"
            )

    gr.Markdown("© 2024 🪽 Albatross 🪽.")


    demo.load(start_conversation, inputs=None, outputs=[chatbot, skill_assessment_output])
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, [chatbot], [chatbot, skill_assessment_output]
    )
    clear.click(clear_chat, None, [chatbot, skill_assessment_output, comparison_output], queue=False)
    submit_button.click(submit_and_compare, skill_assessment_output, comparison_output)

if __name__ == "__main__":
    demo.launch()
