import os

import requests

TITLE = "Gmail Admin Quarantine Alert"
SENDER = "noreply+workspace@google.com"
STATUS_COMPLETE = 5


class Autotask:
    def __init__(self):
        self.h = {
            "ApiIntegrationCode": os.environ["AUTOTASK_INTEGRATION_CODE"],
            "UserName": os.environ["AUTOTASK_USERNAME"],
            "Secret": os.environ["AUTOTASK_SECRET"],
            "Content-Type": "application/json",
        }
        # Autotask indica a qué servidor (zona) pertenece el usuario de API.
        z = requests.get(
            "https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation",
            params={"user": self.h["UserName"]}, timeout=30,
        )
        z.raise_for_status()
        self.base = z.json()["url"].rstrip("/") + "/V1.0"

    def _req(self, method, path, **kw):
        url = path if path.startswith("http") else self.base + path
        r = requests.request(method, url, headers=self.h, timeout=60, **kw)
        if not r.ok:
            raise RuntimeError(f"Autotask {method} {path}: {r.status_code} {r.text[:400]}")
        return r.json() if r.content else {}

    def quarantine_tickets(self, to_addr):
        """Tickets abiertos de cuarentena de Google para un cliente, del más viejo al más nuevo."""
        body = {"filter": [
            {"op": "beginsWith", "field": "title", "value": TITLE},
            {"op": "noteq", "field": "status", "value": STATUS_COMPLETE},
        ]}
        data = self._req("POST", "/Tickets/query", json=body)
        items = data.get("items", [])
        while (data.get("pageDetails") or {}).get("nextPageUrl"):
            data = self._req("GET", data["pageDetails"]["nextPageUrl"])
            items += data.get("items", [])

        to_line = f"to: {to_addr}".lower()
        mine = [
            t for t in items
            if to_line in (t.get("description") or "").lower()
            and SENDER in (t.get("description") or "").lower()
        ]
        return sorted(mine, key=lambda t: t.get("createDate") or "")

    def add_note(self, ticket, text):
        self._req("POST", f"/Tickets/{ticket['id']}/Notes", json={
            "ticketID": ticket["id"],
            "title": "Agente de cuarentenas",
            "description": text[:30000],
            "noteType": int(os.environ.get("AUTOTASK_NOTE_TYPE", "1")),
            "publish": 1,  # visible solo para usuarios internos
        })

    def close(self, ticket, text):
        self.add_note(ticket, text)
        self._req("PATCH", "/Tickets", json={
            "id": ticket["id"],
            "status": STATUS_COMPLETE,
            "resolution": text[:7000],
        })
