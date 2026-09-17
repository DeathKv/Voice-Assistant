from acoes.registro import registrar_acao

def tocar_musica(nome: str) -> str:
    # sua lógica aqui
    return f"Tocando {nome}"

def carregar():
    registrar_acao("tocar_musica", tocar_musica,
        "Toca uma música pelo nome.",
        {"nome": {"tipo": "STRING", "descricao": "Nome da música."}})