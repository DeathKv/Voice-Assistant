import os
import datetime
import mysql.connector
import pandas as pd
from acoes.registro import registrar_acao
from consultas.relatorios import CONSULTAS

# ── Configuração ─────────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",    "localhost"),
    "port":     int(os.getenv("MYSQL_PORTA", "3306")),
    "user":     os.getenv("MYSQL_USUARIO", "root"),
    "password": os.getenv("MYSQL_SENHA",   ""),
    "database": os.getenv("MYSQL_BANCO",   ""),
}

PASTA_SAIDA = os.getenv("RELATORIOS_PASTA", "relatorios")


# ── Conexão MySQL ─────────────────────────────────────────────────

def conectar_mysql():
    """Cria e retorna uma conexão com o MySQL."""
    return mysql.connector.connect(**MYSQL_CONFIG)


def testar_conexao() -> str:
    """Testa se a conexão com o MySQL está funcionando."""
    try:
        conn = conectar_mysql()
        conn.close()
        return f"Conexão com MySQL ({MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}) bem-sucedida."
    except Exception as e:
        return f"Erro ao conectar no MySQL: {e}"


# ── Exportação Excel ──────────────────────────────────────────────

def salvar_excel(df: pd.DataFrame, nome_base: str, descricao: str) -> str:
    """
    Salva um DataFrame como Excel formatado.
    Retorna o caminho do arquivo salvo.
    """
    # Garante que a pasta existe
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    # Nome do arquivo com data e hora
    agora    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo  = os.path.join(PASTA_SAIDA, f"{nome_base}_{agora}.xlsx")

    # Salva com formatação
    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")

        # Ajusta largura das colunas automaticamente
        worksheet = writer.sheets["Dados"]
        for i, coluna in enumerate(df.columns, 1):
            largura = max(
                len(str(coluna)),
                df[coluna].astype(str).map(len).max() if len(df) > 0 else 0
            )
            # Limita entre 10 e 50 caracteres
            largura = min(max(largura + 2, 10), 50)
            worksheet.column_dimensions[
                worksheet.cell(1, i).column_letter
            ].width = largura

    return arquivo


# ── Funções principais ────────────────────────────────────────────

def gerar_relatorio(nome: str) -> str:
    """
    Executa a consulta SQL pelo nome e salva como Excel.
    """
    nome_lower = nome.lower().strip()

    # Procura a consulta pelo nome (aceita parcial)
    consulta      = None
    nome_encontrado = None
    for chave, dados in CONSULTAS.items():
        if nome_lower in chave or chave in nome_lower:
            consulta        = dados
            nome_encontrado = chave
            break

    if not consulta:
        disponiveis = ", ".join(CONSULTAS.keys())
        return f"Consulta '{nome}' não encontrada. Disponíveis: {disponiveis}"

    try:
        print(f"🗄️  Executando consulta: {nome_encontrado}")

        # Conecta e executa
        conn   = conectar_mysql()
        df     = pd.read_sql(consulta["sql"], conn)
        conn.close()

        if df.empty:
            return f"A consulta '{nome_encontrado}' não retornou nenhum dado."

        # Salva o Excel
        caminho = salvar_excel(df, consulta["arquivo"], consulta["descricao"])

        total = len(df)
        return (
            f"Relatório '{consulta['descricao']}' gerado com sucesso. "
            f"{total} registro(s) encontrado(s). "
            f"Arquivo salvo em: {caminho}"
        )

    except mysql.connector.Error as e:
        return f"Erro no MySQL: {e}"
    except Exception as e:
        return f"Erro ao gerar relatório: {e}"


def listar_relatorios() -> str:
    """Lista todas as consultas disponíveis."""
    if not CONSULTAS:
        return "Nenhuma consulta configurada em consultas/relatorios.py"

    lista = []
    for nome, dados in CONSULTAS.items():
        lista.append(f"'{nome}' — {dados['descricao']}")

    return "Relatórios disponíveis: " + " | ".join(lista)


# ── Registro ─────────────────────────────────────────────────────

def carregar():
    registrar_acao(
        "gerar_relatorio",
        gerar_relatorio,
        "Executa uma consulta no banco de dados MySQL e salva o resultado em Excel. "
        f"Relatórios disponíveis: {', '.join(CONSULTAS.keys())}.",
        {
            "nome": {
                "tipo":      "STRING",
                "descricao": (
                    "Nome do relatório desejado. "
                    f"Opções: {', '.join(CONSULTAS.keys())}."
                )
            }
        }
    )

    registrar_acao(
        "listar_relatorios",
        listar_relatorios,
        "Lista todos os relatórios disponíveis para geração.",
        {}
    )

    registrar_acao(
        "testar_conexao_mysql",
        testar_conexao,
        "Testa se a conexão com o banco de dados MySQL está funcionando.",
        {}
    )