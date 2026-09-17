from google.genai import types

# Armazena TODAS as funções e declarações de todos os módulos
_FUNCOES = {}        # {"nome_funcao": funcao_real}
_DECLARACOES = []    # [FunctionDeclaration, ...]

def registrar_acao(nome: str, funcao, descricao: str, parametros: dict = None):
    """
    Registra uma ação no sistema.

    Exemplo de uso:
        registrar_acao(
            nome="abrir_programa",
            funcao=minha_funcao,
            descricao="Abre um programa no PC.",
            parametros={
                "nome": {"tipo": "STRING", "descricao": "Nome do programa"}
            }
        )
    """
    # Salva a função real
    _FUNCOES[nome] = funcao

    # Monta os parâmetros para o Gemini
    props = {}
    required = []

    if parametros:
        for param_nome, param_info in parametros.items():
            tipo_map = {
                "STRING": types.Type.STRING,
                "NUMBER": types.Type.NUMBER,
                "BOOLEAN": types.Type.BOOLEAN,
            }
            props[param_nome] = types.Schema(
                type=tipo_map.get(param_info.get("tipo", "STRING"), types.Type.STRING),
                description=param_info.get("descricao", "")
            )
            if param_info.get("obrigatorio", True):
                required.append(param_nome)

    # Cria a declaração para o Gemini
    schema = types.Schema(type=types.Type.OBJECT, properties=props)
    if required:
        schema = types.Schema(type=types.Type.OBJECT, properties=props, required=required)

    _DECLARACOES.append(
        types.FunctionDeclaration(
            name=nome,
            description=descricao,
            parameters=schema
        )
    )

    print(f"   ✅ Ação registrada: {nome}")


def obter_ferramentas():
    """Retorna a lista de ferramentas para o Gemini."""
    if _DECLARACOES:
        return [types.Tool(function_declarations=_DECLARACOES)]
    return []


def executar(nome: str, args: dict) -> str:
    """Executa uma ação registrada pelo nome."""
    if nome in _FUNCOES:
        try:
            print(f"🔧 Executando: {nome}({args})")
            return _FUNCOES[nome](**args)
        except Exception as e:
            return f"Erro ao executar '{nome}': {str(e)}"
    return f"Ação '{nome}' não encontrada."