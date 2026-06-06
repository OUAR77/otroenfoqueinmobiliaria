#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fpdf import FPDF
import os

FONT_DIR = "C:/Windows/Fonts"

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "B", 9)
        self.set_text_color(220, 38, 38)
        self.cell(0, 8, "Otro Enfoque Inmobiliaria", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 38, 38)
        self.line(10, 14, 200, 14)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Arial", "B", 14)
        self.set_text_color(220, 38, 38)
        self.ln(6)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 38, 38)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def body_text(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(51, 51, 51)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(51, 51, 51)
        x = self.get_x()
        self.cell(6)
        self.cell(4, 5.5, "-")
        _, y = self.get_y(), self.get_y()
        self.set_xy(self.l_margin + 10, y)
        self.multi_cell(0, 5.5, text)

    def price_row(self, concept, price):
        self.set_font("Arial", "", 10)
        self.set_text_color(51, 51, 51)
        self.cell(130, 6, concept)
        self.set_font("Arial", "B", 10)
        self.cell(0, 6, price, align="R", new_x="LMARGIN", new_y="NEXT")


pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

pdf.add_font("Arial", "", os.path.join(FONT_DIR, "arial.ttf"))
pdf.add_font("Arial", "B", os.path.join(FONT_DIR, "arialbd.ttf"))
pdf.add_font("Arial", "I", os.path.join(FONT_DIR, "ariali.ttf"))
pdf.add_font("Arial", "BI", os.path.join(FONT_DIR, "arialbi.ttf"))

pdf.add_page()

# Title
pdf.set_font("Arial", "B", 24)
pdf.set_text_color(220, 38, 38)
pdf.cell(0, 14, "Otro Enfoque Inmobiliaria", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 13)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 8, "Memoria del desarrollo web", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)

# 1. Resumen
pdf.section_title("1. Resumen del proyecto")
pdf.body_text(
    "Desarrollo de sitio web profesional para Otro Enfoque Inmobiliaria, con sede en "
    "Huércal de Almería (C/ Río Júcar 17, 1º-oficina 3). El sitio incluye catálogo "
    "de propiedades con mapa interactivo, panel de administración, calculadora "
    "hipotecaria, chat con inteligencia artificial y página de reseñas de Google. "
    "Se entrega en dos formatos: servidor online (Python) y versión portátil "
    "autocontenida (USB, sin necesidad de instalar nada)."
)

# 2. Funcionalidades
pdf.section_title("2. Funcionalidades incluidas")

features = [
    "Diseño responsive adaptable a móviles, tablets y ordenadores.",
    "Colores corporativos: rojo (#DC2626) y blanco, tipografía Cinzel + Josefin Sans.",
    "Página principal con hero, propiedades destacadas, presentación del agente, servicios y reseñas.",
    "Catálogo de propiedades con buscador por texto, tipo de operación, tipo de inmueble, habitaciones y rango de precio.",
    "Mapa interactivo (Leaflet + OpenStreetMap) con marcadores y precios.",
    "Ficha detallada de cada propiedad con galería de imágenes, lightbox con zoom, mapa de situación y botón de WhatsApp.",
    "Panel de administración protegido con contraseña: alta, modificación y borrado de propiedades, gestión de imágenes, bandeja de mensajes.",
    "Formulario de contacto con almacenamiento en base de datos.",
    "Calculadora hipotecaria con resultados en tiempo real y botón de contacto por WhatsApp.",
    "Chatbot con inteligencia artificial (Groq API / Llama 3.3 70B) que responde preguntas sobre la agencia y las propiedades.",
    "Página de reseñas con valoraciones reales importadas de Google.",
    "SEO básico: meta tags, Open Graph, Twitter Cards, sitemap.xml.",
    "Enlace directo a WhatsApp en toda la web.",
    "Versión portátil en USB: ejecutable que funciona sin instalar nada, listo para presentaciones.",
]
for f in features:
    pdf.bullet(f)

# 3. Precios
pdf.section_title("3. Presupuesto")

pdf.set_font("Arial", "B", 10)
pdf.set_text_color(220, 38, 38)
pdf.cell(130, 7, "Concepto")
pdf.cell(0, 7, "Precio", align="R", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(200, 200, 200)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.set_text_color(51, 51, 51)

prices = [
    ("Desarrollo web completo (frontend + backend personalizado)", "750 EUR"),
    ("Chatbot con inteligencia artificial (Groq API)", ""),
    ("Calculadora hipotecaria interactiva", ""),
    ("Mapa interactivo con marcadores", ""),
    ("Panel de administración (propiedades, imágenes, mensajes)", ""),
    ("Página de reseñas con Google reviews", ""),
    ("SEO (meta tags, Open Graph, sitemap)", ""),
    ("", ""),
    ("Versión portátil USB (autocontenida, sin instalación)", "Incluido"),
    ("", ""),
    ("Configuración de dominio y hosting", "Consultar"),
    ("Mantenimiento mensual (opcional)", "Consultar"),
    ("", ""),
    ("TOTAL (desarrollo completo, pago único)", "750 EUR"),
]
for concept, price in prices:
    pdf.price_row(concept, price)

# 4. Condiciones
pdf.section_title("4. Condiciones")
pdf.body_text(
    "- El precio incluye el desarrollo completo del sitio web.\n"
    "- No incluye hosting, dominio ni certificado SSL (contratación aparte).\n"
    "- No incluye mantenimiento continuado ni actualizaciones de contenido (salvo acuerdo posterior).\n"
    "- El código fuente se entrega al cliente una vez realizado el pago completo.\n"
    "- Forma de pago: 50% al inicio, 50% a la entrega.\n"
    "- Tiempo de desarrollo estimado: 2-3 semanas.\n"
    "- Garantía de corrección de errores: 30 días desde la entrega."
)

# 5. Tecnología
pdf.section_title("5. Tecnología utilizada")
pdf.body_text(
    "Backend: Python 3.14 + FastAPI + SQLAlchemy + SQLite\n"
    "Frontend: Jinja2 + CSS personalizado + JavaScript nativo\n"
    "Mapa: Leaflet.js con OpenStreetMap\n"
    "Chatbot: Groq API (Llama 3.3 70B) + preguntas frecuentes\n"
    "Iconos: Font Awesome\n"
    "Tipografía: Google Fonts (Cinzel + Josefin Sans)\n"
    "Versión portátil: PyInstaller (ejecutable autocontenido, sin dependencias)"
)

# 6. Contacto
pdf.section_title("6. Contacto")
pdf.body_text(
    "Daniel R. (Desarrollador)\n\n"
    "Teléfono: 614 28 51 35\n\n"
    "Para cualquier duda, modificación o ampliación, no dudes en consultar."
)

out = "C:\\Users\\DaniR\\Projects\\otroenfoqueinmobiliaria\\Memoria_Web_OtroEnfoque.pdf"
pdf.output(out)
print(f"PDF creado: {out}")
print(f"Tamaño: {os.path.getsize(out) / 1024:.0f} KB")
