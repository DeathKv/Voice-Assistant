import os
import time
import json
import hmac
import hashlib
import base64
import uuid
import requests
from acoes.registro import registrar_acao

# ── Configuração ─────────────────────────────────────────────────
EMAIL     = os.getenv("EWELINK_EMAIL", "")
SENHA     = os.getenv("EWELINK_SENHA", "")
APP_ID    = os.getenv("EWELINK_APP_ID", "")
APP_SECRET= os.getenv("EWELINK_APP_SECRET", "")
REGIAO    = os.getenv("EWELINK_REGIAO", "eu")

BASE_URL  = f"https://{REGIAO}-apia.coolkit.cc"

# Cache do token (evita login a cada comando)
_cache = {
    "token":      None,
    "user_id":    None,
    "expira_em":  0
}

def carregar_dispositivos():
    """Descobre todos os dispositivos configurados no .env"""
    dispositivos = {}
    for chave, valor in os.environ.items():
        if chave.startswith("EWELINK_") and chave not in (
            "EWELINK_EMAIL", "EWELINK_SENHA",
            "EWELINK_APP_ID", "EWELINK_APP_SECRET", "EWELINK_REGIAO"
        ):
            nome = chave.replace("EWELINK_", "").lower().replace("_", " ")
            dispositivos[nome] = valor
    return dispositivos

DISPOSITIVOS = carregar_dispositivos()


# ── Autenticação ─────────────────────────────────────────────────

def gerar_assinatura(dados: str) -> str:
    """Gera assinatura HMAC-SHA256 para autenticação eWeLink."""
    chave = APP_SECRET.encode("utf-8")
    msg   = dados.encode("utf-8")
    return base64.b64encode(
        hmac.new(chave, msg, hashlib.sha256).digest()
    ).decode("utf-8")


def fazer_login() -> bool:
    """
    Faz login na API eWeLink e salva o token no cache.
    Retorna True se sucesso.
    """
    if not all([EMAIL, SENHA, APP_ID, APP_SECRET]):
        print("⚠️ eWeLink: credenciais não configuradas no .env")
        return False

    # Verifica se o token ainda é válido (expira em 30 dias, renovamos a cada 24h)
    if _cache["token"] and time.time() < _cache["expira_em"]:
        return True

    try:
        payload = {
            "email":    EMAIL,
            "password": SENHA,
        }

        # Gera a assinatura
        payload_str  = json.dumps(payload, separators=(",", ":"))
        assinatura   = gerar_assinatura(payload_str)

        headers = {
            "Content-Type":  "application/json",
            "X-CK-Appid":    APP_ID,
            "Authorization": f"Sign {assinatura}",
        }

        resposta = requests.post(
            f"{BASE_URL}/v2/user/login",
            headers=headers,
            json=payload,
            timeout=10
        )

        dados = resposta.json()

        if dados.get("error") == 0:
            _cache["token"]     = dados["data"]["at"]       # access token
            _cache["user_id"]   = dados["data"]["user"]["apikey"]
            _cache["expira_em"] = time.time() + 86400       # 24 horas
            print("✅ eWeLink: login realizado com sucesso!")
            return True
        else:
            print(f"❌ eWeLink: erro no login — {dados.get('msg', 'desconhecido')}")
            return False

    except Exception as e:
        print(f"❌ eWeLink: erro ao conectar — {e}")
        return False


def obter_headers_auth() -> dict:
    """Retorna headers com autenticação Bearer."""
    return {
        "Content-Type":  "application/json",
        "X-CK-Appid":    APP_ID,
        "Authorization": f"Bearer {_cache['token']}",
    }


# ── Controle de dispositivos ─────────────────────────────────────

def controlar_dispositivo(device_id: str, ligar: bool) -> bool:
    """Envia comando liga/desliga para um dispositivo."""
    try:
        payload = {
            "type":   1,
            "id":     device_id,
            "params": {"switch": "on" if ligar else "off"}
        }

        resposta = requests.post(
            f"{BASE_URL}/v2/device/thing/status",
            headers=obter_headers_auth(),
            json=payload,
            timeout=10
        )

        dados = resposta.json()
        return dados.get("error") == 0

    except Exception as e:
        print(f"❌ eWeLink: erro ao controlar dispositivo — {e}")
        return False


def obter_status_dispositivo(device_id: str) -> str:
    """Obtém o status atual (ligado/desligado) de um dispositivo."""
    try:
        params = {
            "type": 1,
            "id":   device_id,
        }

        resposta = requests.get(
            f"{BASE_URL}/v2/device/thing/status",
            headers=obter_headers_auth(),
            params=params,
            timeout=10
        )

        dados = resposta.json()
        if dados.get("error") == 0:
            switch = dados["data"]["params"].get("switch", "unknown")
            return "ligado" if switch == "on" else "desligado"
        return "desconhecido"

    except Exception:
        return "desconhecido"


# ── Funções principais ────────────────────────────────────────────

def controlar_luz_ewelink(dispositivo: str, acao: str) -> str:
    """Liga ou desliga um dispositivo eWeLink pelo nome."""

    if not fazer_login():
        return "Erro: não foi possível conectar ao eWeLink. Verifique as credenciais no .env"

    dispositivo_lower = dispositivo.lower().strip()

    # Procura o dispositivo pelo nome (aceita parcial)
    device_id     = None
    nome_encontrado = None
    for nome, did in DISPOSITIVOS.items():
        if dispositivo_lower in nome or nome in dispositivo_lower:
            device_id       = did
            nome_encontrado = nome
            break

    if not device_id:
        disponiveis = ", ".join(DISPOSITIVOS.keys()) if DISPOSITIVOS else "nenhum"
        return f"Dispositivo '{dispositivo}' não encontrado. Disponíveis: {disponiveis}"

    ligar = acao.lower().strip() in ["ligar", "acender", "on", "liga", "acende", "ativar"]

    sucesso = controlar_dispositivo(device_id, ligar)

    if sucesso:
        estado = "ligado" if ligar else "desligado"
        return f"Luz do(a) {nome_encontrado} {estado} com sucesso."
    else:
        return f"Erro ao controlar '{nome_encontrado}'. Verifique a conexão."


def controlar_todas_ewelink(acao: str) -> str:
    """Liga ou desliga todos os dispositivos eWeLink."""

    if not fazer_login():
        return "Erro: não foi possível conectar ao eWeLink."

    if not DISPOSITIVOS:
        return "Nenhum dispositivo eWeLink configurado no .env"

    ligar      = acao.lower().strip() in ["ligar", "acender", "on", "liga", "acende", "ativar"]
    resultados = []

    for nome, device_id in DISPOSITIVOS.items():
        sucesso = controlar_dispositivo(device_id, ligar)
        estado  = "ligado" if ligar else "desligado"
        if sucesso:
            resultados.append(f"{nome} {estado}")
        else:
            resultados.append(f"{nome} com erro")

    return "Resultado: " + ", ".join(resultados)


def status_dispositivos_ewelink() -> str:
    """Verifica o status de todos os dispositivos."""

    if not fazer_login():
        return "Erro: não foi possível conectar ao eWeLink."

    if not DISPOSITIVOS:
        return "Nenhum dispositivo eWeLink configurado."

    resultados = []
    for nome, device_id in DISPOSITIVOS.items():
        status = obter_status_dispositivo(device_id)
        resultados.append(f"{nome}: {status}")

    return "Status das luzes — " + ", ".join(resultados)


def listar_dispositivos_ewelink() -> str:
    """Lista todos os dispositivos configurados."""
    if not DISPOSITIVOS:
        return "Nenhum dispositivo eWeLink configurado no .env"
    lista = ", ".join(DISPOSITIVOS.keys())
    return f"Dispositivos disponíveis: {lista}"


# ── Registro ─────────────────────────────────────────────────────

def carregar():
    registrar_acao(
        "controlar_luz_ewelink",
        controlar_luz_ewelink,
        "Liga ou desliga uma luz ou dispositivo inteligente eWeLink pelo nome do cômodo.",
        {
            "dispositivo": {
                "tipo":     "STRING",
                "descricao": f"Nome do dispositivo. Disponíveis: {', '.join(DISPOSITIVOS.keys()) if DISPOSITIVOS else 'nenhum'}."
            },
            "acao": {
                "tipo":     "STRING",
                "descricao": "Ação desejada: ligar ou desligar."
            }
        }
    )

    registrar_acao(
        "controlar_todas_ewelink",
        controlar_todas_ewelink,
        "Liga ou desliga TODOS os dispositivos eWeLink da casa de uma vez.",
        {
            "acao": {
                "tipo":     "STRING",
                "descricao": "Ação: ligar ou desligar."
            }
        }
    )

    registrar_acao(
        "status_dispositivos_ewelink",
        status_dispositivos_ewelink,
        "Verifica o status atual (ligado ou desligado) de todos os dispositivos da casa.",
        {}
    )

    registrar_acao(
        "listar_dispositivos_ewelink",
        listar_dispositivos_ewelink,
        "Lista todos os dispositivos inteligentes disponíveis.",
        {}
    )