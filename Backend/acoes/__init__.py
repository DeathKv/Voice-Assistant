import importlib
import os
import pkgutil

def carregar_todos():
    """Descobre e carrega todos os módulos de ações automaticamente."""
    print("📦 Carregando módulos de ações...")

    pasta = os.path.dirname(__file__)

    for _, nome_modulo, _ in pkgutil.iter_modules([pasta]):
        # Ignora o registro (não é um módulo de ação)
        if nome_modulo == "registro":
            continue

        try:
            modulo = importlib.import_module(f"acoes.{nome_modulo}")
            if hasattr(modulo, "carregar"):
                modulo.carregar()
                print(f"   📂 Módulo '{nome_modulo}' carregado!")
        except Exception as e:
            print(f"   ⚠️ Erro ao carregar módulo '{nome_modulo}': {e}")

    print("✅ Todos os módulos carregados!\n")