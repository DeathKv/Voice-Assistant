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
VOZ     = os.getenv("VOZ_NOME",    "Charon")
IDIOMA  = os.getenv("VOZ_IDIOMA",  "en-US")
MIC_GAIN = float(os.getenv("MIC_GAIN", "2.0"))
CLIENT  = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

acoes.carregar_todos()

historico = []

def amplificar(dados_bytes: bytes) -> bytes:
    """Amplifica o áudio PCM pelo fator MIC_GAIN."""
    if MIC_GAIN == 1.0:
        return dados_bytes
    audio = np.frombuffer(dados_bytes, dtype=np.int16).astype(np.float32)
    audio *= MIC_GAIN
    audio = np.clip(audio, -32768, 32767)  # evita distorção
    return audio.astype(np.int16).tobytes()

def montar_system_instruction(modo_comando=False):
    contexto = obter_contexto_completo()
    base = (
        f"{contexto}\n\n"
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


# ── Som de ativação (NÃO bloqueia o event loop) ─────────────────
def _tocar_som_sync():
    """Roda em thread separada para não travar o asyncio."""
    arquivo = os.getenv("SOM_ATIVACAO", "")
    if arquivo and os.path.exists(arquivo):
        try:
            dados, sample_rate = sf.read(arquivo, dtype='int16')
            if dados.ndim > 1:
                dados = dados[:, 0]
            sd.play(dados, sample_rate)
            sd.wait()
            return
        except Exception as e:
            print(f"⚠️ Erro ao tocar {arquivo}: {e}")
    # Fallback bip
    sr = 24000
    t  = np.linspace(0, 0.3, int(sr * 0.3), False)
    som = np.sin(2 * np.pi * 880 * t) * 0.2
    audio = (som * np.exp(-t * 5) * 32767).astype(np.int16)
    sd.play(audio, sr)
    sd.wait()

async def som_ativacao():
    """Toca o som sem bloquear o event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _tocar_som_sync)


# ── Config ───────────────────────────────────────────────────────
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
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
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
        config_dict["tools"] = obter_ferramentas()
    return types.LiveConnectConfig(**config_dict)


# ── Reprodutor de áudio em streaming ────────────────────────────
async def reproduzir_streaming(fila_audio: asyncio.Queue, texto_aria_ref: list):
    """
    Toca cada chunk de áudio conforme chega na fila.
    Não espera o turno terminar — elimina o delay de resposta.
    """
    loop = asyncio.get_event_loop()
    stream = sd.OutputStream(samplerate=24000, channels=1, dtype="int16")
    stream.start()
    primeiro_chunk = True

    try:
        while True:
            chunk = await fila_audio.get()

            if chunk is None:
                # Sinal de fim de turno
                break

            if primeiro_chunk:
                # Notifica frontend assim que o PRIMEIRO chunk chegar
                await notify_frontend("falando", aria=texto_aria_ref[0])
                primeiro_chunk = False

            # Toca sem bloquear o event loop
            await loop.run_in_executor(None, stream.write, chunk)

    finally:
        stream.stop()
        stream.close()


# ── Turno NORMAL ─────────────────────────────────────────────────
async def um_turno():
    fila_audio        = asyncio.Queue()
    texto_aria_ref    = [""]
    texto_usuario     = ""
    texto_aria        = ""
    ativou_comando    = asyncio.Event()
    resposta_completa = asyncio.Event()

    async with CLIENT.aio.live.connect(model=MODEL, config=montar_config(False)) as session:

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
                        dados = amplificar(dados)
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

                # Áudio → fila streaming
                if sc.model_turn:
                    for parte in sc.model_turn.parts:
                        if parte.inline_data and parte.inline_data.data:
                            audio = np.frombuffer(parte.inline_data.data, dtype=np.int16)
                            await fila_audio.put(audio)

                # Transcrição do usuário
                if sc.input_transcription and sc.input_transcription.text:
                    texto_usuario += sc.input_transcription.text
                    print(f"🗣️  Você: {sc.input_transcription.text}")
                    await notify_frontend("ouvindo", usuario=texto_usuario)

                    # Detectou palavra-chave → sai IMEDIATAMENTE
                    if COMANDO.lower() in texto_usuario.lower():
                        print(f"⚡ Ativação detectada: \"{COMANDO}\"")
                        await notify_frontend("comando")
                        ativou_comando.set()
                        resposta_completa.set()
                        await fila_audio.put(None)
                        return  # ← SAI do loop na hora, sem esperar Gemini

                # Transcrição da Aria
                if sc.output_transcription and sc.output_transcription.text:
                    texto_aria += sc.output_transcription.text
                    texto_aria_ref[0] = texto_aria
                    await notify_frontend("falando", aria=texto_aria)

                # Fim de turno normal
                if sc.turn_complete:
                    await fila_audio.put(None)
                    resposta_completa.set()
                    return  # ← SAI do loop também aqui

        await notify_frontend("ouvindo")

        # Tasks separadas para poder cancelar o mic quando receber() terminar
        task_mic  = asyncio.create_task(enviar_mic())
        task_rec  = asyncio.create_task(receber())
        task_play = asyncio.create_task(reproduzir_streaming(fila_audio, texto_aria_ref))

        # Espera receber() terminar (ela controla o fluxo)
        await task_rec

        # Cancela mic e player imediatamente após receber() sair
        task_mic.cancel()
        task_play.cancel()
        await asyncio.gather(task_mic, task_play, return_exceptions=True)

    if ativou_comando.is_set():
        return "comando"

    if texto_usuario or texto_aria:
        historico.append({"user": texto_usuario.strip(), "aria": texto_aria.strip()})
        if texto_aria:
            print(f"🤖 {NOME}: {texto_aria.strip()}")

    await notify_frontend("ocioso")
    return "normal"


# ── Turno COMANDO ────────────────────────────────────────────────
async def um_turno_comando():
    fila_audio     = asyncio.Queue()
    texto_aria_ref = [""]
    texto_usuario  = ""
    texto_aria     = ""

    async with CLIENT.aio.live.connect(model=MODEL, config=montar_config(True)) as session:
        resposta_completa = asyncio.Event()
        parar_mic         = asyncio.Event()

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
                        dados = amplificar(dados)
                        if not parar_mic.is_set():
                            await session.send_realtime_input(
                                audio=types.Blob(data=dados, mime_type="audio/pcm;rate=16000")
                            )
                    except asyncio.TimeoutError:
                        continue

        async def receber():
            nonlocal texto_usuario, texto_aria

            # ── FASE 1: Ouvir o usuário → esperar tool_call ─────
            print("📡 Fase 1: Aguardando comando do usuário...")

            async for resposta in session.receive():
                sc = resposta.server_content

                # Áudio (caso Gemini fale algo antes do tool call)
                if sc and sc.model_turn:
                    for parte in sc.model_turn.parts:
                        if parte.inline_data and parte.inline_data.data:
                            audio = np.frombuffer(parte.inline_data.data, dtype=np.int16)
                            await fila_audio.put(audio)

                # Transcrição do usuário
                if sc and sc.input_transcription and sc.input_transcription.text:
                    texto_usuario += sc.input_transcription.text
                    print(f"🗣️  Você: {sc.input_transcription.text}")
                    await notify_frontend("comando", usuario=texto_usuario)

                # Transcrição da Aria
                if sc and sc.output_transcription and sc.output_transcription.text:
                    texto_aria += sc.output_transcription.text
                    texto_aria_ref[0] = texto_aria
                    await notify_frontend("falando", aria=texto_aria)

                # Tool call → executa e envia resposta
                if resposta.tool_call:
                    parar_mic.set()
                    await notify_frontend("pensando")
                    print(f"🔧 Tool call recebido!")
                    for fc in resposta.tool_call.function_calls:
                        print(f"   → {fc.name}({dict(fc.args)})")
                        resultado = executar(fc.name, dict(fc.args))
                        print(f"   ✅ Resultado: {resultado}")
                        await session.send_tool_response(
                            function_responses=[types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": resultado}
                            )]
                        )
                    print("📤 Tool response enviado — entrando na Fase 2...")
                    break  # ← SAI do primeiro loop para entrar no segundo

                # Se Gemini terminou sem tool call (respondeu com voz normal)
                if sc and sc.turn_complete:
                    print("🔔 Turno encerrado sem tool call.")
                    await fila_audio.put(None)
                    resposta_completa.set()
                    return

            # ── FASE 2: Receber confirmação de áudio pós-tool ───
            print("📡 Fase 2: Aguardando áudio de confirmação...")
            recebeu_audio = False
            tentativas = 0

            while not recebeu_audio and tentativas < 5:
                tentativas += 1
                print(f"   📡 receive() tentativa #{tentativas}...")

                async for resposta in session.receive():
                    sc = resposta.server_content

                    # Áudio da confirmação
                    if sc and sc.model_turn:
                        for parte in sc.model_turn.parts:
                            if parte.inline_data and parte.inline_data.data:
                                audio = np.frombuffer(parte.inline_data.data, dtype=np.int16)
                                await fila_audio.put(audio)
                                recebeu_audio = True
                                print(f"🔊 Áudio ({len(parte.inline_data.data)} bytes)")

                    # Transcrição da confirmação
                    if sc and sc.output_transcription and sc.output_transcription.text:
                        texto_aria += sc.output_transcription.text
                        texto_aria_ref[0] = texto_aria
                        print(f"💬 Aria: {sc.output_transcription.text}")
                        await notify_frontend("falando", aria=texto_aria)

                    # turn_complete
                    if sc and sc.turn_complete:
                        if recebeu_audio:
                            print("✅ Confirmação concluída!")
                            await fila_audio.put(None)
                            resposta_completa.set()
                            return
                        else:
                            print("   ↩ turn_complete sem áudio — tentando novamente...")
                            break  # sai do async for, mas o while tenta de novo

            # Se esgotou tentativas sem receber áudio
            print("⚠️ Gemini não enviou áudio de confirmação.")
            await fila_audio.put(None)
            resposta_completa.set()

        await notify_frontend("comando")

        # Tasks canceláveis
        task_mic  = asyncio.create_task(enviar_mic())
        task_rec  = asyncio.create_task(receber())
        task_play = asyncio.create_task(reproduzir_streaming(fila_audio, texto_aria_ref))

        # Espera receber() terminar
        await task_rec
        print("🏁 receber() terminou — aguardando player...")

        # Espera player tocar toda a confirmação
        await task_play
        print("🏁 Player terminou — cancelando mic...")

        # Cancela mic
        task_mic.cancel()
        await asyncio.gather(task_mic, return_exceptions=True)

    if texto_usuario or texto_aria:
        historico.append({"user": texto_usuario.strip(), "aria": texto_aria.strip()})
        if texto_aria:
            print(f"🤖 {NOME}: {texto_aria.strip()}")

    await notify_frontend("ocioso")
    print("✅ Modo comando encerrado — voltando ao normal.")

# ── Loop principal ───────────────────────────────────────────────
async def main():
    print(f"🚀 Assistente {NOME} iniciado!")
    print(f"⚡ Frase de ativação: \"{COMANDO}\"")
    print("💬 Fale sua pergunta. Ctrl+C para sair.\n")

    while True:
        print("👂 Ouvindo... (fale agora)")
        resultado = await um_turno()

        if resultado == "comando":
            await som_ativacao()           # ← não bloqueia mais
            print(f"⚡ MODO COMANDO — diga o comando...")
            await um_turno_comando()

        print("🔄 Pronto para a próxima pergunta!\n")