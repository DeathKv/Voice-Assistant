import pyautogui
import subprocess
import os
import datetime

pyautogui.FAILSAFE = True

# Programas conhecidos (nome falado → comando real)
PROGRAMAS = {
    "chrome":      "chrome",
    "google":      "chrome",
    "navegador":   "chrome",
    "notepad":     "notepad",
    "bloco de notas": "notepad",
    "calculadora": "calc",
    "explorer":    "explorer",
    "arquivos":    "explorer",
    "word":        "winword",
    "excel":       "excel",
    "spotify":     "spotify",
    "discord":     "discord",
    "vscode":      "code",
    "vs code":     "code",
}

def abrir_programa(nome: str) -> str:
    nome_lower = nome.lower().strip()
    comando = PROGRAMAS.get(nome_lower, nome_lower)
    try:
        subprocess.Popen(comando, shell=True)
        return f"Programa '{nome}' aberto com sucesso."
    except Exception as e:
        return f"Não foi possível abrir '{nome}': {str(e)}"

def digitar_texto(texto: str) -> str:
    try:
        pyautogui.write(texto, interval=0.03)
        return f"Texto digitado: '{texto}'"
    except Exception as e:
        return f"Erro ao digitar: {str(e)}"

def tirar_screenshot() -> str:
    try:
        pasta    = os.path.join(os.path.expanduser("~"), "Pictures", "Aria")
        os.makedirs(pasta, exist_ok=True)
        agora    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho  = os.path.join(pasta, f"screenshot_{agora}.png")
        pyautogui.screenshot(caminho)
        return f"Screenshot salvo em: {caminho}"
    except Exception as e:
        return f"Erro ao tirar screenshot: {str(e)}"

def pressionar_tecla(tecla: str) -> str:
    try:
        pyautogui.press(tecla)
        return f"Tecla '{tecla}' pressionada."
    except Exception as e:
        return f"Erro ao pressionar tecla '{tecla}': {str(e)}"

def volume_cima() -> str:
    try:
        for _ in range(5):
            pyautogui.press("volumeup")
        return "Volume aumentado."
    except Exception as e:
        return f"Erro ao aumentar volume: {str(e)}"

def volume_baixo() -> str:
    try:
        for _ in range(5):
            pyautogui.press("volumedown")
        return "Volume diminuído."
    except Exception as e:
        return f"Erro ao diminuir volume: {str(e)}"

def minimizar_janela() -> str:
    try:
        pyautogui.hotkey("win", "d")
        return "Janelas minimizadas."
    except Exception as e:
        return f"Erro ao minimizar: {str(e)}"

def fechar_janela() -> str:
    try:
        pyautogui.hotkey("alt", "f4")
        return "Janela fechada."
    except Exception as e:
        return f"Erro ao fechar janela: {str(e)}"