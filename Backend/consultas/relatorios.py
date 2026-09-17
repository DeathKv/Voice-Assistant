# ================================================================
# ARQUIVO DE CONSULTAS SQL
# ================================================================
# Como adicionar uma nova consulta:
#
# 1. Crie um novo bloco abaixo seguindo o padrão
# 2. Reinicie o python main.py
# 3. Pronto! A Aria já conhece a nova consulta
#
# Parâmetros dinâmicos:
# Use {horas}, {data_inicio}, {data_fim}, {limite} nas queries
# O sistema substitui automaticamente antes de executar
# ================================================================

CONSULTAS = {

    # ── Paradas ──────────────────────────────────────────────────
    "paradas 24 horas": {
        "descricao": "Relatório de paradas das últimas 24 horas",
        "arquivo":   "paradas_24h",   # nome base do arquivo Excel
        "sql": """
            SELECT
                equipamento,
                motivo_parada,
                data_inicio,
                data_fim,
                TIMESTAMPDIFF(MINUTE, data_inicio, data_fim) AS duracao_minutos
            FROM paradas
            WHERE data_inicio >= NOW() - INTERVAL 24 HOUR
            ORDER BY data_inicio DESC
        """
    },

    "paradas semana": {
        "descricao": "Relatório de paradas da última semana",
        "arquivo":   "paradas_semana",
        "sql": """
            SELECT
                equipamento,
                motivo_parada,
                data_inicio,
                data_fim,
                TIMESTAMPDIFF(MINUTE, data_inicio, data_fim) AS duracao_minutos
            FROM paradas
            WHERE data_inicio >= NOW() - INTERVAL 7 DAY
            ORDER BY data_inicio DESC
        """
    },

    # ── Produção ──────────────────────────────────────────────────
    "producao hoje": {
        "descricao": "Relatório de produção do dia atual",
        "arquivo":   "producao_hoje",
        "sql": """
            SELECT
                linha,
                produto,
                quantidade_produzida,
                turno,
                data_producao
            FROM producao
            WHERE DATE(data_producao) = CURDATE()
            ORDER BY linha, turno
        """
    },

    # ── Adicione suas consultas abaixo ────────────────────────────
    # "nome da consulta": {
    #     "descricao": "Descrição do que a consulta retorna",
    #     "arquivo":   "nome_do_arquivo_excel",
    #     "sql": """
    #         SELECT * FROM sua_tabela WHERE sua_condicao
    #     """
    # },

}