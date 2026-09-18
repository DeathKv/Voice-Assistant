import asyncio
import json
from gemini_client import main as gemini_main, historico
from web_server import start_server
from memoria_manager import salvar_sessao, salvar_historico
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

async def gerar_resumo_sessao():
    """Pede ao Gemini um resumo do que foi feito na sessão."""
    if not historico:
        print("📝 Nenhuma conversa para resumir.")
        return

    trocas = ""
    for h in historico:
        if h.get("user"): trocas += f"Usuário: {h['user']}\n"
        if h.get("aria"): trocas += f"Assistente: {h['aria']}\n"

    prompt = f"""Faça um resumo curto (1 a 3 frases) do que aconteceu nesta sessão de conversa.
O resumo será usado como memória para sessões futuras.
Seja objetivo e mencione os assuntos principais abordados.

Conversa:
{trocas}

Resumo:"""

    # Client separado, sem tools
    client_texto = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    for tentativa in range(1, 4):
        try:
            print(f"   💭 Gerando resumo (tentativa {tentativa}/3)...")
            loop = asyncio.get_event_loop()
            resposta = await loop.run_in_executor(
                None,
                lambda: client_texto.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                )
            )
            resumo = resposta.text.strip()
            salvar_sessao(resumo)
            print(f"📝 Resumo salvo: {resumo}")
            return
        except Exception as e:
            print(f"⚠️ Tentativa {tentativa} falhou: {e}")
            if tentativa < 3:
                print(f"   ⏳ Aguardando 3s...")
                await asyncio.sleep(3)

    print("⚠️ Não foi possível salvar o resumo após 3 tentativas.")

async def run_everything():
    await asyncio.gather(start_server(), gemini_main())

if __name__ == "__main__":
    try:
        asyncio.run(run_everything())
    except KeyboardInterrupt:
        print("\n\n⏳ Encerrando — salvando memória da sessão...")
        salvar_historico(historico)
        try:
            asyncio.run(gerar_resumo_sessao())
        except Exception as e:
            print(f"⚠️ Erro ao gerar resumo: {e}")
        print("👋 Encerrado.")