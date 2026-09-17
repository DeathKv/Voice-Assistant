import pyautogui
import subprocess
import os
import datetime
from acoes.registro import registrar_acao

pyautogui.FAILSAFE = True

PROGRAMAS = {
    "chrome": "chrome", "google": "chrome", "navegador": "chrome",
    "notepad": "notepad", "bloco de notas": "notepad",
    "calculadora": "calc", "explorer": "explorer", "arquivos": "explorer",
    "word": "winword", "excel": "excel", "spotify": "spotify",
    "discord": "discord", "vscode": "code", "vs code": "code",
}

# ── Funções ──────────────────────────────────────────────────────

def abrir_programa(nome: str) -> str:
    comando = PROGRAMAS.get(nome.lower().strip(), nome.lower().strip())
    try:
        subprocess.Popen(comando, shell=True)
        return f"Programa '{nome}' aberto com sucesso."
    except Exception as e:
        return f"Não foi possível abrir '{nome}': {e}"

def digitar_texto(texto: str) -> str:
    try:
        pyautogui.write(texto, interval=0.03)
        return f"Texto digitado: '{texto}'"
    except Exception as e:
        return f"Erro ao digitar: {e}"

def tirar_screenshot() -> str:
    try:
        pasta = os.path.join(os.path.expanduser("~"), "Pictures", "Aria")
        os.makedirs(pasta, exist_ok=True)
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = os.path.join(pasta, f"screenshot_{agora}.png")
        pyautogui.screenshot(caminho)
        return f"Screenshot salvo em: {caminho}"
    except Exception as e:
        return f"Erro ao tirar screenshot: {e}"

def pressionar_tecla(tecla: str) -> str:
    try:
        pyautogui.press(tecla)
        return f"Tecla '{tecla}' pressionada."
    except Exception as e:
        return f"Erro: {e}"

def volume_cima() -> str:
    for _ in range(5): pyautogui.press("volumeup")
    return "Volume aumentado."

def volume_baixo() -> str:
    for _ in range(5): pyautogui.press("volumedown")
    return "Volume diminuído."

def minimizar_janela() -> str:
    pyautogui.hotkey("win", "d")
    return "Janelas minimizadas."

def fechar_janela() -> str:
    pyautogui.hotkey("alt", "f4")
    return "Janela fechada."

# ── Registro (conecta as funções ao sistema) ─────────────────────

def carregar():
    registrar_acao("abrir_programa", abrir_programa,
        "Abre um programa ou aplicativo no PC.",
        {"nome": {"tipo": "STRING", "descricao": "Nome do programa. Ex: chrome, notepad, spotify."}})

    registrar_acao("digitar_texto", digitar_texto,
        "Digita um texto no campo ativo atual do PC.",
        {"texto": {"tipo": "STRING", "descricao": "O texto a ser digitado."}})

    registrar_acao("tirar_screenshot", tirar_screenshot,
        "Tira uma captura de tela do PC e salva na pasta de imagens.", {})

    registrar_acao("pressionar_tecla", pressionar_tecla,
        "Pressiona uma tecla do teclado.",
        {"tecla": {"tipo": "STRING", "descricao": "Nome da tecla. Ex: enter, esc, tab, f5."}})

    registrar_acao("volume_cima", volume_cima,
        "Aumenta o volume do PC.", {})

    registrar_acao("volume_baixo", volume_baixo,
        "Diminui o volume do PC.", {})

    registrar_acao("minimizar_janela", minimizar_janela,
        "Minimiza todas as janelas abertas.", {})

    registrar_acao("fechar_janela", fechar_janela,
        "Fecha a janela ativa atual.", {})