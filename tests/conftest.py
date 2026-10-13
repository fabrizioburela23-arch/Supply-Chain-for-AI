"""tests/conftest.py — estado global que NO debe filtrarse entre tests.

R1 (misión de reparación 2026-10-04): el corta-circuito de proveedores de IA
(core.ai._CIRCUIT) es memoria de proceso; un test que simula "modelo retirado"
dejaría al proveedor en pausa para los tests siguientes.
"""
import os
import sys

import pytest

os.environ.setdefault('KHIPU_SCHEDULER', 'off')
os.environ.setdefault('WORLD_GDELT_EVENTS', 'off')
os.environ.setdefault('WORLD_GDELT_BACKFILL', 'off')   # el relleno en segundo plano tiene su test   # tests del World Monitor usan la API GEO simulada; los eventos crudos tienen sus tests   # R5: el hilo periódico no arranca al importar server en tests


@pytest.fixture(autouse=True)
def _ai_circuits_cerrados():
    ai = sys.modules.get('core.ai')
    if ai is not None and hasattr(ai, '_CIRCUIT'):
        ai._CIRCUIT.clear()
    yield
    ai = sys.modules.get('core.ai')
    if ai is not None and hasattr(ai, '_CIRCUIT'):
        ai._CIRCUIT.clear()


@pytest.fixture(autouse=True)
def _libro_async_vacio():
    """Paso 20/21 (INFRA_OPERATIVA): las decisiones async (chat, MCP, qué-pasaría-si) y las filas de ai_calls se
    escriben en hilos propios. Se vacían al terminar cada test: nada pendiente puede caer sobre las tablas que el
    módulo siguiente borra y recrea."""
    yield
    d = sys.modules.get('core.decisions')
    if d is not None and hasattr(d, 'flush_async'):
        try:
            d.flush_async(timeout=5.0)
        except Exception:  # noqa: BLE001
            pass
    a = sys.modules.get('core.ai_calls')
    if a is not None and hasattr(a, 'flush'):
        try:
            a.flush()
        except Exception:  # noqa: BLE001
            pass
