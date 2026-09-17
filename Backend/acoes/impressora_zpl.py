import socket
import os
from acoes.registro import registrar_acao

# ── Configuração ─────────────────────────────────────────────────
IP    = os.getenv("IMPRESSORA_IP", "")
PORTA = int(os.getenv("IMPRESSORA_PORTA", "9100"))

def carregar_arquivos_zpl():
    """
    Descobre todos os arquivos ZPL configurados no .env.
    Qualquer variável que comece com ZPL_ é carregada.
    Ex: ZPL_TESTE=zpl/etiqueta.zpl → {"teste": "zpl/etiqueta.zpl"}
    """
    arquivos = {}
    for chave, valor in os.environ.items():
        if chave.startswith("ZPL_"):
            nome = chave.replace("ZPL_", "").lower().replace("_", " ")
            arquivos[nome] = valor
    return arquivos

ARQUIVOS_ZPL = carregar_arquivos_zpl()


# ── Funções ──────────────────────────────────────────────────────

def enviar_zpl_para_impressora(conteudo_zpl: str) -> bool:
    """
    Envia conteúdo ZPL diretamente para a impressora via socket TCP.
    Retorna True se sucesso, False se erro.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((IP, PORTA))
        s.sendall(conteudo_zpl.encode("utf-8"))
    return True


def imprimir_zpl(nome: str) -> str:
    """Imprime um arquivo ZPL pelo nome configurado no .env"""

    if not IP:
        return "Erro: IP da impressora não configurado no .env (IMPRESSORA_IP)."

    nome_lower = nome.lower().strip()

    # Procura o arquivo pelo nome (aceita parcial)
    caminho = None
    nome_encontrado = None
    for nome_config, caminho_config in ARQUIVOS_ZPL.items():
        if nome_lower in nome_config or nome_config in nome_lower:
            caminho = caminho_config
            nome_encontrado = nome_config
            break

    if not caminho:
        disponiveis = ", ".join(ARQUIVOS_ZPL.keys()) if ARQUIVOS_ZPL else "nenhum"
        return f"Arquivo ZPL '{nome}' não encontrado. Disponíveis: {disponiveis}"

    if not os.path.exists(caminho):
        return f"Erro: arquivo '{caminho}' não encontrado na pasta do projeto."

    try:
        # Lê o arquivo ZPL
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Envia para a impressora
        enviar_zpl_para_impressora(conteudo)
        return f"Arquivo ZPL '{nome_encontrado}' enviado para a impressora ({IP}) com sucesso."

    except socket.timeout:
        return f"Erro: impressora ({IP}) não respondeu. Verifique se está ligada e conectada."
    except ConnectionRefusedError:
        return f"Erro: impressora ({IP}) recusou a conexão. Verifique o IP e a porta."
    except UnicodeDecodeError:
        # Tenta ler como binário se falhar UTF-8
        try:
            with open(caminho, "rb") as f:
                conteudo_bytes = f.read()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((IP, PORTA))
                s.sendall(conteudo_bytes)
            return f"Arquivo ZPL '{nome_encontrado}' enviado com sucesso."
        except Exception as e:
            return f"Erro ao enviar arquivo: {e}"
    except Exception as e:
        return f"Erro inesperado: {e}"


def listar_zpl() -> str:
    """Lista todos os arquivos ZPL disponíveis."""
    if not ARQUIVOS_ZPL:
        return "Nenhum arquivo ZPL configurado no .env"

    lista = []
    for nome, caminho in ARQUIVOS_ZPL.items():
        existe = "✅" if os.path.exists(caminho) else "❌ arquivo não encontrado"
        lista.append(f"{nome} ({existe})")

    return "Arquivos ZPL disponíveis: " + ", ".join(lista)


# ── Registro ─────────────────────────────────────────────────────

def carregar():
    registrar_acao(
        "imprimir_zpl",
        imprimir_zpl,
        "Envia um arquivo ZPL para a impressora Zebra imprimir. "
        "O usuário informa o nome do arquivo configurado.",
        {
            "nome": {
                "tipo": "STRING",
                "descricao": (
                    "Nome do arquivo ZPL a imprimir. "
                    f"Disponíveis: {', '.join(ARQUIVOS_ZPL.keys()) if ARQUIVOS_ZPL else 'nenhum configurado'}."
                )
            }
        }
    )

    registrar_acao(
        "listar_zpl",
        listar_zpl,
        "Lista todos os arquivos ZPL disponíveis para impressão.",
        {}
    )