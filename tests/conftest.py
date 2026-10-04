"""tests/conftest.py — estado global que NO debe filtrarse entre tests.

R1 (misión de reparación 2026-10-04): el corta-circuito de proveedores de IA
(core.ai._CIRCUIT) es memoria de proceso; un test que simula "modelo retirado"
dejaría al proveedor en pausa para los tests siguientes.
"""
import os
import sys

import pytest

os.environ.setdefault('KHIPU_SCHEDULER', 'off')   # R5: el hilo periódico no arranca al importar server en tests


@pytest.fixture(autouse=True)
def _ai_circuits_cerrados():
    ai = sys.modules.get('core.ai')
    if ai is not None and hasattr(ai, '_CIRCUIT'):
        ai._CIRCUIT.clear()
    yield
    ai = sys.modules.get('core.ai')
    if ai is not None and hasattr(ai, '_CIRCUIT'):
        ai._CIRCUIT.clear()
