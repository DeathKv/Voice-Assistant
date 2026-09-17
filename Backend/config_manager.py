import os
from dotenv import dotenv_values, set_key

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

VOZES = [
    "Zephyr","Puck","Charon","Kore","Fenrir","Leda","Orus","Aoede",
    "Callirrhoe","Autonoe","Enceladus","Iapetus","Umbriel","Algieba",
    "Despina","Erinome","Algenib","Rasalghul","Laomedeia","Achernar",
    "Alnilam","Schedar","Gacrux","Pulcherrima","Achird","Zubenelgenubi",
    "Vindemiatrix","Sadachbia","Sadaltager","Sulafat",
]

def ler_env() -> dict:
    return dotenv_values(ENV_PATH)

def salvar_variavel(chave: str, valor: str):
    set_key(ENV_PATH, chave, valor, quote_mode="never")

def salvar_multiplas(pares: dict):
    for chave, valor in pares.items():
        salvar_variavel(chave, valor)

def obter_config_frontend() -> dict:
    env = ler_env()

    def v(chave, padrao=""):
        return env.get(chave, padrao)

    return {
        "assistente": {
            "label": "Assistente",
            "campos": {
                "NOME_ASSISTENTE":  {"label": "Nome da Assistente",      "valor": v("NOME_ASSISTENTE","Aria"),        "tipo": "text"},
                "COMANDO_ATIVACAO": {"label": "Frase de Ativação",       "valor": v("COMANDO_ATIVACAO","System Call"), "tipo": "text"},
                "SOM_ATIVACAO":     {"label": "Arquivo de Som (.wav)",   "valor": v("SOM_ATIVACAO","ativacao.wav"),   "tipo": "text"},
            }
        },
        "voz": {
            "label": "Voz",
            "campos": {
                "VOZ_NOME":   {"label": "Voz Gemini",   "valor": v("VOZ_NOME","Charon"), "tipo": "select", "opcoes": VOZES},
                "VOZ_IDIOMA": {"label": "Idioma (BCP-47)", "valor": v("VOZ_IDIOMA","en-US"), "tipo": "text"},
            }
        },
        "vad": {
            "label": "Detecção de Silêncio",
            "campos": {
                "VAD_SILENCE_MS": {"label": "Silêncio para encerrar fala (ms)", "valor": v("VAD_SILENCE_MS","600"), "tipo": "range", "min": 200, "max": 2000},
                "VAD_PREFIX_MS":  {"label": "Prefixo de áudio capturado (ms)",  "valor": v("VAD_PREFIX_MS","20"),  "tipo": "range", "min": 0,   "max": 500},
            }
        },
        "impressora": {
            "label": "Impressora ZPL",
            "campos": {
                "IMPRESSORA_IP":   {"label": "IP da Impressora",    "valor": v("IMPRESSORA_IP","192.168.1.100"), "tipo": "text"},
                "IMPRESSORA_PORTA":{"label": "Porta TCP",           "valor": v("IMPRESSORA_PORTA","9100"),      "tipo": "text"},
                "ZPL_TESTE":       {"label": "Arquivo ZPL de teste","valor": v("ZPL_TESTE","zpl/etiqueta_teste.zpl"), "tipo": "text"},
            }
        },
        "mysql": {
            "label": "MySQL",
            "campos": {
                "MYSQL_HOST":    {"label": "Host / IP",       "valor": v("MYSQL_HOST",""),    "tipo": "text"},
                "MYSQL_PORTA":   {"label": "Porta",           "valor": v("MYSQL_PORTA","3306"),"tipo": "text"},
                "MYSQL_USUARIO": {"label": "Usuário",         "valor": v("MYSQL_USUARIO",""), "tipo": "text"},
                "MYSQL_SENHA":   {"label": "Senha",           "valor": v("MYSQL_SENHA",""),   "tipo": "password"},
                "MYSQL_BANCO":   {"label": "Banco de Dados",  "valor": v("MYSQL_BANCO",""),   "tipo": "text"},
                "RELATORIOS_PASTA": {"label": "Pasta de Relatórios", "valor": v("RELATORIOS_PASTA","C:\\Relatorios\\Aria"), "tipo": "text"},
            }
        },
        "ewelink": {
            "label": "eWeLink",
            "campos": {
                "EWELINK_EMAIL":      {"label": "E-mail",        "valor": v("EWELINK_EMAIL",""),      "tipo": "text"},
                "EWELINK_SENHA":      {"label": "Senha",         "valor": v("EWELINK_SENHA",""),      "tipo": "password"},
                "EWELINK_APP_ID":     {"label": "App ID",        "valor": v("EWELINK_APP_ID",""),     "tipo": "text"},
                "EWELINK_APP_SECRET": {"label": "App Secret",    "valor": v("EWELINK_APP_SECRET",""), "tipo": "password"},
                "EWELINK_REGIAO":     {"label": "Região (eu/us/as)", "valor": v("EWELINK_REGIAO","eu"), "tipo": "select", "opcoes": ["eu","us","as"]},
            }
        },
    }