import json
import os
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), "memoria")
FATOS_PATH    = os.path.join(BASE, "fatos.json")
SESSOES_PATH  = os.path.join(BASE, "sessoes.json")
HISTORICO_PATH= os.path.join(BASE, "historico.json")

MAX_SESSOES   = 30   # máximo de sessões guardadas
MAX_HISTORICO = 50   # máximo de trocas no histórico bruto


# ── Helpers de leitura/escrita ───────────────────────────────────

def _ler(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _salvar(path: str, dados):
    os.makedirs(BASE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ── CAMADA 1: Fatos permanentes ──────────────────────────────────

def ler_fatos() -> dict:
    return _ler(FATOS_PATH, {})

def salvar_fatos(fatos: dict):
    """Mescla os novos fatos com os existentes."""
    atuais = ler_fatos()
    atuais.update(fatos)
    _salvar(FATOS_PATH, atuais)
    print(f"💾 Memória: {len(fatos)} fato(s) novo(s) salvo(s).")


# ── CAMADA 2: Resumo das sessões ─────────────────────────────────

def ler_sessoes() -> list:
    return _ler(SESSOES_PATH, [])

def salvar_sessao(resumo: str):
    sessoes = ler_sessoes()
    sessoes.append({
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumo": resumo
    })
    # Mantém só as últimas MAX_SESSOES sessões
    if len(sessoes) > MAX_SESSOES:
        sessoes = sessoes[-MAX_SESSOES:]
    _salvar(SESSOES_PATH, sessoes)
    print(f"💾 Memória: resumo da sessão salvo.")


# ── CAMADA 3: Histórico bruto ────────────────────────────────────

def ler_historico() -> list:
    return _ler(HISTORICO_PATH, [])

def salvar_historico(historico: list):
    recente = historico[-MAX_HISTORICO:]
    _salvar(HISTORICO_PATH, recente)


# ── Montar contexto para o system_instruction ────────────────────

def montar_contexto_memoria() -> str:
    partes = []

    # Fatos permanentes
    fatos = ler_fatos()
    if fatos:
        partes.append("=== O QUE VOCÊ SABE SOBRE O USUÁRIO ===")
        for chave, valor in fatos.items():
            partes.append(f"• {chave}: {valor}")

    # Últimas 5 sessões
    sessoes = ler_sessoes()
    if sessoes:
        partes.append("\n=== SESSÕES ANTERIORES ===")
        for s in sessoes[-5:]:
            partes.append(f"• [{s['data']}] {s['resumo']}")

    # Últimas 10 trocas do histórico bruto
    historico = ler_historico()
    if historico:
        partes.append("\n=== CONVERSA RECENTE (sessão anterior) ===")
        for h in historico[-10:]:
            if h.get("user"):
                partes.append(f"Usuário: {h['user']}")
            if h.get("aria"):
                partes.append(f"Assistente: {h['aria']}")

    if not partes:
        return ""

    return "\n".join(partes)