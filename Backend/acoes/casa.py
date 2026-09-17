import requests
import os
import json
from acoes.registro import registrar_acao

# ── Configuração dos cômodos ─────────────────────────────────────
# Carrega do .env no formato: COMODO_NOME=IP
# Ex: COMODO_SALA=192.168.1.50

def carregar_comodos():
    """Descobre todos os cômodos configurados no .env"""
    comodos = {}
    for chave, valor in os.environ.items():
        if chave.startswith("COMODO_"):
            nome = chave.replace("COMODO_", "").lower().replace("_", " ")
            comodos[nome] = valor
    return comodos

COMODOS = carregar_comodos()


def listar_comodos() -> str:
    """Lista todos os cômodos configurados."""
    if not COMODOS:
        return "Nenhum cômodo configurado no .env"
    lista = ", ".join([f"{nome} ({ip})" for nome, ip in COMODOS.items()])
    return f"Cômodos disponíveis: {lista}"


def controlar_luz(comodo: str, acao: str) -> str:
    """
    Liga ou desliga a luz de um cômodo.
    Envia requisição HTTP para a tomada inteligente.
    """
    comodo_lower = comodo.lower().strip()

    # Procura o cômodo pelo nome (aceita parcial)
    ip = None
    nome_encontrado = None
    for nome, endereco in COMODOS.items():
        if comodo_lower in nome or nome in comodo_lower:
            ip = endereco
            nome_encontrado = nome
            break

    if not ip:
        disponiveis = ", ".join(COMODOS.keys()) if COMODOS else "nenhum"
        return f"Cômodo '{comodo}' não encontrado. Disponíveis: {disponiveis}"

    acao_lower = acao.lower().strip()
    ligar = acao_lower in ["ligar", "acender", "on", "liga", "acende", "ativar"]

    try:
        # ────────────────────────────────────────────────────────
        # ADAPTE AQUI para sua tomada inteligente!
        #
        # Exemplo para Tasmota (Sonoff com firmware Tasmota):
        url = f"http://{ip}/cm?cmnd=Power%20{'On' if ligar else 'Off'}"

        # Exemplo para Shelly:
        # url = f"http://{ip}/relay/0?turn={'on' if ligar else 'off'}"

        # Exemplo para Tuya (via tinytuya - precisa de outro código):
        # Veja o PASSO 8 para Tuya
        # ────────────────────────────────────────────────────────

        resposta = requests.get(url, timeout=5)

        if resposta.status_code == 200:
            estado = "ligada" if ligar else "desligada"
            return f"Luz do(a) {nome_encontrado} {estado} com sucesso."
        else:
            return f"Erro: tomada respondeu com código {resposta.status_code}"

    except requests.Timeout:
        return f"Erro: tomada do(a) {nome_encontrado} ({ip}) não respondeu."
    except requests.ConnectionError:
        return f"Erro: não foi possível conectar na tomada do(a) {nome_encontrado} ({ip})."
    except Exception as e:
        return f"Erro ao controlar luz: {e}"


def controlar_todas(acao: str) -> str:
    """Liga ou desliga TODAS as luzes da casa."""
    if not COMODOS:
        return "Nenhum cômodo configurado."

    resultados = []
    for nome in COMODOS:
        resultado = controlar_luz(nome, acao)
        resultados.append(resultado)

    return " | ".join(resultados)


# ── Registro ─────────────────────────────────────────────────────

def carregar():
    registrar_acao("listar_comodos", listar_comodos,
        "Lista todos os cômodos da casa que têm luzes inteligentes.", {})

    registrar_acao("controlar_luz", controlar_luz,
        "Liga ou desliga a luz de um cômodo específico da casa.",
        {
            "comodo": {"tipo": "STRING", "descricao": "Nome do cômodo. Ex: sala, quarto, cozinha, banheiro."},
            "acao":   {"tipo": "STRING", "descricao": "Ação: ligar ou desligar."}
        })

    registrar_acao("controlar_todas", controlar_todas,
        "Liga ou desliga TODAS as luzes da casa de uma vez.",
        {"acao": {"tipo": "STRING", "descricao": "Ação: ligar ou desligar."}})