import os
import requests
from google import genai
import json
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

IG_TOKEN = os.environ['IG_ACCESS_TOKEN']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
YOUTUBE_TOKEN_JSON = os.environ.get('YOUTUBE_TOKEN')

client = genai.Client(api_key=GEMINI_API_KEY)

def otimizar_com_gemini(legenda_original):
    prompt = f"""
    Você é o estrategista do canal Cortes e Política (focado em debates políticos, entrevistas, bastidores do poder e atualidades).
    Transforme a legenda abaixo em metadados otimizados para um YouTube Short.
    Retorne APENAS um formato JSON válido com as seguintes chaves:
    "titulo" (curto, instigante ou polêmico, max 80 caracteres. OBRIGATÓRIO: inclua exatamente 3 hashtags no final, ex: #Politica #Debate #Noticias),
    "descricao" (atraente, contextualizada e com hashtags extras),
    "tags" (lista de palavras-chave virais separadas por vírgula).
    
    Legenda original: {legenda_original}
    """
    
    for tentativa in range(3):
        try:
            resposta = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt
            )
            texto_json = resposta.text.replace('```json', '').replace('```', '').strip()
            return json.loads(texto_json)
            
        except Exception as e:
            print(f"ERRO DA IA (Tentativa {tentativa + 1}/3): {e}")
            if tentativa < 2:
                time.sleep(15)
            else:
                return {
                    "titulo": "Bastidores da Política #Politica #Brasil #Shorts", 
                    "descricao": legenda_original, 
                    "tags": "politica, debate, brasil, noticias"
                }

def upload_para_youtube(titulo, descricao, tags, arquivo_video):
    if not YOUTUBE_TOKEN_JSON:
        print("ERRO: YOUTUBE_TOKEN não encontrado nas variáveis de ambiente.")
        return

    token_info = json.loads(YOUTUBE_TOKEN_JSON)
    creds = Credentials.from_authorized_user_info(token_info)
    youtube = build('youtube', 'v3', credentials=creds)
    
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(',')]
        
    corpo = {
        'snippet': {
            'title': titulo,
            'description': descricao,
            'tags': tags,
            'categoryId': '25'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }
    
    media = MediaFileUpload(arquivo_video, chunksize=-1, resumable=True)
    
    print(f"Iniciando upload para o YouTube: {titulo}")
    request = youtube.videos().insert(
        part=','.join(corpo.keys()),
        body=corpo,
        media_body=media
    )
    response = request.execute()
    print(f"✅ Upload concluído! URL do vídeo: https://youtube.com/shorts/{response['id']}")

def checar_novo_reel():
    url = f"https://graph.instagram.com/me/media?fields=id,media_type,media_url,caption&access_token={IG_TOKEN}"
    resposta = requests.get(url).json()

    if 'data' not in resposta or len(resposta['data']) == 0:
        print("Nenhum post encontrado ou acesso negado.")
        return

    ultimo_post = resposta['data'][0]
    post_id = ultimo_post['id']

    arquivo_id = "ultimo_id.txt"
    if os.path.exists(arquivo_id):
        with open(arquivo_id, "r") as f:
            ultimo_id_salvo = f.read().strip()
        if post_id == ultimo_id_salvo:
            print("⚠️ Este Reel já foi publicado no YouTube. A aguardar novo conteúdo...")
            return

    if ultimo_post.get('media_type') != 'VIDEO':
        print("O último post não é um vídeo (Reel). Ignorando.")
        return

    legenda = ultimo_post.get('caption', 'Bastidores da política #shorts')
    print("Enviando legenda para a IA otimizar...")
    seo_youtube = otimizar_com_gemini(legenda)
    
    print(f"🎯 Título gerado: {seo_youtube['titulo']}")
    
    video_url = ultimo_post['media_url']
    video_data = requests.get(video_url).content
    arquivo_local = "reel_atual.mp4"
    
    with open(arquivo_local, "wb") as f:
        f.write(video_data)
        
    print("✅ Vídeo baixado. Iniciando envio para o YouTube...")
    upload_para_youtube(
        titulo=seo_youtube['titulo'],
        descricao=seo_youtube['descricao'],
        tags=seo_youtube['tags'],
        arquivo_video=arquivo_local
    )

    with open(arquivo_id, "w") as f:
        f.write(post_id)
    print("🧠 ID do vídeo guardado na memória com sucesso!")

if __name__ == "__main__":
    checar_novo_reel()
