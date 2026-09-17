import asyncio
import json
import websockets
from config_manager import obter_config_frontend, salvar_multiplas

CLIENTES: set = set()

async def handler(websocket):
    CLIENTES.add(websocket)
    print(f"🔌 Frontend conectado. Total: {len(CLIENTES)}")
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            tipo = msg.get("tipo", "")

            if tipo == "get_config":
                print("📋 Frontend pediu configurações...")
                config = obter_config_frontend()
                print(f"   → Enviando {len(config)} seções.")
                await websocket.send(json.dumps({
                    "tipo":   "config_dados",
                    "config": config
                }))

            elif tipo == "save_config":
                campos = msg.get("campos", {})
                print(f"💾 Salvando {len(campos)} campo(s) no .env...")
                try:
                    salvar_multiplas(campos)
                    print("   ✅ Salvo com sucesso.")
                    await websocket.send(json.dumps({
                        "tipo":   "config_salva",
                        "sucesso": True
                    }))
                except Exception as ex:
                    print(f"   ❌ Erro ao salvar: {ex}")
                    await websocket.send(json.dumps({
                        "tipo":    "config_salva",
                        "sucesso": False,
                        "erro":    str(ex)
                    }))

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        CLIENTES.discard(websocket)
        print(f"🔌 Frontend desconectado. Total: {len(CLIENTES)}")


async def broadcast(dados: dict):
    """Envia um pacote para todos os frontends conectados."""
    if not CLIENTES:
        return
    msg = json.dumps(dados)
    mortos = set()
    for ws in CLIENTES:
        try:
            await ws.send(msg)
        except Exception:
            mortos.add(ws)
    CLIENTES.difference_update(mortos)


async def notify_frontend(estado: str, usuario: str = "", aria: str = ""):
    """Atalho usado pelo gemini_client para atualizar o estado no Frontend."""
    await broadcast({
        "tipo":    "estado",
        "state":   estado,
        "usuario": usuario,
        "aria":    aria,
    })


async def start_server():
    print("🌐 WebSocket escutando em ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()