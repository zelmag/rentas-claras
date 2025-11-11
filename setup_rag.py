# type: ignore
import os
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from dotenv import load_dotenv
from llama_index.core.llms import ChatMessage
from tenacity import retry, stop_after_attempt, wait_exponential

# Cargar variables de entorno (incluida GEMINI_API_KEY)
load_dotenv()

# --- CONFIGURACIÓN DE LOS MODELOS ---
# Usamos el modelo de embeddings específico de Gemini
embed_model = GoogleGenAIEmbedding(model_name="models/embedding-001")

# Configure LLM with more aggressive retries
llm = GoogleGenAI(
    model="models/gemini-2.0-flash",
    max_retries=5,  # Increase retries
    timeout=60  # Increase timeout
)

# 1. Función de Indexación
def setup_mexico_rag_index(data_dir="data", persist_dir="./storage"):
    """
    Carga el texto legal desde la carpeta 'data', lo indexa y guarda.
    Si ya existe un índice guardado, lo carga en lugar de recalcularlo.
    """
    # Check if index already exists
    if os.path.exists(persist_dir):
        print("Índice existente encontrado. Cargando desde disco...")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context, embed_model=embed_model)
        print("Índice cargado exitosamente.")
        return index
    
    # If no index exists, create it
    print("No se encontró índice. Creando uno nuevo...")
    
    # 1. Asegurar que el archivo de ley esté en la carpeta 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    # Crea el archivo de ley temporalmente para este ejemplo (asegúrate de que tu archivo 'mexican_law.txt' esté en esta carpeta)
    law_text = """
LEY APLICABLE: Ley de Aviación Civil Mexicana (LACM)

--- COMPENSACIONES POR DEMORA (Artículo 47 Bis) ---

1. DEMORA INTERMEDIA (Superior a 1 hora e Inferior a 4 horas):
    La persona pasajera será compensada conforme a las políticas de compensación de la aerolínea, las cuales deben incluir mínimamente descuentos para vuelos en fecha posterior, alimentos y bebidas o una combinación de estos.
    
    *REGLA CLAVE:* Si la demora es **mayor a dos horas pero menor a cuatro**, los descuentos incluidos en las políticas de compensación no podrán ser **menores al 7.5% del precio del boleto**.

2. DEMORA GRAVE Y CANCELACIÓN (Mayor a 4 horas o Cancelación):
    La persona pasajera será compensada conforme a la Ley, y debe elegir entre:
    
    A. **Reintegro Monetario + Indemnización (la opción para ZelmaHelps):** Reintegrar el 100% del precio del boleto (o la parte no realizada), MÁS una indemnización a la persona pasajera no inferior al **veinticinco por ciento (25%) del precio del boleto** o de la parte no realizada del viaje.
    
    B. Transporte Sustituto: Ofrecer transporte sustituto en el primer vuelo disponible y proporcionar sin cargo: llamadas, correos, alimentos, alojamiento y transporte terrestre si es necesaria pernocta.

--- PLAZO Y AUTORIDAD (Art. 47 Bis y Autoridad) ---

PLAZO DE PAGO:
Las indemnizaciones deberán cubrirse en un periodo máximo de **diez días naturales** posteriores a la reclamación del pasajero.

AUTORIDAD Y SANCIONES:
Las infracciones a los derechos de los pasajeros serán sancionadas por **PROFECO** (Procuraduría Federal del Consumidor), y ninguna cláusula puede anular el pago de las indemnizaciones.
"""
    with open(os.path.join(data_dir, "mexican_law.txt"), "w", encoding="utf-8") as f:
        f.write(law_text)


    print("Iniciando la lectura y el embedding de la Ley Mexicana...")
    
    # LlamaIndex lee todos los documentos en la carpeta 'data'
    documents = SimpleDirectoryReader(data_dir).load_data()

    # Crea el índice vectorial (el Knowledge Vault)
    # LlamaIndex usa el embed_model configurado para hacer el "chunking" y crear los embeddings
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"Índice guardado en {persist_dir}")
    print("Indexación completada. Índice listo para ser consultado.")
    return index

def setup_airline_policies_index(data_dir="data/airline_policies", persist_dir="./storage_airlines"):
    """
    Load and index airline policies
    """
    if os.path.exists(persist_dir):
        print("Índice de políticas encontrado. Cargando...")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context, embed_model=embed_model)
        return index
    
    print("Creando índice de políticas de aerolíneas...")
    documents = SimpleDirectoryReader(data_dir).load_data()
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    index.storage_context.persist(persist_dir=persist_dir)
    return index

if __name__ == "__main__":
    # --- Ejecutar la Indexación ---
    mexico_index = setup_mexico_rag_index()
    airline_index = setup_airline_policies_index() 
        
    query_engine = mexico_index.as_query_engine(llm=llm)
    
    print("\n--- PRUEBA DE RECUPERACIÓN (RAG) ---")
    response = query_engine.query("¿Cuál es la compensación mínima si un vuelo se cancela y en cuántos días se debe pagar?")
    
    print(f"\nRespuesta de Gemini (usando tu ley):\n{response}")
    
    # Verificación: La respuesta debería citar el 25% y 10 días.
