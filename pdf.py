import streamlit as st
import PyPDF2
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import requests

# Configuración de la página
st.set_page_config(
    page_title="Corrector de Textos en Español",
    layout="wide",
)

# Título de la aplicación
st.title("Corrector de Gramática y Estilo para Textos en Español")

# Instrucciones
st.markdown("""
Esta aplicación permite subir un archivo PDF y corregirlo en hasta **200,000 caracteres**. 
Selecciona el nivel de corrección y descarga el documento corregido en formato PDF manteniendo el formato original tanto como sea posible.
""")

# Carga de la clave API desde los secretos de Streamlit
OPENROUTER_API_KEY = st.secrets["openrouter"]["api_key"]

# Función para extraer texto del PDF
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# Función para dividir el texto en chunks si es necesario
def split_text(text, max_length=1500):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= max_length:
            current_chunk += para + "\n"
        else:
            chunks.append(current_chunk)
            current_chunk = para + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# Función para corregir el texto usando la API de OpenRouter
def correct_text(text, level):
    if level == "Mínimo":
        prompt = "Corrige la ortografía y la puntuación del siguiente texto en español:\n\n" + text
    elif level == "Intermedio":
        prompt = "Corrige la ortografía, gramática y puntuación del siguiente texto en español:\n\n" + text
    elif level == "Avanzado":
        prompt = "Corrige la ortografía, gramática y puntuación del siguiente texto en español. Además, mejora el estilo y ofrece sugerencias de redacción:\n\n" + text
    else:
        prompt = text  # Default to no correction

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        st.error(f"Error en la API: {response.status_code} - {response.text}")
        return None

# Función para generar un PDF a partir del texto corregido
def generate_pdf(original_pdf, corrected_text):
    reader = PyPDF2.PdfReader(original_pdf)
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Simplemente agregando el texto corregido; mantener el formato original es complejo
    # Para una mejor preservación del formato, se necesitarían herramientas más avanzadas
    text_object = can.beginText(40, 750)
    for line in corrected_text.split('\n'):
        text_object.textLine(line)
    can.drawText(text_object)
    can.save()

    packet.seek(0)
    new_pdf = PyPDF2.PdfReader(packet)
    writer = PyPDF2.PdfWriter()

    # Agregar las páginas originales y sobreponer el texto corregido
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        if page_num < len(new_pdf.pages):
            page.merge_page(new_pdf.pages[page_num])
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()

# Interfaz de usuario para subir el archivo PDF
uploaded_file = st.file_uploader("Sube tu archivo PDF", type=["pdf"])

# Selección del nivel de corrección
correction_level = st.selectbox(
    "Selecciona el nivel de corrección",
    ("Mínimo (Ortografía y Puntuación)", "Intermedio (Ortografía, Gramática y Puntuación)", "Avanzado (Incluye Estilo y Redacción)")
)

if uploaded_file is not None:
    with st.spinner("Extrayendo texto del PDF..."):
        text = extract_text_from_pdf(uploaded_file)
    
    if len(text) > 200000:
        st.error("El documento supera los 200,000 caracteres. Por favor, sube un archivo más pequeño.")
    else:
        st.success("Texto extraído exitosamente.")
        st.text_area("Texto Extraído", text, height=300)

        if st.button("Corregir Texto"):
            with st.spinner("Corrigiendo el texto..."):
                # Determinar el nivel de corrección
                if correction_level.startswith("Mínimo"):
                    level = "Mínimo"
                elif correction_level.startswith("Intermedio"):
                    level = "Intermedio"
                else:
                    level = "Avanzado"

                # Dividir el texto en chunks si es muy largo
                chunks = split_text(text)
                corrected_chunks = []

                for i, chunk in enumerate(chunks):
                    st.write(f"Corrigiendo chunk {i+1} de {len(chunks)}...")
                    corrected = correct_text(chunk, level)
                    if corrected:
                        corrected_chunks.append(corrected)
                    else:
                        st.error("Error al corregir el texto.")
                        break

                corrected_text = "\n".join(corrected_chunks)

                if corrected_text:
                    st.success("Texto corregido exitosamente.")
                    st.text_area("Texto Corregido", corrected_text, height=300)

                    # Generar el PDF corregido
                    corrected_pdf = generate_pdf(uploaded_file, corrected_text)

                    st.download_button(
                        label="Descargar PDF Corregido",
                        data=corrected_pdf,
                        file_name="corregido.pdf",
                        mime="application/pdf"
                    )
