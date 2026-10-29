"""Navegador automatizado para la cuarentena de Google Admin.

Google no ofrece API para dar Allow/Deny en la cuarentena, así que el agente
usa un navegador. La sesión se guarda en /data (volumen de Railway) para no
iniciar sesión en cada corrida. Cada paso deja una captura en /data/debug,
que se puede ver desde el dashboard en /debug/<archivo>.
"""
import os

import pyotp
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

URL = "https://email-quarantine.google.com/adminreview"
DEBUG_DIR = "/data/debug"


class Quarantine:
    def __init__(self, client):
        self.c = client
        p = client["env"]
        self.email = os.environ[f"GOOGLE_{p}_EMAIL"]
        self.password = os.environ[f"GOOGLE_{p}_PASSWORD"]
        # Opcional: solo hace falta si la cuenta tiene verificación en dos pasos.
        self.totp = os.environ.get(f"GOOGLE_{p}_TOTP_SECRET", "").strip()

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            f"/data/profile-{self.c['key']}",
            headless=os.environ.get("HEADLESS", "true") == "true",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 1000},
            locale="en-US",
        )
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        return self

    def __exit__(self, *exc):
        self.ctx.close()
        self._pw.stop()

    def snap(self, name):
        os.makedirs(DEBUG_DIR, exist_ok=True)
        base = f"{DEBUG_DIR}/{self.c['key']}-{name}"
        try:
            self.page.screenshot(path=base + ".png", full_page=True)
            with open(base + ".txt", "w") as f:
                f.write(self.page.inner_text("body"))
        except Exception:
            pass

    def open(self):
        p = self.page
        p.goto(URL, wait_until="domcontentloaded")
        p.wait_for_timeout(3000)
        if "accounts.google.com" in p.url:
            self._login()
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(2500)
        if "email-quarantine.google.com" not in p.url:
            self.snap("login-fallo")
            raise RuntimeError("No se pudo entrar a la cuarentena. Revisa /debug/" + self.c["key"] + "-login-fallo.png")
        self.snap("lista")

    def _login(self):
        p = self.page
        email = p.locator('input[type="email"]')
        if email.count() and email.first.is_visible():
            email.first.fill(self.email)
            p.keyboard.press("Enter")
            p.wait_for_timeout(3000)

        p.wait_for_selector('input[type="password"]', timeout=20000)
        p.fill('input[type="password"]', self.password)
        p.keyboard.press("Enter")
        p.wait_for_timeout(4000)

        totp = p.locator('input[name="totpPin"], input#totpPin')
        if self.totp and not totp.count():
            # Si Google ofrece otro método primero, cambia a la app de autenticador.
            try:
                p.get_by_text("Try another way").click(timeout=5000)
                p.wait_for_timeout(2000)
                p.get_by_text("Google Authenticator").first.click(timeout=5000)
                p.wait_for_timeout(3000)
            except PWTimeout:
                pass
        if totp.count() and not self.totp:
            self.snap("login-fallo")
            raise RuntimeError("Google pidió el código del autenticador, pero GOOGLE_" + self.c["env"]
                               + "_TOTP_SECRET está vacía. Activa la verificación en dos pasos y agrega la clave en Railway.")
        if totp.count():
            totp.first.fill(pyotp.TOTP(self.totp).now())
            p.keyboard.press("Enter")
            p.wait_for_timeout(5000)

        if "accounts.google.com" in p.url:
            self.snap("login-fallo")
            raise RuntimeError("Google pidió una verificación que el agente no pudo completar. Revisa /debug/"
                               + self.c["key"] + "-login-fallo.png")

    def page_text(self):
        return self.page.inner_text("body")

    def act(self, subject, label):
        """Abre el correo por su asunto y presiona el botón Allow o Deny."""
        p = self.page
        p.get_by_text(subject, exact=False).first.click(timeout=15000)
        p.wait_for_timeout(2500)

        btn = p.get_by_role("button", name=label, exact=True)
        if not btn.count():
            btn = p.get_by_text(label, exact=True)
        btn.first.click(timeout=10000)
        p.wait_for_timeout(1500)

        # Si aparece una ventana de confirmación, confírmala.
        dialog = p.get_by_role("dialog")
        if dialog.count() and dialog.first.is_visible():
            dialog.first.get_by_role("button", name=label).first.click(timeout=10000)
            p.wait_for_timeout(1500)

        p.goto(URL, wait_until="domcontentloaded")
        p.wait_for_load_state("networkidle")
        p.wait_for_timeout(2000)
