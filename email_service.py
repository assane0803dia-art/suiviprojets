"""
Service d'envoi d'email — utilise smtplib (bibliothèque standard de Python),
pas besoin d'un service tiers comme SendGrid.

Fonctionne avec n'importe quel serveur SMTP (Gmail, Outlook, etc.). Pour Gmail,
il faut un "mot de passe d'application" (pas votre mot de passe habituel) :
https://myaccount.google.com/apppasswords

Configuration requise dans .streamlit/secrets.toml :
    SMTP_HOST     = "smtp.gmail.com"
    SMTP_PORT     = 587
    SMTP_USER     = "votre.adresse@gmail.com"
    SMTP_PASSWORD = "le mot de passe d'application (16 caractères, sans espaces)"
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st


def is_configured() -> bool:
    return all(
        key in st.secrets
        for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
    )


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Envoie un email texte simple. Retourne (succès, message)."""
    if not is_configured():
        return False, "L'envoi d'email n'est pas configuré (SMTP_HOST/SMTP_USER/SMTP_PASSWORD manquants dans les secrets)."

    if not to_email:
        return False, "Aucune adresse email de destination renseignée."

    try:
        msg = MIMEMultipart()
        msg["From"] = st.secrets["SMTP_USER"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(st.secrets["SMTP_HOST"], int(st.secrets["SMTP_PORT"])) as server:
            server.starttls()
            server.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASSWORD"])
            server.send_message(msg)

        return True, f"Email envoyé avec succès à {to_email}."
    except Exception as e:
        return False, f"Échec de l'envoi : {e}"
