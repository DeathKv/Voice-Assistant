import asyncio
import sounddevice as sd
import numpy as np
from google import genai
from web_server import notify_frontend
from web_server import broadcast
from google.genai import types
from dotenv import load_dotenv
import os
import soundfile as sf
import acoes
from acoes.registro import obter_ferramentas, executar
from acoes.contexto import obter_contexto_completo

load_dotenv()

MODEL   = "gemini-3.8-live"
NOME    = os.getenv("NOME_ASSISTENTE", "Aria")
COMANDO = os.getenv("COMANDO_ATIVACAO", "System Call")
VOZ     = os.getenv("VOZ_NOME",    "Charon")   # 👈 NOVO
IDIOMA  = os.getenv("VOZ_IDIOMA",  "en-US")    # 👈 NOVO
CLIENT  = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Carrega todos os módulos de ações automaticamente
acoes.carregar_todos()

# ── Memória da conversa ──────────────────────────────────────────
historico = []

def montar_system_instruction(modo_comando=False):
    contexto = obter_contexto_completo()   
    base = (
        f"{contexto}\n\n"  # 👈 injeta aqui
        f"Você é {NOME}, uma assistente pessoal de inteligência artificial "
        "inspirada no J.A.R.V.I.S. do Homem de Ferro. "
        "Sua personalidade é: extremamente educada, formal, calma, sofisticada, "
        "levemente sarcástica quando apropriado, sempre eficiente e direta. "
        "Trate o usuário como 'senhor' ocasionalmente. "
        "Suas respostas devem ser curtas, precisas e elegantes — nunca prolixas. "
        "Você deve SEMPRE responder em português brasileiro, "
        "mesmo que a pergunta seja em outro idioma. "
        "Nunca quebre o personagem."
    )

    if modo_comando:
        base += (
            "\n\nVocê está em MODO COMANDO. O usuário vai pedir para você "
            "executar uma ação no PC dele ou na casa dele. "
            "Use as ferramentas disponíveis. "
            "Após executar, confirme brevemente o que fez de forma elegante."
        )

    if historico:
        base += "\n\nHistórico recente da conversa:\n"
        for h in historico[-10:]:
            if h.get("user"): base += f"Usuário disse: {h['user']}\n"
            if h.get("aria"): base += f"{NOME} respondeu: {h['aria']}\n"

    return base


# ── Som de ativação ──────────────────────────────────────────────
def som_ativacao():
    """Toca o som de ativação configurado no .env"""
    arquivo = os.getenv("SOM_ATIVACAO", "")

    if arquivo and os.path.exists(arquivo):
        try:
            dados, sample_rate = sf.read(arquivo, dtype='int16')

            # Garante que é mono
            if dados.ndim > 1:
                dados = dados[:, 0]

            sd.play(dados, sample_rate)
            sd.wait()
            return
        except Exception as e:
            print(f"⚠️ Erro ao tocar {arquivo}: {e}")

    # Fallback: bip simples caso não tenha arquivo
    sr = 24000
    duracao = 0.3
    t = np.linspace(0, duracao, int(sr * duracao), False)
    som = np.sin(2 * np.pi * 880 * t) * 0.2
    envelope = np.exp(-t * 5)
    audio = (som * envelope * 32767).astype(np.int16)
    sd.play(audio, sr)
    sd.wait()



# ── Config (com ou sem ferramentas) ──────────────────────────────
def montar_config(com_ferramentas=False):
    config_dict = dict(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOZ),
            ),
            language_code=IDIOMA,
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                silence_duration_ms=int(os.getenv("VAD_SILENCE_MS", "600")),
                prefix_padding_ms=int(os.getenv("VAD_PREFIX_MS",  "20")),
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction=types.Content(
            parts=[types.Part(text=montar_system_instruction(modo_comando=com_ferramentas))],
            role="user"
        )
    )

    if com_ferramentas:
        config_dict["tools"] = obter_ferramentas()  # 👈 vem do registro.py

    return types.LiveConnectConfig(**config_dict)


# ── Turno NORMAL (só conversa, sem ferramentas) ──────────────────
async def um_turno():
    chunks_audio   = []
    texto_usuario  = ""
    texto_aria     = ""
    ativou_comando = asyncio.Event()

    async with CLIENT.aio.live.connect(model=MODEL, config=montar_config(False)) as session:
        resposta_completa = asyncio.Event()

        async def enviar_mic():
            loop = asyncio.get_event_loop()
            fila_mic = asyncio.Queue()

            def callback(indata, frames, time, status):
                asyncio.run_coroutine_threadsafe(fila_mic.put(indata.tobytes()), loop)

            with sd.InputStream(samplerate=16000, channels=1,
                                dtype="int16", blocksize=1024, callback=callback):
                while not resposta_completa.is_set():
                    try:
                        dados = await asyncio.wait_for(fila_mic.get(), timeout=0.1)
                        await session.send_realtime_input(
                            audio=types.Blob(data=dados, mime_type="audio/pcm;rate=16000")
                        )
                    except asyncio.TimeoutError:
                        continue

        async def receber():
            nonlocal texto_usuario, texto_aria

            async for resposta in session.receive():
                sc = resposta.server_content
                if not sc:
                    continue

                # Áudio da resposta
                if sc.model_turn:
                    for parte in sc.model_turn.parts:
                        if parte.inline_data and parte.inline_data.data:
                            audio = np.frombuffer(parte.inline_data.data, dtype=np.int16)
                            chunks_audio.append(audio)

                # Transcrição do usuário
                if sc.input_transcription and sc.input_transcription.text:
                    texto_usuario += sc.input_transcription.text
                    print(f"🗣️  Você: {sc.input_transcription.text}")
                    await notify_frontend("ouvindo", usuario=texto_usuario)

                    # Detecta frase de ativação
                    if COMANDO.lower() in texto_usuario.lower():
                        print(f"⚡ Frase de ativação detectada: \"{COMANDO}\"")
                        ativou_comando.set()
                        resposta_completa.set()

                # Transcrição da Aria
                if sc.output_transcription and sc.output_transcription.text:
                    texto_aria += sc.output_transcription.text
                    await notify_frontend("falando", aria=texto_aria)

                if sc.turn_complete:
                    resposta_completa.set()

        await notify_frontend("ouvindo")
        await asyncio.gather(enviar_mic(), receber())

    # Se detectou a frase de ativação, retorna "comando"
    if ativou_comando.is_set():
        return "comando"

    # Fluxo normal
    await notify_frontend("pensando")

    if texto_usuario or texto_aria:
        historico.append({"user": texto_usuario.strip(), "aria": texto_aria.strip()})
        if texto_aria:
            print(f"🤖 {NOME}: {texto_aria.strip()}")

    if chunks_audio:
        await notify_frontend("falando", aria=texto_aria)
        await asyncio.sleep(0.15)
        audio_total = np.concatenate(chunks_audio)
        with sd.OutputStream(samplerate=24000, channels=1, dtype="int16") as stream:
            stream.write(audio_total)

    await notify_frontend("ocioso")
    return "normal"


# ── Turno COMANDO (com ferramentas ativadas) ─────────────────────
async def um_turno_comando():
    chunks_audio  = []
    texto_usuario = ""
    texto_aria    = ""

    async with CLIENT.aio.live.connect(model=MODEL, config=montar_config(True)) as session:
        resposta_completa = asyncio.Event()
        parar_mic = asyncio.Event()

        async def enviar_mic():
            loop = asyncio.get_event_loop()
            fila_mic = asyncio.Queue()

            def callback(indata, frames, time, status):
                asyncio.run_coroutine_threadsafe(fila_mic.put(indata.tobytes()), loop)

            with sd.InputStream(samplerate=16000, channels=1,
                                dtype="int16", blocksize=1024, callback=callback):
                while not resposta_completa.is_set() and not parar_mic.is_set():
                    try:
                        dados = await asyncio.wait_for(fila_mic.get(), timeout=0.1)
                        if not parar_mic.is_set():
                            await session.send_realtime_input(
                                audio=types.Blob(data=dados, mime_type="audio/pcm;rate=16000")
                            )
                    except asyncio.TimeoutError:
                        continue

        async def receber():
            nonlocal texto_usuario, texto_aria
            ferramenta_pendente = False

            async for resposta in session.receive():
                sc = resposta.server_content

                # Áudio da resposta
                if sc and sc.model_turn:
                    for parte in sc.model_turn.parts:
                        if parte.inline_data and parte.inline_data.data:
                            audio = np.frombuffer(parte.inline_data.data, dtype=np.int16)
                            chunks_audio.append(audio)

                # Transcrição do usuário
                if sc and sc.input_transcription and sc.input_transcription.text:
                    texto_usuario += sc.input_transcription.text
                    print(f"🗣️  Você: {sc.input_transcription.text}")
                    await notify_frontend("comando", usuario=texto_usuario)

                # Transcrição da Aria
                if sc and sc.output_transcription and sc.output_transcription.text:
                    texto_aria += sc.output_transcription.text
                    await notify_frontend("falando", aria=texto_aria)

                # Chamada de ferramenta
                if resposta.tool_call:
                    parar_mic.set()
                    ferramenta_pendente = True
                    for fc in resposta.tool_call.function_calls:
                        await notify_frontend("pensando")
                        resultado = executar(fc.name, dict(fc.args))  # 👈 vem do registro.py
                        print(f"✅ Resultado: {resultado}")
                        await session.send_tool_response(
                            function_responses=[types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": resultado}
                            )]
                        )

                # Fim do turno
                if sc and sc.turn_complete:
                    if ferramenta_pendente:
                        ferramenta_pendente = False
                        continue
                    print("✅ Comando executado!")
                    resposta_completa.set()

        await notify_frontend("comando")
        await asyncio.gather(enviar_mic(), receber())
        await notify_frontend("pensando")

    if texto_usuario or texto_aria:
        historico.append({"user": texto_usuario.strip(), "aria": texto_aria.strip()})
        if texto_aria:
            print(f"🤖 {NOME}: {texto_aria.strip()}")

    if chunks_audio:
        await notify_frontend("falando", aria=texto_aria)
        await asyncio.sleep(0.15)
        audio_total = np.concatenate(chunks_audio)
        with sd.OutputStream(samplerate=24000, channels=1, dtype="int16") as stream:
            stream.write(audio_total)

    await notify_frontend("ocioso")


# ── Loop principal ───────────────────────────────────────────────
async def main():
    print(f"🚀 Assistente {NOME} iniciado!")
    print(f"⚡ Frase de ativação de comando: \"{COMANDO}\"")
    print("💬 Fale sua pergunta. Ctrl+C para sair.\n")

    while True:
        print("👂 Ouvindo... (fale agora)")
        resultado = await um_turno()

        if resultado == "comando":
            som_ativacao()
            await notify_frontend("comando")
            print(f"⚡ MODO COMANDO ATIVADO — diga o comando...")
            await um_turno_comando()

        print("🔄 Pronto para a próxima pergunta!\n")