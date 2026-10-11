---
tipo: "modulo"
capa: "Comité"
ruta: "research/deliberation.py"
lenguaje: "python"
lineas: 361
aliases: ["research/deliberation.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# research/deliberation.py

> Módulo · capa [[Capa Comité]] · 361 líneas · `research/deliberation.py`

## Para qué sirve

la SALA DEL COMITÉ: puestos y conversación visible.

## API pública

- `seat_name(seat)` _(línea 52)_
- `stance_of(v)` _(línea 56)_
- `build_seats(conv, views, track, absent=…)` — [{seat, emoji, name_es, name_en, stance, net, n_claims, n_pos, n_neg, reliability, n_scored, hits}] — un puesto por agente con … _(línea 74)_
- `tally(seats)` _(línea 110)_
- `opening(label, symbol, seats, n_claims, n_rels)` — Mensaje inaugural del Presidente. _(línea 142)_
- `positions(seats, conv, claims_by_id, cref, evidence=…)` — Una intervención por puesto: su postura neta + su conclusión de mayor peso (texto real del claim) + su fuente principal + su historial. _(línea 168)_
- `rebuttals(rels, claims_by_id, cref, seats, max_n=…)` — Réplicas: cada contradicción detectada (X#) se vuelve un cruce entre los dos puestos. Sin contradicciones pero con posturas opuestas, la … _(línea 205)_
- `market_msg(live, symbol)` _(línea 255)_
- `risk_msg(risk, symbol)` _(línea 282)_
- `mandate_msg(client)` _(línea 302)_
- `quant_msg(overall, conv, decision, reason_es, reason_en, sizing, seats, dl)` _(línea 319)_
- `chair_close(body, final_decision, quant_decision, dl, ai_used)` — Cierre del Presidente: respuesta a cada disenso + veredicto. _(línea 336)_

**Internas** (empiezan con `_`): `_hz`, `_cut`, `_sent`, `_msg`, `_track_txt`, `_p`

## Depende de

_Nada interno._

## Lo usan

- [[research.ask_agent.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.debate.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_committee_os_narr.py]]
- [[tests.test_phase3.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-02 — SALA DEL COMITÉ - PUESTOS + DEBATE EN VIVO (sw v175)]]
