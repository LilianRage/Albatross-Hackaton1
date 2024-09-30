import requests
import json
import re
import gradio as gr
import logging

# Configuration du logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Remplacez par votre clé API
OPENROUTER_API_KEY = "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"
YOUR_SITE_URL = "votre-site.com"  # Remplacez par votre URL si nécessaire
YOUR_APP_NAME = "MonChatbot"

# Variables pour stocker les informations
user_info = {"ville": None, "études": None}

def extract_info_from_summary(summary):
    # Utilisation d'expressions régulières pour extraire la ville et les études
    location_match = re.search(r"Vous habitez (.*?) et", summary)
    studies_match = re.search(r"et vous avez effectué des études en (.*?)[.]", summary)

    if location_match:
        user_info['ville'] = location_match.group(1)
    if studies_match:
        user_info['études'] = studies_match.group(1)

    # Afficher les informations dans la console
    print(json.dumps(user_info, indent=2))

def chatbot_response(message, history, pdf_text=None, image_path=None):
    global user_info

    # Préparer les messages pour l'API
    messages = [
        {"role": "system", "content": """Vous êtes un recruteur dans le domaine des ressources humaines (RH). 
        Votre tâche est de poser deux questions importantes à l'utilisateur : où il habite et quelles études il a faites. 
        Si l'utilisateur a déjà fourni une réponse, passez à la question suivante. 
        Uniquement une fois que toutes ces informations ont été obtenues, terminez par : "Albatross vous remercie ! Voici les informations que vous avez fournies :". 
        Ensuite, l'IA doit formuler un résumé clair et concis, en récapitulant les réponses de l'utilisateur, par exemple : 
        "Vous habitez [lieu] et vous avez effectué des études en [domaine/études]". Cela permettra à l'IA d'offrir une réponse polie et professionnelle, tout en confirmant les informations collectées. 
        Ne terminez par le message de remerciement qu'une fois que toutes les informations sont complètes."""},
        {"role": "user", "content": message}
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
                "model": "nousresearch/hermes-3-llama-3.1-405b:free",
                "messages": messages
            })
        )

        if response.status_code == 200:
            data = response.json()
            bot_message = data['choices'][0]['message']['content']
            print("Réponse de l'API :", json.dumps(data, indent=2))

            # Détecter si le message contient le résumé final
            if "Albatross vous remercie" in bot_message:
                extract_info_from_summary(bot_message)

            return bot_message
        else:
            return f"Erreur {response.status_code}: {response.text}"

    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur: {str(e)}"

def user(user_message, history, pdf_text, image):
    return "", history + [[user_message, None]], pdf_text, image

def bot(history, pdf_text, image):
    if history:
        bot_message = chatbot_response(history[-1][0], history[:-1], pdf_text, image)
        history[-1][1] = bot_message
        return history
    return []

def clear_chat():
    global user_info
    user_info = {"ville": None, "études": None}
    return [], None, None

# Créer l'interface Gradio
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    chatbot = gr.Chatbot(label="Historique de la conversation")
    msg = gr.Textbox(label="Votre message", placeholder="Tapez votre message ici...")
    clear = gr.Button("Effacer la conversation")
    pdf_text = gr.State()

    msg.submit(user, [msg, chatbot, pdf_text], [msg, chatbot, pdf_text], queue=False).then(
        bot, [chatbot, pdf_text], chatbot
    )
    clear.click(clear_chat, None, [chatbot, pdf_text], queue=False)

demo.launch()
