import requests
import json
import gradio as gr
import logging

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
        "sort[0][field]": "ID_Etu",  # Trie par l'ID de l'étudiant
        "sort[0][direction]": "desc",  # Trie de manière décroissante (du plus récent au plus ancien)
        "maxRecords": 1  # Limite à un enregistrement (le plus récent)
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if len(data['records']) > 0:
                last_record = data['records'][0]  # Premier enregistrement, car trié par "desc"
                last_user_id = last_record['fields'].get('ID_Etu', 'Aucun ID trouvé')
                
                #print(f"Le dernier ID utilisateur est : {last_user_id}")
                return last_user_id
            else:
                #print("Aucun enregistrement trouvé.")
                return None
        else:
            logger.error(f"Erreur lors de la récupération des ID : {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des ID : {str(e)}")
        return None

# Appel de la fonction pour afficher l'ID dans le terminal
get_last_user_id()


competence_responses = []
current_question_index = 0

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
        descriptions = [(record['fields'].get('Nom', f"Entreprise {i+1}"), record['fields']['Description entreprises']) for i, record in enumerate(data['records'])]
        return descriptions
    else:
        logger.error(f"Erreur lors de la récupération des descriptions d'entreprises : {response.status_code} - {response.text}")
        return []

def compare_skills_ai(student_skills, enterprise_skills):
    messages = [
        {"role": "system", "content": "Vous êtes un expert en recrutement chargé d'évaluer la correspondance entre les compétences d'un étudiant et celles requises par une entreprise. Votre tâche est d'analyser ces compétences et de fournir une valeur de correspondance entre l'étudiant et les différentes entreprise, je veux simplement la note global pour chaque entreprise. Tenez compte des compétences similaires ou complémentaires, pas seulement des correspondances exactes."},
        {"role": "user", "content": f"Compétences de l'étudiant :\n{student_skills}\n\nCompétences requises par l'entreprise :\n{enterprise_skills}\n\nVeuillez analyser ces compétences et fournir un chiffre entre 0 et 100 pour la correspondance entre l'etudiant et l'entreprise afin de voir le taux de compatibilité entre l'etudiants et les différentes entreprises. en détaille rien, juste la note global sans le détail. Ecrit juste le nom de l'entreprise puis le score"}
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
            return ai_analysis
        else:
            logger.error(f"Erreur lors de l'appel à l'API : {response.status_code} - {response.text}")
            return "Erreur lors de l'analyse des compétences."
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur lors de l'analyse des compétences : {str(e)}"

def compare_with_enterprises(skill_assessment):
    enterprise_descriptions = get_enterprise_descriptions()
    results = []
    
    for enterprise_name, enterprise_desc in enterprise_descriptions:
        analysis = compare_skills_ai(skill_assessment, enterprise_desc)
        results.append((enterprise_name, analysis))
    
    output = ""
    for enterprise_name, analysis in results:
        output += f"Analyse pour {enterprise_name}:\n{analysis}\n\n"
    
    print(output)
    return output

def chatbot_response(message, history):
    global competence_responses, current_question_index
    
    competence_responses.append(message)
    current_question_index += 1
    
    if current_question_index < len(competence_questions):
        return competence_questions[current_question_index], None
    else:
        skill_assessment = call_api_for_skill_assessment(competence_responses)
        return f"Merci pour vos réponses ! Voici votre bilan de compétences :\n\n{skill_assessment}", skill_assessment

def start_conversation():
    global current_question_index, competence_responses
    current_question_index = 0
    competence_responses = []
    return [[None, competence_questions[0]]], None

def user(user_message, history):
    return "", history + [[user_message, None]]

def bot(history):
    if history:
        bot_message, skill_assessment = chatbot_response(history[-1][0], history[:-1])
        history[-1][1] = bot_message
        return history, skill_assessment
    return [], None

def clear_chat():
    global competence_responses, current_question_index
    competence_responses = []
    current_question_index = 0
    return [], None, None

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
            return "Données envoyées avec succès à Airtable."
        else:
            logger.error(f"Erreur lors de l'envoi à Airtable : {response.status_code} - {response.text}")
            return f"Erreur lors de l'enregistrement dans Airtable : {response.status_code}"
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi à Airtable : {str(e)}")
        return f"Erreur lors de l'enregistrement dans Airtable : {str(e)}"

def submit_and_compare(skill_assessment_output):
    # Remplissage de la BDD Airtable avec le bilan des compétences
    airtable_response = upload_to_airtable(skill_assessment_output)
    
    # Comparaison avec les entreprises
    comparison_result = compare_with_enterprises(skill_assessment_output)
    
    return f"Résultat de l'enregistrement dans Airtable: {airtable_response}\n\n{comparison_result}"

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    chatbot = gr.Chatbot(label="Historique de la conversation")
    msg = gr.Textbox(label="Votre message", placeholder="Tapez votre message ici...")
    clear = gr.Button("Effacer la conversation")
    skill_assessment_output = gr.Textbox(label="Bilan des compétences", interactive=False)
    submit_button = gr.Button("Soumettre et comparer")
    comparison_output = gr.Textbox(label="Résultat de la comparaison", interactive=False)

    demo.load(start_conversation, inputs=None, outputs=[chatbot, skill_assessment_output])
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, [chatbot], [chatbot, skill_assessment_output]
    )
    clear.click(clear_chat, None, [chatbot, skill_assessment_output, comparison_output], queue=False)
    submit_button.click(submit_and_compare, skill_assessment_output, comparison_output)

demo.launch()