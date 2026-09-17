import requests
import datetime
import os

def obter_localizacao() -> dict:
    """
    Obtém localização aproximada via IP (sem precisar de GPS).
    Retorna cidade, estado, país, latitude e longitude.
    """
    try:
        resposta = requests.get("http://ip-api.com/json/?lang=pt-BR", timeout=5)
        dados    = resposta.json()
        if dados.get("status") == "success":
            return {
                "cidade":    dados.get("city", ""),
                "estado":    dados.get("regionName", ""),
                "pais":      dados.get("country", ""),
                "latitude":  dados.get("lat", 0),
                "longitude": dados.get("lon", 0),
                "timezone":  dados.get("timezone", ""),
                "isp":       dados.get("isp", ""),
            }
    except Exception:
        pass
    return {}


def obter_clima(lat: float, lon: float) -> dict:
    """
    Obtém o clima atual via Open-Meteo (gratuito, sem API key).
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"wind_speed_10m,weather_code"
            f"&timezone=auto"
        )
        dados = requests.get(url, timeout=5).json()
        atual = dados.get("current", {})

        # Tradução do código de clima
        codigo = atual.get("weather_code", 0)
        condicao = traduzir_clima(codigo)

        return {
            "temperatura": atual.get("temperature_2m", ""),
            "umidade":     atual.get("relative_humidity_2m", ""),
            "vento":       atual.get("wind_speed_10m", ""),
            "condicao":    condicao,
        }
    except Exception:
        return {}


def traduzir_clima(codigo: int) -> str:
    tabela = {
        0:  "Céu limpo",
        1:  "Principalmente limpo", 2: "Parcialmente nublado", 3: "Encoberto",
        45: "Neblina", 48: "Neblina com geada",
        51: "Garoa leve", 53: "Garoa moderada", 55: "Garoa intensa",
        61: "Chuva leve", 63: "Chuva moderada", 65: "Chuva forte",
        71: "Neve leve", 73: "Neve moderada", 75: "Neve forte",
        80: "Pancadas de chuva", 81: "Pancadas moderadas", 82: "Pancadas fortes",
        95: "Tempestade", 96: "Tempestade com granizo",
    }
    return tabela.get(codigo, "Condição desconhecida")


def obter_contexto_completo() -> str:
    """
    Monta uma string com data, hora, localização e clima
    para ser injetada no system_instruction da Aria.
    """
    agora     = datetime.datetime.now()
    dias_pt   = ["Segunda-feira","Terça-feira","Quarta-feira",
                  "Quinta-feira","Sexta-feira","Sábado","Domingo"]
    meses_pt  = ["janeiro","fevereiro","março","abril","maio","junho",
                  "julho","agosto","setembro","outubro","novembro","dezembro"]

    dia_semana = dias_pt[agora.weekday()]
    data_str   = f"{agora.day} de {meses_pt[agora.month-1]} de {agora.year}"
    hora_str   = agora.strftime("%H:%M")

    linhas = [
        "=== CONTEXTO ATUAL DO USUÁRIO ===",
        f"Data: {dia_semana}, {data_str}",
        f"Hora: {hora_str}",
    ]

    # Localização
    loc = obter_localizacao()
    if loc:
        linhas.append(
            f"Localização: {loc['cidade']}, {loc['estado']}, {loc['pais']}"
        )
        linhas.append(
            f"Coordenadas: {loc['latitude']}, {loc['longitude']}"
        )

        # Clima
        clima = obter_clima(loc["latitude"], loc["longitude"])
        if clima:
            linhas.append(
                f"Clima atual: {clima['condicao']}, "
                f"{clima['temperatura']}°C, "
                f"Umidade {clima['umidade']}%, "
                f"Vento {clima['vento']} km/h"
            )

    linhas.append("=================================")
    return "\n".join(linhas)