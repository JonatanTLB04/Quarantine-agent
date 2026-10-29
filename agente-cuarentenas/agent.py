"""Una corrida del agente: Autotask -> Google -> Claude -> Google -> Autotask -> registro."""
import os
import traceback

import db
from autotask import Autotask
from config import CLIENTS
from decide import classify
from google_quarantine import Quarantine

MODE = os.environ.get("MODO", "observacion")  # "observacion" o "real"
LABEL = {
    "allow": os.environ.get("GOOGLE_ALLOW_LABEL", "Allow"),
    "deny": os.environ.get("GOOGLE_DENY_LABEL", "Deny"),
}


def run_all():
    at = Autotask()
    for c in CLIENTS:
        try:
            run_client(at, c)
        except Exception as e:
            traceback.print_exc()
            db.add(client=c["name"], kind="error", result="error", mode=MODE,
                   detail=f"{type(e).__name__}: {e}")


def run_client(at, c):
    tickets = at.quarantine_tickets(c["to"])
    if not tickets:
        return  # nada que hacer: no entra a Google si no hay tickets
    numbers = ", ".join(t["ticketNumber"] for t in tickets)

    done = []
    with Quarantine(c) as q:
        q.open()
        for m in classify(c["name"], q.page_text()):
            d = m["decision"]
            if d == "unsure":
                action = "Ninguna"
            elif MODE != "real":
                action = f"Habría dado {LABEL[d]}"
            else:
                try:
                    q.act(m["subject"], LABEL[d])
                    action = LABEL[d]
                except Exception as e:
                    q.snap("accion-fallo")
                    m["why"] = f"{m.get('why', '')} No se pudo aplicar {LABEL[d]}: {e}"
                    m["decision"] = "unsure"
                    action = "Error"
            done.append((m, action))

    unsure = [m for m, _ in done if m["decision"] == "unsure"]
    resumen = "\n".join(f"- {a}: \"{m.get('subject')}\" de {m.get('sender')}. {m.get('why')}" for m, a in done) \
        or "- La cuarentena ya estaba vacía."
    keep = tickets[-1] if unsure else None
    to_close = [t for t in tickets if t is not keep]

    if MODE == "real":
        for t in to_close:
            at.close(t, f"Resuelto automáticamente por el agente de cuarentenas.\n\n{resumen}")
        if keep:
            at.add_note(keep, "El agente no pudo decidir con seguridad sobre estos correos; "
                              "siguen en cuarentena y requieren revisión manual.\n\n"
                        + "\n".join(f"- \"{m.get('subject')}\" de {m.get('sender')}. {m.get('why')}" for m in unsure))
        ticket_detail = (f"Cerrados: {', '.join(t['ticketNumber'] for t in to_close) or 'ninguno'}"
                         + (f". Abierto para revisión: {keep['ticketNumber']}" if keep else ""))
        ticket_result = "review" if keep else "ok"
    else:
        ticket_detail = (f"Habría cerrado: {', '.join(t['ticketNumber'] for t in to_close) or 'ninguno'}"
                         + (f". Habría dejado abierto: {keep['ticketNumber']}" if keep else ""))
        ticket_result = "observacion"

    for m, a in done:
        result = "review" if m["decision"] == "unsure" else ("ok" if MODE == "real" else "observacion")
        db.add(client=c["name"], kind="message", sender=m.get("sender"), subject=m.get("subject"),
               recipient=m.get("recipient"), decision=m["decision"], category=m.get("category"),
               why=m.get("why"), google_action=a, tickets=numbers, result=result, mode=MODE)
    db.add(client=c["name"], kind="tickets", tickets=numbers, result=ticket_result,
           mode=MODE, detail=ticket_detail)
