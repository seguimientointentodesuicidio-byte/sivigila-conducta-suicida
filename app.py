"""
SIVIGILA - Vigilancia Conducta Suicida | Valle del Cauca
Evento 356 - Intento de Suicidio
Secretaría Departamental de Salud del Valle del Cauca

Aplicativo web para vigilancia y seguimiento de casos de conducta suicida.
Stack: Streamlit + Google Sheets (gspread) + Plotly
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import hashlib
import json
import io
import time

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="SIVIGILA - Conducta Suicida | Valle del Cauca",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Colores institucionales ---
COLOR_AZUL_OSCURO = "#1B3A5C"
COLOR_AZUL_MEDIO = "#2E6B9E"
COLOR_BLANCO = "#FFFFFF"
COLOR_GRIS_CLARO = "#F0F2F6"
COLOR_ROJO_ALERTA = "#D32F2F"
COLOR_AMARILLO_ALERTA = "#F9A825"

# --- CSS personalizado ---
st.markdown(f"""
<style>
    /* Header principal */
    .main-header {{
        background: linear-gradient(135deg, {COLOR_AZUL_OSCURO}, {COLOR_AZUL_MEDIO});
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }}
    .main-header h1 {{
        font-size: 1.6rem;
        margin: 0;
        font-weight: 700;
    }}
    .main-header p {{
        font-size: 0.9rem;
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
    }}

    /* KPI cards */
    .kpi-card {{
        background: white;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid {COLOR_AZUL_OSCURO};
    }}
    .kpi-card .kpi-value {{
        font-size: 2.2rem;
        font-weight: 800;
        color: {COLOR_AZUL_OSCURO};
        line-height: 1.1;
    }}
    .kpi-card .kpi-label {{
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.3rem;
        font-weight: 500;
    }}
    .kpi-card-danger {{
        border-left-color: {COLOR_ROJO_ALERTA};
    }}
    .kpi-card-danger .kpi-value {{
        color: {COLOR_ROJO_ALERTA};
    }}
    .kpi-card-warning {{
        border-left-color: {COLOR_AMARILLO_ALERTA};
    }}
    .kpi-card-warning .kpi-value {{
        color: {COLOR_AMARILLO_ALERTA};
    }}

    /* Alerta tables */
    .alerta-roja {{
        background: #FFEBEE;
        border-left: 4px solid {COLOR_ROJO_ALERTA};
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }}
    .alerta-amarilla {{
        background: #FFF8E1;
        border-left: 4px solid {COLOR_AMARILLO_ALERTA};
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }}

    /* Login */
    .login-container {{
        max-width: 420px;
        margin: 3rem auto;
        padding: 2.5rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        text-align: center;
    }}
    .login-container h2 {{
        color: {COLOR_AZUL_OSCURO};
        margin-bottom: 0.3rem;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLOR_AZUL_OSCURO} 0%, #0D2137 100%);
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label {{
        color: white !important;
    }}

    /* Success message */
    .success-box {{
        background: #E8F5E9;
        border: 1px solid #4CAF50;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {COLOR_GRIS_CLARO};
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.5rem;
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LISTAS DE DATOS (Constantes)
# ============================================================

MUNICIPIOS_VALLE = [
    "ALCALA", "ANDALUCIA", "ANSERMANUEVO", "ARGELIA", "BOLIVAR",
    "BUENAVENTURA", "BUGA", "BUGALAGRANDE", "CAICEDONIA", "CALI",
    "CALIMA-DARIEN", "CANDELARIA", "CARTAGO", "DAGUA", "EL AGUILA",
    "EL CAIRO", "EL CERRITO", "EL DOVIO", "FLORIDA", "GINEBRA",
    "GUACARI", "JAMUNDI", "LA CUMBRE", "LA UNION", "LA VICTORIA",
    "OBANDO", "PALMIRA", "PRADERA", "RESTREPO", "RIOFRIO",
    "ROLDANILLO", "SAN PEDRO", "SEVILLA", "TORO", "TRUJILLO",
    "TULUA", "ULLOA", "VERSALLES", "VIJES", "YOTOCO", "YUMBO", "ZARZAL"
]

EPS_LISTA = [
    "ALIANSALUD", "ANAS WAYUU EPSI", "ASMET SALUD",
    "ASOCIACIÓN INDÍGENA DEL CAUCA EPSI", "CAJACOPI ATLÁNTICO",
    "CAPITAL SALUD", "CAPRESOCA", "COMFACHOCÓ", "COMFAORIENTE",
    "COMFENALCO VALLE", "COMPENSAR", "COOSALUD",
    "DUSAKAWI EPSI", "EMSSANAR",
    "EPM (EMPRESAS PÚBLICAS DE MEDELLÍN)", "EPS FAMILIAR DE COLOMBIA",
    "FAMISANAR", "FONDO PASIVO SOCIAL FERROCARRILES",
    "MALLAMAS EPSI", "MUTUAL SER", "NUEVA EPS",
    "PIJAOS SALUD EPSI", "SALUD MÍA", "SALUD TOTAL",
    "SANITAS", "SAVIA SALUD",
    "SOS (SERVICIO OCCIDENTAL DE SALUD)", "SURA",
    "OTRA (especificar)"
]

CURSOS_VIDA = [
    "Primera infancia (0-5 años)",
    "Infancia (6-11 años)",
    "Adolescencia (12-17 años)",
    "Juventud (18-28 años)",
    "Adultez (29-59 años)",
    "Vejez (60+ años)"
]


def calcular_curso_vida(edad):
    """Calcula el curso de vida a partir de la edad."""
    edad = int(edad) if edad else 0
    if edad <= 5:
        return "Primera infancia (0-5 años)"
    elif edad <= 11:
        return "Infancia (6-11 años)"
    elif edad <= 17:
        return "Adolescencia (12-17 años)"
    elif edad <= 28:
        return "Juventud (18-28 años)"
    elif edad <= 59:
        return "Adultez (29-59 años)"
    else:
        return "Vejez (60+ años)"

TIPOS_DOCUMENTO = ["CC", "TI", "RC", "CE", "PA", "MS"]

ESTADOS_CASO = [
    "ACTIVO", "CERRADO", "EN SEGUIMIENTO",
    "REMITIDO A OTRA EPS", "FALLECIDO", "SIN CONTACTO"
]

# Columnas de la hoja DATOS en Google Sheets
COLUMNAS_DATOS = [
    "id", "fecha_digitacion", "funcionario_reporta", "eps_reporta",
    "semana_epidemiologica", "ciclo_vital", "intento_previo",
    "nombres", "apellidos", "tipo_documento", "numero_documento",
    "edad", "sexo", "municipio_residencia",
    "fecha_notificacion_sivigila", "fecha_atencion_medicina",
    "hospitalizacion", "fecha_alta",
    "valoracion_psicologia", "fecha_psicologia",
    "valoracion_psiquiatria", "fecha_psiquiatria",
    "seguimiento_1", "seguimiento_2", "seguimiento_3",
    "ruta_salud_mental", "asiste_servicios",
    "seguimiento_7dias_postalta", "fecha_seguimiento_postalta",
    "num_seguimientos_realizados", "abandono_tratamiento",
    "reintento_posterior", "estado_caso", "observaciones",
    "ultima_modificacion_por", "ultima_modificacion_fecha"
]

# ============================================================
# FUNCIONES DE CONEXIÓN A GOOGLE SHEETS
# ============================================================

def obtener_conexion_gsheets():
    """
    Conecta a Google Sheets usando las credenciales de la cuenta de servicio
    almacenadas en st.secrets.
    Retorna el objeto spreadsheet.
    """
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {str(e)}")
        st.info("Verifique que las credenciales en st.secrets estén correctamente configuradas.")
        return None


def obtener_hoja_datos(spreadsheet):
    """Retorna la hoja 'DATOS' del spreadsheet."""
    try:
        return spreadsheet.worksheet("DATOS")
    except gspread.exceptions.WorksheetNotFound:
        # Crear la hoja si no existe, con los encabezados
        hoja = spreadsheet.add_worksheet(title="DATOS", rows=1000, cols=len(COLUMNAS_DATOS))
        hoja.append_row(COLUMNAS_DATOS)
        return hoja


def obtener_hoja_usuarios(spreadsheet):
    """Retorna la hoja 'USUARIOS' del spreadsheet."""
    try:
        return spreadsheet.worksheet("USUARIOS")
    except gspread.exceptions.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title="USUARIOS", rows=100, cols=5)
        hoja.append_row(["usuario", "password_hash", "nombre_completo", "rol", "eps_asignada"])
        return hoja


# ============================================================
# FUNCIONES DE DATOS (CRUD)
# ============================================================

def cargar_datos(spreadsheet, forzar=False):
    """
    Carga todos los registros de la hoja DATOS como DataFrame.
    Usa caché de session_state con TTL manual para no saturar la API.
    """
    ahora = time.time()
    cache_key = "_datos_cache"
    cache_time_key = "_datos_cache_time"

    if not forzar and cache_key in st.session_state:
        if ahora - st.session_state.get(cache_time_key, 0) < 60:
            return st.session_state[cache_key]

    try:
        hoja = obtener_hoja_datos(spreadsheet)
        all_values = hoja.get_all_values()
        if len(all_values) > 1:
            num_cols = len(COLUMNAS_DATOS)
            # Forzar encabezados definidos (ignorar lo que diga la hoja)
            # Rellenar filas cortas con cadenas vacías
            datos = [(row + [''] * num_cols)[:num_cols] for row in all_values[1:]]
            df = pd.DataFrame(datos, columns=COLUMNAS_DATOS)
            # Eliminar filas completamente vacías
            df = df[df.apply(lambda row: any(str(v).strip() != '' for v in row), axis=1)]
        else:
            df = pd.DataFrame(columns=COLUMNAS_DATOS)
        st.session_state[cache_key] = df
        st.session_state[cache_time_key] = ahora
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=COLUMNAS_DATOS)


def col_num_a_letra(n):
    """Convierte número de columna (1-indexado) a letra(s) de Excel. Ej: 1→A, 27→AA, 36→AJ."""
    resultado = ""
    while n > 0:
        n, residuo = divmod(n - 1, 26)
        resultado = chr(65 + residuo) + resultado
    return resultado


def generar_id():
    """Genera un ID único basado en timestamp."""
    return f"CS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{int(time.time()*1000) % 10000}"


def guardar_registro(spreadsheet, datos_dict):
    """
    Guarda un nuevo registro en la hoja DATOS.
    datos_dict: diccionario con las columnas como claves.
    """
    try:
        hoja = obtener_hoja_datos(spreadsheet)
        datos_dict["id"] = generar_id()
        datos_dict["fecha_digitacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        datos_dict["ultima_modificacion_por"] = datos_dict.get("funcionario_reporta", "")
        datos_dict["ultima_modificacion_fecha"] = datos_dict["fecha_digitacion"]

        fila = [str(datos_dict.get(col, "")) for col in COLUMNAS_DATOS]
        hoja.append_row(fila, value_input_option="USER_ENTERED", table_range="A1")

        # Invalidar caché
        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        return True, datos_dict["id"]
    except Exception as e:
        return False, str(e)


def actualizar_registro(spreadsheet, id_registro, datos_dict, usuario_modifica):
    """
    Actualiza un registro existente buscando por ID.
    """
    try:
        hoja = obtener_hoja_datos(spreadsheet)
        # Buscar la fila con el ID
        celdas_col_a = hoja.col_values(1)  # Columna A = id
        fila_num = None
        for i, valor in enumerate(celdas_col_a):
            if valor.strip() == str(id_registro).strip():
                fila_num = i + 1  # gspread es 1-indexado
                break

        if fila_num is None:
            return False, "Registro no encontrado."

        datos_dict["ultima_modificacion_por"] = usuario_modifica
        datos_dict["ultima_modificacion_fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        fila = [str(datos_dict.get(col, "")) for col in COLUMNAS_DATOS]
        # Actualizar rango completo de la fila
        rango = f"A{fila_num}:{col_num_a_letra(len(COLUMNAS_DATOS))}{fila_num}"
        hoja.update(rango, [fila], value_input_option="USER_ENTERED")

        # Invalidar caché
        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        return True, "Actualizado correctamente."
    except Exception as e:
        return False, str(e)


def buscar_por_documento(df, numero_doc):
    """Busca pacientes por número de documento."""
    if df.empty:
        return pd.DataFrame()
    numero_doc = str(numero_doc).strip()
    resultado = df[df["numero_documento"].astype(str).str.strip() == numero_doc]
    return resultado


# ============================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================

def hash_password(password):
    """Genera hash SHA-256 de la contraseña."""
    return hashlib.sha256(password.encode()).hexdigest()


def verificar_credenciales(spreadsheet, usuario, password):
    """
    Verifica las credenciales contra la hoja USUARIOS.
    Retorna (True, datos_usuario) o (False, None).
    """
    try:
        hoja = obtener_hoja_usuarios(spreadsheet)
        registros = hoja.get_all_records()
        password_hash = hash_password(password)

        for reg in registros:
            if (reg.get("usuario", "").strip().lower() == usuario.strip().lower()
                    and reg.get("password_hash", "").strip() == password_hash):
                return True, {
                    "usuario": reg["usuario"],
                    "nombre_completo": reg.get("nombre_completo", usuario),
                    "rol": reg.get("rol", "EPS").upper(),
                    "eps_asignada": reg.get("eps_asignada", "")
                }
        return False, None
    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")
        return False, None


def crear_usuario(spreadsheet, usuario, password, nombre_completo, rol, eps_asignada):
    """Crea un nuevo usuario en la hoja USUARIOS."""
    try:
        hoja = obtener_hoja_usuarios(spreadsheet)
        registros = hoja.get_all_records()

        # Verificar duplicados
        for reg in registros:
            if reg.get("usuario", "").strip().lower() == usuario.strip().lower():
                return False, "El usuario ya existe."

        password_hash = hash_password(password)
        hoja.append_row([usuario, password_hash, nombre_completo, rol, eps_asignada])
        return True, "Usuario creado exitosamente."
    except Exception as e:
        return False, str(e)


# ============================================================
# FUNCIÓN: Filtrar datos según rol
# ============================================================

def filtrar_por_rol(df):
    """Filtra el DataFrame según el rol del usuario logueado."""
    if st.session_state.get("rol") == "SECRETARIA":
        return df
    else:
        eps_usuario = st.session_state.get("eps_asignada", "")
        if eps_usuario and not df.empty:
            return df[df["eps_reporta"] == eps_usuario]
        return df


# ============================================================
# PANTALLA DE LOGIN
# ============================================================

def mostrar_login():
    """Muestra la pantalla de inicio de sesión."""
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo centrado
        try:
            st.image("Imagen1.png", width=250, use_container_width=False)
        except:
            st.markdown(f"""
            <div style="text-align:center; padding:1rem;">
                <h2 style="color:{COLOR_AZUL_OSCURO};">🏥 Gobernación del Valle del Cauca</h2>
                <p style="color:#666;">Secretaría Departamental de Salud</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center; margin-bottom:1.5rem;">
            <h3 style="color:{COLOR_AZUL_OSCURO}; margin-bottom:0.2rem;">
                SIVIGILA - Vigilancia Conducta Suicida
            </h3>
            <p style="color:#888; font-size:0.85rem;">Evento 356 | Valle del Cauca</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
            submitted = st.form_submit_button("🔑 Ingresar", use_container_width=True)

            if submitted:
                if not usuario or not password:
                    st.error("⚠️ Ingrese usuario y contraseña.")
                else:
                    spreadsheet = obtener_conexion_gsheets()
                    if spreadsheet:
                        valido, datos_usuario = verificar_credenciales(spreadsheet, usuario, password)
                        if valido:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario"] = datos_usuario["usuario"]
                            st.session_state["nombre_completo"] = datos_usuario["nombre_completo"]
                            st.session_state["rol"] = datos_usuario["rol"]
                            st.session_state["eps_asignada"] = datos_usuario["eps_asignada"]
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas. Verifique usuario y contraseña.")

        st.markdown("""
        <div style="text-align:center; margin-top:2rem; color:#aaa; font-size:0.75rem;">
            <p>Sistema de vigilancia epidemiológica - Uso institucional exclusivo</p>
            <p>Secretaría Departamental de Salud | Gobernación del Valle del Cauca</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# SIDEBAR (después de login)
# ============================================================

def mostrar_sidebar():
    """Configura el sidebar con logo, info de usuario y navegación."""
    with st.sidebar:
        try:
            st.image("Imagen1.png", width=200)
        except:
            st.markdown(f"### 🏥 Gobernación del Valle del Cauca")

        st.markdown("---")
        st.markdown(f"**👤 {st.session_state.get('nombre_completo', '')}**")
        st.markdown(f"🏷️ Rol: **{st.session_state.get('rol', '')}**")
        if st.session_state.get("rol") == "EPS":
            st.markdown(f"🏥 EPS: **{st.session_state.get('eps_asignada', '')}**")
        st.markdown("---")

        # Menú de navegación
        opciones = [
            "📊 Tablero de Control",
            "📝 Registrar Nuevo Caso",
            "✏️ Editar / Actualizar Caso",
            "📥 Exportar Datos"
        ]
        if st.session_state.get("rol") == "SECRETARIA":
            opciones.append("📤 Carga Masiva")
            opciones.append("⚙️ Gestionar Usuarios")

        pagina = st.radio("Navegación", opciones, label_visibility="collapsed")

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown(f"""
        <div style="position:fixed; bottom:10px; font-size:0.7rem; opacity:0.6;">
            SIVIGILA Evento 356<br>
            Valle del Cauca v1.0
        </div>
        """, unsafe_allow_html=True)

        return pagina


# ============================================================
# MÓDULO 1: FORMULARIO DE DIGITACIÓN
# ============================================================

def modulo_formulario(spreadsheet):
    """Formulario de registro de nuevos casos."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📝 Registro de Nuevo Caso - Conducta Suicida</h1>
        <p>Evento 356 SIVIGILA | Formulario de Digitación</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Formulario principal ---
    with st.form("formulario_nuevo_caso", clear_on_submit=True):
        # ---- Sección: Identificación del Caso ----
        st.markdown(f"#### 🏷️ Identificación del Caso")
        col1, col2 = st.columns(2)
        with col1:
            # EPS: auto-fill para rol EPS
            if st.session_state.get("rol") == "EPS":
                eps_seleccionada = st.session_state.get("eps_asignada", "")
                st.text_input("EPS/EAPB que reporta *", value=eps_seleccionada, disabled=True, key="eps_disabled")
            else:
                eps_seleccionada = st.selectbox("EPS/EAPB que reporta *", options=[""] + EPS_LISTA, key="eps_select")

            semana_epi = st.number_input("Semana epidemiológica *", min_value=1, max_value=53, value=1, step=1)
        with col2:
            intento_previo = st.radio("¿Antecedente de intento previo? *", options=["NO", "SI"], horizontal=True)

        # EPS "Otra" - campo adicional
        eps_otra = ""
        if st.session_state.get("rol") != "EPS" and eps_seleccionada == "OTRA (especificar)":
            eps_otra = st.text_input("Especifique la EPS:").upper()

        st.markdown("---")

        # ---- Sección: Datos del Paciente ----
        st.markdown(f"#### 👤 Datos del Paciente")
        col1, col2 = st.columns(2)
        with col1:
            nombres = st.text_input("Nombres *", placeholder="NOMBRES DEL PACIENTE")
            tipo_doc = st.selectbox("Tipo de documento *", options=TIPOS_DOCUMENTO)
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=0, step=1)
        with col2:
            apellidos = st.text_input("Apellidos *", placeholder="APELLIDOS DEL PACIENTE")
            numero_doc = st.text_input("Número de documento *", placeholder="Solo números")
            sexo = st.selectbox("Sexo *", options=["Masculino", "Femenino", "Indeterminado"])

        col1, col2 = st.columns(2)
        with col1:
            municipio = st.selectbox("Municipio de residencia *", options=[""] + MUNICIPIOS_VALLE)
        with col2:
            curso_vida = calcular_curso_vida(edad)
            st.text_input("Curso de vida (automático)", value=curso_vida, disabled=True)

        st.markdown("---")

        # ---- Sección: Notificación y Atención Inicial ----
        st.markdown(f"#### 📋 Notificación y Atención Inicial")
        col1, col2 = st.columns(2)
        with col1:
            fecha_notificacion = st.date_input("Fecha de notificación SIVIGILA *", value=date.today())
            hospitalizacion = st.selectbox("Hospitalización", options=["NO", "SI", "NO APLICA"])
        with col2:
            fecha_med_gral = st.date_input("Fecha atención medicina general", value=None)
            fecha_alta = st.date_input("Fecha de alta", value=None,
                                       help="Solo si hospitalización = SI")

        st.markdown("---")

        # ---- Sección: Atención en Salud Mental ----
        st.markdown(f"#### 🧠 Atención en Salud Mental")
        col1, col2 = st.columns(2)
        with col1:
            val_psicologia = st.selectbox("Valoración por Psicología", options=["NO", "SI", "NO APLICA"])
            fecha_psicologia = st.date_input("Fecha primera atención Psicología", value=None)
        with col2:
            val_psiquiatria = st.selectbox("Valoración por Psiquiatría", options=["NO", "SI", "NO APLICA"])
            fecha_psiquiatria = st.date_input("Fecha primera atención Psiquiatría", value=None)

        st.markdown("---")

        # ---- Sección: Seguimientos ----
        st.markdown(f"#### 📞 Seguimientos")
        seguimiento_1 = st.text_input("Seguimiento 1", placeholder="Ej: 13/03/2025 PSICOLOGÍA")
        seguimiento_2 = st.text_input("Seguimiento 2", placeholder="Ej: 20/03/2025 PSIQUIATRÍA")
        seguimiento_3 = st.text_input("Seguimiento 3", placeholder="Ej: 27/03/2025 PSICOLOGÍA")

        st.markdown("---")

        # ---- Sección: Seguimiento Post-Alta y Estado ----
        st.markdown(f"#### 📊 Seguimiento Post-Alta y Estado del Caso")
        col1, col2 = st.columns(2)
        with col1:
            ruta_salud_mental = st.selectbox("¿Se encuentra en ruta de salud mental?",
                                             options=["SI", "NO", "EN PROCESO"])
            asiste_servicios = st.selectbox("¿Asiste a los servicios?",
                                           options=["SI", "NO", "SIN CONTACTO"])
            seg_7dias = st.selectbox("Seguimiento ≤7 días post alta",
                                     options=["NO APLICA", "SI", "NO"])
        with col2:
            fecha_seg_postalta = st.date_input("Fecha del seguimiento post-alta", value=None)
            num_seguimientos = st.number_input("Número de seguimientos realizados",
                                               min_value=0, max_value=50, value=0)
            abandono = st.selectbox("¿Abandonó el tratamiento?",
                                    options=["NO", "SI", "SIN INFORMACIÓN"])

        col1, col2 = st.columns(2)
        with col1:
            reintento = st.selectbox("¿Reintento posterior?",
                                     options=["NO", "SI", "SIN INFORMACIÓN"])
        with col2:
            estado_caso = st.selectbox("Estado del caso *", options=ESTADOS_CASO)

        st.markdown("---")

        # ---- Sección: Observaciones ----
        st.markdown(f"#### 📝 Observaciones y Trazabilidad")
        observaciones = st.text_area("Observaciones",
                                     placeholder="Bitácora de gestión: llamadas, notas, derivaciones...",
                                     height=120)

        # Funcionario: auto-fill
        funcionario = st.text_input("Funcionario que reporta",
                                    value=st.session_state.get("nombre_completo", ""),
                                    disabled=True)

        st.markdown(f"📅 **Fecha de digitación:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # ---- Botón de guardar ----
        submitted = st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary")

        if submitted:
            # Validaciones
            errores = []
            eps_final = eps_seleccionada if eps_seleccionada != "OTRA (especificar)" else eps_otra
            if st.session_state.get("rol") == "EPS":
                eps_final = st.session_state.get("eps_asignada", "")

            if not eps_final:
                errores.append("EPS/EAPB es obligatorio.")
            if not nombres.strip():
                errores.append("Nombres es obligatorio.")
            if not apellidos.strip():
                errores.append("Apellidos es obligatorio.")
            if not numero_doc.strip():
                errores.append("Número de documento es obligatorio.")
            if not municipio:
                errores.append("Municipio de residencia es obligatorio.")
            if edad == 0:
                errores.append("Verifique que la edad sea correcta (actualmente es 0).")

            if errores:
                for err in errores:
                    st.error(f"⚠️ {err}")
            else:
                # Verificar duplicados por número de documento
                df_check = cargar_datos(spreadsheet, forzar=True)
                df_check = filtrar_por_rol(df_check)
                duplicados = buscar_por_documento(df_check, numero_doc)
                if not duplicados.empty:
                    st.warning(f"⚠️ Ya existe(n) **{len(duplicados)}** registro(s) con el documento **{numero_doc}**. "
                               "Si desea actualizar el caso existente, use el módulo 'Editar / Actualizar Caso'.")
                    cols_mostrar = ["nombres", "apellidos", "numero_documento", "eps_reporta",
                                    "estado_caso", "fecha_notificacion_sivigila"]
                    cols_disp = [c for c in cols_mostrar if c in duplicados.columns]
                    st.dataframe(duplicados[cols_disp], use_container_width=True, hide_index=True)
                else:
                    # Construir diccionario de datos
                    datos = {
                        "eps_reporta": eps_final,
                        "semana_epidemiologica": str(semana_epi),
                        "ciclo_vital": calcular_curso_vida(edad),
                        "intento_previo": intento_previo,
                        "nombres": nombres.upper().strip(),
                        "apellidos": apellidos.upper().strip(),
                        "tipo_documento": tipo_doc,
                        "numero_documento": numero_doc.strip(),
                        "edad": str(edad),
                        "sexo": sexo,
                        "municipio_residencia": municipio,
                        "fecha_notificacion_sivigila": str(fecha_notificacion) if fecha_notificacion else "",
                        "fecha_atencion_medicina": str(fecha_med_gral) if fecha_med_gral else "",
                        "hospitalizacion": hospitalizacion,
                        "fecha_alta": str(fecha_alta) if fecha_alta else "",
                        "valoracion_psicologia": val_psicologia,
                        "fecha_psicologia": str(fecha_psicologia) if fecha_psicologia else "",
                        "valoracion_psiquiatria": val_psiquiatria,
                        "fecha_psiquiatria": str(fecha_psiquiatria) if fecha_psiquiatria else "",
                        "seguimiento_1": seguimiento_1,
                        "seguimiento_2": seguimiento_2,
                        "seguimiento_3": seguimiento_3,
                        "ruta_salud_mental": ruta_salud_mental,
                        "asiste_servicios": asiste_servicios,
                        "seguimiento_7dias_postalta": seg_7dias,
                        "fecha_seguimiento_postalta": str(fecha_seg_postalta) if fecha_seg_postalta else "",
                        "num_seguimientos_realizados": str(num_seguimientos),
                        "abandono_tratamiento": abandono,
                        "reintento_posterior": reintento,
                        "estado_caso": estado_caso,
                        "observaciones": observaciones,
                        "funcionario_reporta": st.session_state.get("nombre_completo", ""),
                    }

                    with st.spinner("Guardando registro..."):
                        exito, resultado = guardar_registro(spreadsheet, datos)

                    if exito:
                        st.success(f"✅ Registro guardado exitosamente para **{nombres.upper()} {apellidos.upper()}** "
                                   f"(ID: {resultado})")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar: {resultado}")


# ============================================================
# MÓDULO 2: TABLERO DE CONTROL (DASHBOARD)
# ============================================================

def modulo_dashboard(spreadsheet):
    """Tablero de control con KPIs, gráficas y alertas."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 Tablero de Control - Vigilancia Conducta Suicida</h1>
        <p>Evento 356 SIVIGILA | Secretaría Departamental de Salud | Valle del Cauca</p>
    </div>
    """, unsafe_allow_html=True)

    # Cargar y filtrar datos
    df = cargar_datos(spreadsheet, forzar=False)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay datos registrados aún. Comience registrando casos en el módulo de Digitación.")
        return

    # Convertir tipos
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce").fillna(0).astype(int)
    df["num_seguimientos_realizados"] = pd.to_numeric(
        df["num_seguimientos_realizados"], errors="coerce").fillna(0).astype(int)
    df["semana_epidemiologica"] = pd.to_numeric(
        df["semana_epidemiologica"], errors="coerce").fillna(0).astype(int)

    # --- Filtros ---
    with st.expander("🔽 Filtros", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_eps = st.multiselect("EPS", options=sorted(df["eps_reporta"].unique().tolist()))
        with col2:
            filtro_municipio = st.multiselect("Municipio", options=sorted(df["municipio_residencia"].unique().tolist()))
        with col3:
            filtro_ciclo = st.multiselect("Curso de vida", options=sorted(df["ciclo_vital"].unique().tolist()))
        with col4:
            filtro_estado = st.multiselect("Estado del caso", options=sorted(df["estado_caso"].unique().tolist()))

        col1, col2 = st.columns(2)
        with col1:
            try:
                fechas_validas = pd.to_datetime(df["fecha_notificacion_sivigila"], errors="coerce").dropna()
                if not fechas_validas.empty:
                    fecha_min = fechas_validas.min().date()
                    fecha_max = fechas_validas.max().date()
                    filtro_fecha = st.date_input("Rango de fechas de notificación",
                                                 value=(fecha_min, fecha_max),
                                                 min_value=fecha_min, max_value=fecha_max)
                else:
                    filtro_fecha = None
            except:
                filtro_fecha = None

    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_eps:
        df_filtrado = df_filtrado[df_filtrado["eps_reporta"].isin(filtro_eps)]
    if filtro_municipio:
        df_filtrado = df_filtrado[df_filtrado["municipio_residencia"].isin(filtro_municipio)]
    if filtro_ciclo:
        df_filtrado = df_filtrado[df_filtrado["ciclo_vital"].isin(filtro_ciclo)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["estado_caso"].isin(filtro_estado)]
    if filtro_fecha and isinstance(filtro_fecha, tuple) and len(filtro_fecha) == 2:
        df_filtrado["_fecha_temp"] = pd.to_datetime(df_filtrado["fecha_notificacion_sivigila"], errors="coerce")
        df_filtrado = df_filtrado[
            (df_filtrado["_fecha_temp"] >= pd.Timestamp(filtro_fecha[0])) &
            (df_filtrado["_fecha_temp"] <= pd.Timestamp(filtro_fecha[1]))
        ]
        df_filtrado = df_filtrado.drop(columns=["_fecha_temp"], errors="ignore")

    # --- KPIs ---
    total_casos = len(df_filtrado)
    reincidentes = len(df_filtrado[df_filtrado["intento_previo"].str.upper() == "SI"])
    pct_reincidentes = (reincidentes / total_casos * 100) if total_casos > 0 else 0
    menores_18 = len(df_filtrado[df_filtrado["edad"] < 18])
    activos_sin_seg = len(df_filtrado[
        (df_filtrado["estado_caso"].str.upper() == "ACTIVO") &
        (df_filtrado["num_seguimientos_realizados"] == 0)
    ])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_casos}</div>
            <div class="kpi-label">Total Casos Registrados</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-value">{reincidentes} <small style="font-size:0.5em;">({pct_reincidentes:.1f}%)</small></div>
            <div class="kpi-label">🚨 Reincidentes (intento previo)</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card kpi-card-warning">
            <div class="kpi-value">{menores_18}</div>
            <div class="kpi-label">⚠️ Menores de 18 años</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-value">{activos_sin_seg}</div>
            <div class="kpi-label">🚨 Activos sin seguimiento</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Gráficas ---
    tab1, tab2, tab3 = st.tabs(["📊 Distribución", "📈 Tendencias", "🚨 Alertas"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Casos por municipio
            if not df_filtrado.empty:
                df_mun = df_filtrado["municipio_residencia"].value_counts().reset_index()
                df_mun.columns = ["Municipio", "Casos"]
                df_mun["Porcentaje"] = (df_mun["Casos"] / df_mun["Casos"].sum() * 100).round(1)
                df_mun = df_mun.sort_values("Casos", ascending=True)
                fig_mun = px.bar(df_mun, x="Casos", y="Municipio", orientation="h",
                                 title="Casos por Municipio",
                                 color="Casos", color_continuous_scale="Reds",
                                 text="Casos", custom_data=["Porcentaje"])
                fig_mun.update_traces(textposition="outside",
                                      hovertemplate="<b>%{y}</b><br>Casos: %{x}<br>Porcentaje: %{customdata[0]}%<extra></extra>")
                fig_mun.update_layout(height=max(400, len(df_mun) * 28), showlegend=False,
                                      coloraxis_showscale=False)
                st.plotly_chart(fig_mun, use_container_width=True)

        with col2:
            # Casos por EPS
            if not df_filtrado.empty:
                df_eps = df_filtrado["eps_reporta"].value_counts().reset_index()
                df_eps.columns = ["EPS", "Casos"]
                df_eps["Porcentaje"] = (df_eps["Casos"] / df_eps["Casos"].sum() * 100).round(1)
                fig_eps = px.bar(df_eps, x="EPS", y="Casos",
                                 title="Casos por EPS",
                                 color="Casos", color_continuous_scale="Blues",
                                 text="Casos", custom_data=["Porcentaje"])
                fig_eps.update_traces(textposition="outside",
                                      hovertemplate="<b>%{x}</b><br>Casos: %{y}<br>Porcentaje: %{customdata[0]}%<extra></extra>")
                fig_eps.update_layout(xaxis_tickangle=-45, height=400, showlegend=False,
                                      coloraxis_showscale=False)
                st.plotly_chart(fig_eps, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Distribución por curso de vida
            if not df_filtrado.empty:
                df_ciclo = df_filtrado["ciclo_vital"].value_counts().reset_index()
                df_ciclo.columns = ["Curso de Vida", "Casos"]
                fig_ciclo = px.pie(df_ciclo, values="Casos", names="Curso de Vida",
                                   title="Distribución por Curso de Vida",
                                   color_discrete_sequence=["#0D2137", "#1B3A5C", "#2E6B9E", "#4A90C4", "#7FB3D8", "#B5D4E9"],
                                   hole=0.4)
                fig_ciclo.update_traces(textinfo="percent+value")
                st.plotly_chart(fig_ciclo, use_container_width=True)

        with col2:
            # Distribución por sexo
            if not df_filtrado.empty:
                df_sexo = df_filtrado["sexo"].value_counts().reset_index()
                df_sexo.columns = ["Sexo", "Casos"]
                fig_sexo = px.pie(df_sexo, values="Casos", names="Sexo",
                                  title="Distribución por Sexo",
                                  color_discrete_sequence=["#D32F2F", "#1565C0", "#9E9E9E"],
                                  hole=0.4)
                fig_sexo.update_traces(textinfo="percent+value")
                st.plotly_chart(fig_sexo, use_container_width=True)

    with tab2:
        # Tendencia por semana epidemiológica
        if not df_filtrado.empty:
            df_sem = df_filtrado.groupby("semana_epidemiologica").size().reset_index(name="Casos")
            df_sem = df_sem.sort_values("semana_epidemiologica")
            fig_sem = px.line(df_sem, x="semana_epidemiologica", y="Casos",
                              title="Tendencia de Casos por Semana Epidemiológica",
                              markers=True, text="Casos")
            fig_sem.update_traces(textposition="top center",
                                  line_color=COLOR_AZUL_OSCURO, marker_color=COLOR_ROJO_ALERTA)
            fig_sem.update_layout(xaxis_title="Semana Epidemiológica", yaxis_title="Número de Casos")
            st.plotly_chart(fig_sem, use_container_width=True)

        # Casos por estado
        if not df_filtrado.empty:
            df_estado = df_filtrado["estado_caso"].value_counts().reset_index()
            df_estado.columns = ["Estado", "Casos"]
            df_estado["Porcentaje"] = (df_estado["Casos"] / df_estado["Casos"].sum() * 100).round(1)
            fig_estado = px.bar(df_estado, x="Estado", y="Casos",
                                title="Distribución por Estado del Caso",
                                color="Estado",
                                text="Casos", custom_data=["Porcentaje"],
                                color_discrete_map={
                                    "ACTIVO": "#F9A825",
                                    "CERRADO": "#4CAF50",
                                    "EN SEGUIMIENTO": "#2196F3",
                                    "FALLECIDO": "#D32F2F",
                                    "SIN CONTACTO": "#9E9E9E",
                                    "REMITIDO A OTRA EPS": "#FF9800"
                                })
            fig_estado.update_traces(textposition="outside",
                                     hovertemplate="<b>%{x}</b><br>Casos: %{y}<br>Porcentaje: %{customdata[0]}%<extra></extra>")
            fig_estado.update_layout(showlegend=False)
            st.plotly_chart(fig_estado, use_container_width=True)

    with tab3:
        # --- Tabla: Alerta Roja - Reincidentes ---
        st.markdown("""
        <div class="alerta-roja">
            <strong>🚨 ALERTA ROJA — Pacientes con intento previo (Reincidentes)</strong>
        </div>
        """, unsafe_allow_html=True)
        df_reincidentes = df_filtrado[df_filtrado["intento_previo"].str.upper() == "SI"]
        if not df_reincidentes.empty:
            cols_alerta = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                           "edad", "eps_reporta", "fecha_notificacion_sivigila", "estado_caso"]
            cols_disp = [c for c in cols_alerta if c in df_reincidentes.columns]
            st.dataframe(df_reincidentes[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron pacientes reincidentes con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Tabla: Alerta Amarilla - Sin seguimiento ---
        st.markdown("""
        <div class="alerta-amarilla">
            <strong>⚠️ ALERTA AMARILLA — Pacientes activos sin seguimiento o sin contacto</strong>
        </div>
        """, unsafe_allow_html=True)
        df_sin_seg = df_filtrado[
            ((df_filtrado["estado_caso"].str.upper() == "ACTIVO") &
             (df_filtrado["num_seguimientos_realizados"] == 0)) |
            (df_filtrado["asiste_servicios"].str.upper().isin(["NO", "SIN CONTACTO"]))
        ]
        if not df_sin_seg.empty:
            cols_alerta2 = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                            "edad", "eps_reporta", "asiste_servicios", "num_seguimientos_realizados",
                            "estado_caso"]
            cols_disp2 = [c for c in cols_alerta2 if c in df_sin_seg.columns]
            st.dataframe(df_sin_seg[cols_disp2], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron pacientes sin seguimiento con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Tabla: Alerta - Abandonos ---
        st.markdown("""
        <div class="alerta-amarilla">
            <strong>⚠️ ALERTA — Pacientes que abandonaron tratamiento</strong>
        </div>
        """, unsafe_allow_html=True)
        df_abandono = df_filtrado[df_filtrado["abandono_tratamiento"].str.upper() == "SI"]
        if not df_abandono.empty:
            cols_alerta3 = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                            "edad", "eps_reporta", "estado_caso"]
            cols_disp3 = [c for c in cols_alerta3 if c in df_abandono.columns]
            st.dataframe(df_abandono[cols_disp3], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron pacientes que hayan abandonado tratamiento.")


# ============================================================
# MÓDULO 3: EDICIÓN Y ACTUALIZACIÓN DE CASOS
# ============================================================

def modulo_edicion(spreadsheet):
    """Módulo para buscar, ver y editar registros existentes."""
    st.markdown(f"""
    <div class="main-header">
        <h1>✏️ Editar / Actualizar Caso</h1>
        <p>Busque un registro y actualice la información de seguimiento</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=True)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay registros disponibles para editar.")
        return

    # --- Búsqueda ---
    st.markdown("#### 🔍 Buscar Registro")
    col1, col2 = st.columns([2, 2])
    with col1:
        busq_doc = st.text_input("Buscar por número de documento", key="edit_busq_doc")
    with col2:
        busq_nombre = st.text_input("Buscar por nombre o apellido", key="edit_busq_nombre")

    df_resultado = df.copy()
    if busq_doc:
        df_resultado = df_resultado[df_resultado["numero_documento"].astype(str).str.contains(busq_doc, na=False)]
    if busq_nombre:
        busq_upper = busq_nombre.upper()
        df_resultado = df_resultado[
            df_resultado["nombres"].astype(str).str.upper().str.contains(busq_upper, na=False) |
            df_resultado["apellidos"].astype(str).str.upper().str.contains(busq_upper, na=False)
        ]

    if df_resultado.empty:
        st.warning("No se encontraron registros con los criterios de búsqueda.")
        return

    # Mostrar tabla de resultados
    st.markdown(f"**{len(df_resultado)} registro(s) encontrado(s)**")
    cols_tabla = ["id", "nombres", "apellidos", "numero_documento", "eps_reporta",
                  "municipio_residencia", "edad", "estado_caso", "fecha_notificacion_sivigila"]
    cols_disp = [c for c in cols_tabla if c in df_resultado.columns]
    st.dataframe(df_resultado[cols_disp], use_container_width=True, hide_index=True)

    # Seleccionar registro para editar
    ids_disponibles = df_resultado["id"].tolist()
    if not ids_disponibles:
        return

    st.markdown("---")
    id_seleccionado = st.selectbox("Seleccione el ID del registro a editar:", options=ids_disponibles)

    if id_seleccionado:
        registro = df_resultado[df_resultado["id"] == id_seleccionado].iloc[0].to_dict()
        # Sufijo dinámico para que los widgets se reinicien al cambiar de paciente
        ks = f"_{id_seleccionado}"

        st.markdown(f"#### Editando: **{registro.get('nombres', '')} {registro.get('apellidos', '')}** "
                    f"(Doc: {registro.get('numero_documento', '')})")

        with st.form(f"formulario_edicion{ks}"):
            # ---- Identificación ----
            st.markdown("##### 🏷️ Identificación del Caso")
            col1, col2 = st.columns(2)
            with col1:
                eps_edit = st.selectbox("EPS/EAPB", options=EPS_LISTA,
                                        index=EPS_LISTA.index(registro.get("eps_reporta", ""))
                                        if registro.get("eps_reporta", "") in EPS_LISTA else 0)
                semana_edit = st.number_input("Semana epidemiológica", min_value=1, max_value=53,
                                              value=int(registro.get("semana_epidemiologica", 1) or 1))
            with col2:
                ciclo_edit = calcular_curso_vida(int(registro.get("edad", 0) or 0))
                st.text_input("Curso de vida (automático)", value=ciclo_edit, disabled=True, key=f"edit_ciclo{ks}")
                intento_edit = st.radio("¿Intento previo?",
                                        options=["NO", "SI"],
                                        index=0 if registro.get("intento_previo", "NO") != "SI" else 1,
                                        horizontal=True, key=f"edit_intento{ks}")

            # ---- Datos Paciente ----
            st.markdown("##### 👤 Datos del Paciente")
            col1, col2 = st.columns(2)
            with col1:
                nombres_edit = st.text_input("Nombres", value=registro.get("nombres", ""), key=f"edit_nombres{ks}")
                tipo_doc_edit = st.selectbox("Tipo documento", options=TIPOS_DOCUMENTO,
                                             index=TIPOS_DOCUMENTO.index(registro.get("tipo_documento", "CC"))
                                             if registro.get("tipo_documento", "") in TIPOS_DOCUMENTO else 0)
                edad_edit = st.number_input("Edad", min_value=0, max_value=120,
                                            value=int(registro.get("edad", 0) or 0), key=f"edit_edad{ks}")
            with col2:
                apellidos_edit = st.text_input("Apellidos", value=registro.get("apellidos", ""), key=f"edit_apellidos{ks}")
                num_doc_edit = st.text_input("Número de documento",
                                             value=str(registro.get("numero_documento", "")), key=f"edit_numdoc{ks}")
                sexo_edit = st.selectbox("Sexo", options=["Masculino", "Femenino", "Indeterminado"],
                                         index=["Masculino", "Femenino", "Indeterminado"].index(
                                             registro.get("sexo", "Masculino"))
                                         if registro.get("sexo", "") in ["Masculino", "Femenino", "Indeterminado"]
                                         else 0, key=f"edit_sexo{ks}")

            municipio_edit = st.selectbox("Municipio de residencia", options=[""] + MUNICIPIOS_VALLE,
                                          index=(MUNICIPIOS_VALLE.index(registro.get("municipio_residencia", "")) + 1)
                                          if registro.get("municipio_residencia", "") in MUNICIPIOS_VALLE else 0,
                                          key=f"edit_mun{ks}")

            # ---- Notificación ----
            st.markdown("##### 📋 Notificación y Atención")
            col1, col2 = st.columns(2)
            with col1:
                def parse_date_safe(val):
                    try:
                        if val and str(val).strip() and str(val).strip() != "None":
                            return pd.to_datetime(val).date()
                    except:
                        pass
                    return None

                fecha_notif_edit = st.date_input("Fecha notificación SIVIGILA",
                                                  value=parse_date_safe(registro.get("fecha_notificacion_sivigila")),
                                                  key=f"edit_fecha_notif{ks}")
                hosp_opts = ["NO", "SI", "NO APLICA"]
                hosp_edit = st.selectbox("Hospitalización", options=hosp_opts,
                                         index=hosp_opts.index(registro.get("hospitalizacion", "NO"))
                                         if registro.get("hospitalizacion", "") in hosp_opts else 0,
                                         key=f"edit_hosp{ks}")
            with col2:
                fecha_med_edit = st.date_input("Fecha atención medicina general",
                                               value=parse_date_safe(registro.get("fecha_atencion_medicina")),
                                               key=f"edit_fecha_med{ks}")
                fecha_alta_edit = st.date_input("Fecha de alta",
                                                value=parse_date_safe(registro.get("fecha_alta")),
                                                key=f"edit_fecha_alta{ks}")

            # ---- Salud Mental ----
            st.markdown("##### 🧠 Atención en Salud Mental")
            col1, col2 = st.columns(2)
            sino_na = ["NO", "SI", "NO APLICA"]
            with col1:
                val_psic_edit = st.selectbox("Valoración Psicología", options=sino_na,
                                             index=sino_na.index(registro.get("valoracion_psicologia", "NO"))
                                             if registro.get("valoracion_psicologia", "") in sino_na else 0,
                                             key=f"edit_val_psic{ks}")
                fecha_psic_edit = st.date_input("Fecha Psicología",
                                                value=parse_date_safe(registro.get("fecha_psicologia")),
                                                key=f"edit_fecha_psic{ks}")
            with col2:
                val_psiq_edit = st.selectbox("Valoración Psiquiatría", options=sino_na,
                                             index=sino_na.index(registro.get("valoracion_psiquiatria", "NO"))
                                             if registro.get("valoracion_psiquiatria", "") in sino_na else 0,
                                             key=f"edit_val_psiq{ks}")
                fecha_psiq_edit = st.date_input("Fecha Psiquiatría",
                                                value=parse_date_safe(registro.get("fecha_psiquiatria")),
                                                key=f"edit_fecha_psiq{ks}")

            # ---- Seguimientos ----
            st.markdown("##### 📞 Seguimientos")
            seg1_edit = st.text_input("Seguimiento 1", value=str(registro.get("seguimiento_1", "")),
                                      key=f"edit_seg1{ks}")
            seg2_edit = st.text_input("Seguimiento 2", value=str(registro.get("seguimiento_2", "")),
                                      key=f"edit_seg2{ks}")
            seg3_edit = st.text_input("Seguimiento 3", value=str(registro.get("seguimiento_3", "")),
                                      key=f"edit_seg3{ks}")

            # ---- Estado ----
            st.markdown("##### 📊 Estado y Seguimiento Post-Alta")
            col1, col2 = st.columns(2)
            ruta_opts = ["SI", "NO", "EN PROCESO"]
            asiste_opts = ["SI", "NO", "SIN CONTACTO"]
            seg7_opts = ["NO APLICA", "SI", "NO"]
            abandono_opts = ["NO", "SI", "SIN INFORMACIÓN"]
            reintento_opts = ["NO", "SI", "SIN INFORMACIÓN"]

            with col1:
                ruta_edit = st.selectbox("¿En ruta de salud mental?", options=ruta_opts,
                                         index=ruta_opts.index(registro.get("ruta_salud_mental", "SI"))
                                         if registro.get("ruta_salud_mental", "") in ruta_opts else 0,
                                         key=f"edit_ruta{ks}")
                asiste_edit = st.selectbox("¿Asiste a servicios?", options=asiste_opts,
                                           index=asiste_opts.index(registro.get("asiste_servicios", "SI"))
                                           if registro.get("asiste_servicios", "") in asiste_opts else 0,
                                           key=f"edit_asiste{ks}")
                seg7_edit = st.selectbox("Seguimiento ≤7 días post alta", options=seg7_opts,
                                         index=seg7_opts.index(registro.get("seguimiento_7dias_postalta", "NO APLICA"))
                                         if registro.get("seguimiento_7dias_postalta", "") in seg7_opts else 0,
                                         key=f"edit_seg7{ks}")
            with col2:
                fecha_segpost_edit = st.date_input("Fecha seguimiento post-alta",
                                                    value=parse_date_safe(
                                                        registro.get("fecha_seguimiento_postalta")),
                                                    key=f"edit_fecha_segpost{ks}")
                num_seg_edit = st.number_input("Nº seguimientos realizados", min_value=0, max_value=50,
                                               value=int(registro.get("num_seguimientos_realizados", 0) or 0),
                                               key=f"edit_num_seg{ks}")
                abandono_edit = st.selectbox("¿Abandonó tratamiento?", options=abandono_opts,
                                             index=abandono_opts.index(registro.get("abandono_tratamiento", "NO"))
                                             if registro.get("abandono_tratamiento", "") in abandono_opts else 0,
                                             key=f"edit_abandono{ks}")

            col1, col2 = st.columns(2)
            with col1:
                reintento_edit = st.selectbox("¿Reintento posterior?", options=reintento_opts,
                                              index=reintento_opts.index(
                                                  registro.get("reintento_posterior", "NO"))
                                              if registro.get("reintento_posterior", "") in reintento_opts else 0,
                                              key=f"edit_reintento{ks}")
            with col2:
                estado_edit = st.selectbox("Estado del caso", options=ESTADOS_CASO,
                                           index=ESTADOS_CASO.index(registro.get("estado_caso", "ACTIVO"))
                                           if registro.get("estado_caso", "") in ESTADOS_CASO else 0,
                                           key=f"edit_estado{ks}")

            # ---- Observaciones ----
            st.markdown("##### 📝 Observaciones")
            obs_edit = st.text_area("Observaciones", value=str(registro.get("observaciones", "")),
                                    height=120, key=f"edit_obs{ks}")

            # ---- Guardar ----
            submitted_edit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")

            if submitted_edit:
                datos_actualizados = {
                    "id": id_seleccionado,
                    "fecha_digitacion": registro.get("fecha_digitacion", ""),
                    "funcionario_reporta": registro.get("funcionario_reporta", ""),
                    "eps_reporta": eps_edit,
                    "semana_epidemiologica": str(semana_edit),
                    "ciclo_vital": calcular_curso_vida(edad_edit),
                    "intento_previo": intento_edit,
                    "nombres": nombres_edit.upper().strip(),
                    "apellidos": apellidos_edit.upper().strip(),
                    "tipo_documento": tipo_doc_edit,
                    "numero_documento": num_doc_edit.strip(),
                    "edad": str(edad_edit),
                    "sexo": sexo_edit,
                    "municipio_residencia": municipio_edit,
                    "fecha_notificacion_sivigila": str(fecha_notif_edit) if fecha_notif_edit else "",
                    "fecha_atencion_medicina": str(fecha_med_edit) if fecha_med_edit else "",
                    "hospitalizacion": hosp_edit,
                    "fecha_alta": str(fecha_alta_edit) if fecha_alta_edit else "",
                    "valoracion_psicologia": val_psic_edit,
                    "fecha_psicologia": str(fecha_psic_edit) if fecha_psic_edit else "",
                    "valoracion_psiquiatria": val_psiq_edit,
                    "fecha_psiquiatria": str(fecha_psiq_edit) if fecha_psiq_edit else "",
                    "seguimiento_1": seg1_edit,
                    "seguimiento_2": seg2_edit,
                    "seguimiento_3": seg3_edit,
                    "ruta_salud_mental": ruta_edit,
                    "asiste_servicios": asiste_edit,
                    "seguimiento_7dias_postalta": seg7_edit,
                    "fecha_seguimiento_postalta": str(fecha_segpost_edit) if fecha_segpost_edit else "",
                    "num_seguimientos_realizados": str(num_seg_edit),
                    "abandono_tratamiento": abandono_edit,
                    "reintento_posterior": reintento_edit,
                    "estado_caso": estado_edit,
                    "observaciones": obs_edit,
                }

                with st.spinner("Actualizando registro..."):
                    exito, msg = actualizar_registro(
                        spreadsheet, id_seleccionado, datos_actualizados,
                        st.session_state.get("nombre_completo", "")
                    )

                if exito:
                    st.success(f"✅ Registro actualizado exitosamente para "
                               f"**{nombres_edit.upper()} {apellidos_edit.upper()}**")
                else:
                    st.error(f"❌ Error al actualizar: {msg}")


# ============================================================
# MÓDULO 4: EXPORTACIÓN DE DATOS
# ============================================================

def modulo_exportacion(spreadsheet):
    """Módulo de exportación de datos a CSV y Excel."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📥 Exportación de Datos</h1>
        <p>Descargue los datos registrados en formato CSV o Excel</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=True)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay datos disponibles para exportar.")
        return

    st.markdown(f"**Total de registros disponibles para exportar: {len(df)}**")

    # --- Filtros opcionales ---
    with st.expander("🔽 Filtrar datos antes de exportar"):
        col1, col2 = st.columns(2)
        with col1:
            exp_eps = st.multiselect("Filtrar por EPS", options=sorted(df["eps_reporta"].unique().tolist()),
                                     key="exp_eps")
            exp_mun = st.multiselect("Filtrar por Municipio",
                                     options=sorted(df["municipio_residencia"].unique().tolist()),
                                     key="exp_mun")
        with col2:
            exp_ciclo = st.multiselect("Filtrar por Curso de vida",
                                       options=sorted(df["ciclo_vital"].unique().tolist()),
                                       key="exp_ciclo")
            exp_estado = st.multiselect("Filtrar por Estado",
                                        options=sorted(df["estado_caso"].unique().tolist()),
                                        key="exp_estado")

    df_export = df.copy()
    if exp_eps:
        df_export = df_export[df_export["eps_reporta"].isin(exp_eps)]
    if exp_mun:
        df_export = df_export[df_export["municipio_residencia"].isin(exp_mun)]
    if exp_ciclo:
        df_export = df_export[df_export["ciclo_vital"].isin(exp_ciclo)]
    if exp_estado:
        df_export = df_export[df_export["estado_caso"].isin(exp_estado)]

    st.markdown(f"**Registros a exportar (con filtros): {len(df_export)}**")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📄 Descargar CSV")
        csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_data,
            file_name=f"sivigila_356_valle_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 📊 Descargar Excel (.xlsx)")
        st.markdown("*Con hojas separadas por curso de vida*")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            # Hoja con todos los datos
            df_export.to_excel(writer, sheet_name="TODOS_LOS_DATOS", index=False)

            # Hojas separadas por curso de vida
            for ciclo in CURSOS_VIDA:
                df_ciclo = df_export[df_export["ciclo_vital"] == ciclo]
                if not df_ciclo.empty:
                    nombre_hoja = ciclo.split("(")[0].strip()[:31]  # Max 31 chars para nombre de hoja
                    df_ciclo.to_excel(writer, sheet_name=nombre_hoja, index=False)

        buffer.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=buffer,
            file_name=f"sivigila_356_valle_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Preview de los datos
    st.markdown("---")
    st.markdown("#### 👁️ Vista previa de los datos")
    st.dataframe(df_export, use_container_width=True, hide_index=True)


# ============================================================
# MÓDULO 5: GESTIÓN DE USUARIOS (solo SECRETARÍA)
# ============================================================

def modulo_gestion_usuarios(spreadsheet):
    """Gestión de usuarios del sistema (solo administrador)."""
    st.markdown(f"""
    <div class="main-header">
        <h1>⚙️ Gestión de Usuarios</h1>
        <p>Crear y administrar usuarios del sistema</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("rol") != "SECRETARIA":
        st.error("⛔ No tiene permisos para acceder a este módulo.")
        return

    # --- Usuarios actuales ---
    st.markdown("#### 👥 Usuarios registrados")
    try:
        hoja_usuarios = obtener_hoja_usuarios(spreadsheet)
        registros = hoja_usuarios.get_all_records()
        df_usuarios = pd.DataFrame(registros)
        if not df_usuarios.empty:
            # No mostrar el hash de la contraseña
            df_mostrar = df_usuarios[["usuario", "nombre_completo", "rol", "eps_asignada"]].copy()
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("No hay usuarios registrados.")
    except Exception as e:
        st.error(f"Error al cargar usuarios: {str(e)}")

    st.markdown("---")

    # --- Crear nuevo usuario ---
    st.markdown("#### ➕ Crear Nuevo Usuario")
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_usuario = st.text_input("Nombre de usuario *", placeholder="Ej: digitador.sura")
            nueva_password = st.text_input("Contraseña *", type="password")
            confirmar_password = st.text_input("Confirmar contraseña *", type="password")
        with col2:
            nuevo_nombre = st.text_input("Nombre completo *", placeholder="Ej: María García López")
            nuevo_rol = st.selectbox("Rol *", options=["EPS", "SECRETARIA"])
            nueva_eps = st.selectbox("EPS asignada (solo para rol EPS)",
                                     options=["N/A"] + [e for e in EPS_LISTA if e != "OTRA (especificar)"])

        crear = st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary")

        if crear:
            if not nuevo_usuario or not nueva_password or not nuevo_nombre:
                st.error("⚠️ Todos los campos marcados con * son obligatorios.")
            elif nueva_password != confirmar_password:
                st.error("⚠️ Las contraseñas no coinciden.")
            elif len(nueva_password) < 6:
                st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
            else:
                eps_asig = nueva_eps if nuevo_rol == "EPS" and nueva_eps != "N/A" else ""
                exito, msg = crear_usuario(spreadsheet, nuevo_usuario, nueva_password,
                                           nuevo_nombre, nuevo_rol, eps_asig)
                if exito:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ============================================================
# MÓDULO 6: CARGA MASIVA (solo SECRETARÍA)
# ============================================================

# Diccionario de códigos EAPB → nombre descriptivo
EAPB_MAP = {
    "EPS001": "ALIANSALUD", "EPSS01": "ALIANSALUD", "EPSSO1": "ALIANSALUD",
    "ESS208": "ANAS WAYUU EPSI", "EPSI04": "ANAS WAYUU EPSI",
    "ESSC62": "ASMET SALUD", "ESS062": "ASMET SALUD",
    "ESS182": "ASOCIACION INDIGENA DEL CAUCA", "EPSIC3": "ASOCIACION INDIGENA DEL CAUCA",
    "EPS103": "ASOCIACION INDIGENA DEL CAUCA", "EPSI03": "ASOCIACION INDIGENA DEL CAUCA",
    "CCF055": "CAJACOPI ATLANTICO",
    "EPSS34": "CAPITAL SALUD EPSS S.A.S.",
    "CCF102": "C.C.F. COMFACHOCO",
    "CCF050": "CONFAORIENTE", "CCFC50": "COMFAORIENTE",
    "EPS012": "COMFENALCO", "EPSS12": "COMFENALCO",
    "EPS008": "COMPENSAR E.P.S.", "EPSSO8": "COMPENSAR", "EPSS08": "COMPENSAR",
    "ESSC24": "COOSALUD", "ESS024": "COOSALUD", "EPSS42": "COOSALUD",
    "EPSI01": "DUSAKAWI EPSI", "EPS101": "DUSAKAWI EPSI", "EPSIC1": "DUSAKAWI EPSI",
    "ESS177": "DUSAKAWI EPSI",
    "ESSC18": "EMSSANAR", "ESS118": "EMSSANAR",
    "EPS017": "EPS FAMISANAR LTDA.", "EPSS17": "EPS FAMISANAR LTDA.",
    "EAS027": "FONDO PASIVO SOCIAL FERROCARRILES",
    "EPSI05": "MALLAMAS EPSI", "EPSIC5": "MALLAMAS EPSI",
    "ESS207": "MUTUAL SER", "EPSS48": "MUTUAL SER", "ESSCO7": "MUTUAL SER",
    "ESSC07": "MUTUAL SER",
    "EPS041": "NUEVA EPS", "EPSS41": "NUEVA EPS", "EPS037": "NUEVA EPS",
    "EPSS37": "NUEVA EPS", "EPS042": "NUEVA EPS",
    "EPSI06": "PIJAOS SALUD EPSI",
    "EPS047": "SALUD MIA", "EPSS46": "SALUD MIA",
    "EPSS02": "SALUD TOTAL", "EPS002": "SALUD TOTAL", "EPSSO2": "SALUD TOTAL",
    "EPS005": "SANITAS", "EPSS05": "SANITAS",
    "CCF002": "SAVIA SALUD", "EPSS40": "SAVIA SALUD", "EPS040": "SAVIA SALUD",
    "EPS018": "S.O.S.", "EPSS18": "S.O.S.",
    "EPS010": "SURA", "EPSS10": "SURA", "14-28": "SURA", "37209": "SURA",
    "13-18": "SURA", "EMP021": "SURA",
    "I": "INDETERMINADO", "N": "NO ASEGURADO",
    "EPS003": "CAFESALUD", "EPSS03": "CAFESALUD", "EPSM03": "CAFESALUD",
    "EPS016": "COOMEVA", "EPSS16": "COOMEVA",
    "EPS045": "MEDIMAS", "EPS044": "MEDIMAS", "EPSS44": "MEDIMAS", "EPSS45": "MEDIMAS",
    "EPS013": "SALUDCOOP", "EPSS13": "SALUDCOOP",
    "EPSC33": "SALUDVIDA", "EPSM33": "SALUDVIDA", "EPS033": "SALUDVIDA",
    "EPSS33": "SALUDVIDA", "EPS034": "SALUDVIDA",
    "REFM01": "FUERZAS MILITARES", "RES003": "FUERZAS MILITARES",
    "REPN01": "POLICIA NACIONAL", "RES001": "POLICIA NACIONAL",
    "REMG01": "MAGISTERIO",
    "ESS184": "RESGUARDO INDÍGENA",
    "EPSS47": "SALUD BOLÍVAR",
    "EPS023": "CRUZ BLANCA", "EPSS23": "CRUZ BLANCA",
    "EPS038": "MULTIMEDICAS",
    "ESSC91": "ECOOPSOS",
    "EPS022": "CONVIDA",
    "ESS133": "COMPARTA", "ESSC33": "COMPARTA",
    "EPSC20": "CAPRECOM",
    "EMP023": "COLSANITAS",
}

# Normalización de nombres EAPB → nombres exactos de EPS_LISTA del aplicativo
NORM_EPS = {
    "S.O.S.": "SOS (SERVICIO OCCIDENTAL DE SALUD)",
    "S.O.S": "SOS (SERVICIO OCCIDENTAL DE SALUD)",
    "EMMSANAR": "EMSSANAR",
    "COMPENSAR E.P.S.": "COMPENSAR",
    "EPS FAMISANAR LTDA.": "FAMISANAR",
    "CAPITAL SALUD EPSS S.A.S.": "CAPITAL SALUD",
    "C.C.F. COMFACHOCO": "COMFACHOCÓ",
    "CONFAORIENTE": "COMFAORIENTE",
    "COMFENALCO": "COMFENALCO VALLE",
    "SANITAS E.P.S. S.A.": "SANITAS",
    "EPS SANITAS - CM": "SANITAS",
    "ASOCIACION INDIGENA DEL CAUCA": "ASOCIACIÓN INDÍGENA DEL CAUCA EPSI",
    "MALLAMAS - EMPRESA PROMOTORA DE SALUD MALLAMAS EPS INDIGENA": "MALLAMAS EPSI",
    "ENTIDAD PROMOTORA DE SALUD MALLAMAS EPSI": "MALLAMAS EPSI",
    "PIJAOS SALUD EPS -I": "PIJAOS SALUD EPSI",
    "SALUD MIA": "SALUD MÍA",
    "SAVIA SALUD E.P.S.": "SAVIA SALUD",
    "SAVIA SALUD SUBSIDIADO": "SAVIA SALUD",
    "EPS SAVIA SALUD": "SAVIA SALUD",
    "CAJACOPI ATLANTICO": "CAJACOPI ATLÁNTICO",
    "CAJA DE DE COMPENSACION FAMILIAR CAJACOPI ATLANTICO": "CAJACOPI ATLÁNTICO",
    "FONDO DE PASIVO SOCIAL DE FERROCARRILES NACIONALES DE COLOMBIA.": "FONDO PASIVO SOCIAL FERROCARRILES",
    "ASOCIACIÓN DE CABILDOS INDÍGENAS DEL CESAR 'DUSAKAWI'": "DUSAKAWI EPSI",
    "ASOCIACION DE CABILDOS INDIGENAS DEL CESAR DUSAKAWI EPSI": "DUSAKAWI EPSI",
    "ASOCIACIÓN MUTUAL SER EMPRESA SOLIDARIA DE SALUD ESS": "MUTUAL SER",
}

# Etiquetas para convertir códigos numéricos de la base SAT
LBL_SI_NO = {1: "SI", 2: "NO"}
LBL_SEXO = {"M": "Masculino", "F": "Femenino", "I": "Indeterminado"}
LBL_PAC_HOS = {1: "SI", 2: "NO"}


def normalizar_eps(nombre_eapb):
    """Normaliza el nombre de EAPB al formato de EPS_LISTA del aplicativo."""
    if not nombre_eapb or str(nombre_eapb).strip() == "":
        return ""
    nombre = str(nombre_eapb).strip().upper()
    # Buscar en normalización
    for clave, valor in NORM_EPS.items():
        if clave.upper() == nombre:
            return valor
    # Si ya es un nombre válido de EPS_LISTA, devolverlo tal cual
    if nombre in [e.upper() for e in EPS_LISTA if e != "OTRA (especificar)"]:
        for e in EPS_LISTA:
            if e.upper() == nombre:
                return e
    # Devolver el original (quedará como EPS no estándar)
    return nombre_eapb.strip()


def detectar_tipo_base(df):
    """Detecta si es Base Completa o Base SAT."""
    if "caso_nuevo" in df.columns or "EAPB" in df.columns:
        return "COMPLETA"
    if "pac_hos_" in df.columns and "gp_otros" in df.columns:
        # Verificar si tiene códigos numéricos (SAT) o etiquetas (Completa)
        sample = df["gp_discapa"].dropna().head(5).tolist()
        if any(isinstance(v, (int, float)) for v in sample):
            return "SAT"
        if any(str(v).strip() in ["1", "2"] for v in sample):
            return "SAT"
    return "COMPLETA"


def transformar_base(df, tipo_base):
    """Transforma la base (Completa o SAT) al esquema de COLUMNAS_DATOS del aplicativo."""
    registros = []

    for _, row in df.iterrows():
        # --- EPS ---
        if tipo_base == "COMPLETA" and "EAPB" in df.columns:
            eps_raw = str(row.get("EAPB", "")).strip()
        else:
            cod = str(row.get("cod_ase_", "")).strip()
            eps_raw = EAPB_MAP.get(cod, cod)
        eps_final = normalizar_eps(eps_raw)

        # --- Nombres y apellidos ---
        pri_nom = str(row.get("pri_nom_", "")).strip().upper()
        seg_nom = str(row.get("seg_nom_", "")).strip().upper()
        nombres = f"{pri_nom} {seg_nom}".strip()

        pri_ape = str(row.get("pri_ape_", "")).strip().upper()
        seg_ape = str(row.get("seg_ape_", "")).strip().upper()
        apellidos = f"{pri_ape} {seg_ape}".strip()

        # --- Edad y curso de vida ---
        edad_raw = row.get("edad_", 0)
        try:
            edad = int(float(str(edad_raw).replace(":", "").strip()))
        except:
            edad = 0
        curso = calcular_curso_vida(edad)

        # --- Sexo ---
        sexo_raw = str(row.get("sexo_", "")).strip().upper()
        if tipo_base == "SAT":
            sexo = LBL_SEXO.get(sexo_raw, sexo_raw)
        else:
            if sexo_raw == "M":
                sexo = "Masculino"
            elif sexo_raw == "F":
                sexo = "Femenino"
            else:
                sexo = sexo_raw if sexo_raw in ["Masculino", "Femenino", "Indeterminado"] else "Indeterminado"

        # --- Intento previo ---
        ip_raw = row.get("inten_prev", "")
        if tipo_base == "SAT":
            try:
                ip_val = int(float(str(ip_raw).replace(":", "").strip()))
                intento = LBL_SI_NO.get(ip_val, "NO")
            except:
                intento = "NO"
        else:
            intento = "SI" if str(ip_raw).strip().upper() in ["SI", "SÍ", "1"] else "NO"

        # --- Hospitalización ---
        if tipo_base == "SAT" and "pac_hos_" in df.columns:
            try:
                ph = int(float(str(row.get("pac_hos_", "")).replace(":", "").strip()))
                hosp = LBL_PAC_HOS.get(ph, "NO APLICA")
            except:
                hosp = "NO APLICA"
        else:
            hosp = "NO APLICA"

        # --- Valoraciones psicología/psiquiatría ---
        def convertir_si_no(val, es_sat):
            if es_sat:
                try:
                    v = int(float(str(val).replace(":", "").strip()))
                    return LBL_SI_NO.get(v, "NO")
                except:
                    return "NO"
            else:
                return "SI" if str(val).strip().upper() in ["SI", "SÍ", "1"] else "NO"

        val_psic = convertir_si_no(row.get("psicologia", ""), tipo_base == "SAT")
        val_psiq = convertir_si_no(row.get("psiquiatri", ""), tipo_base == "SAT")

        # --- Municipio ---
        mun = str(row.get("nmun_resi", "")).strip().upper()

        # --- Fechas ---
        def fmt_fecha(val):
            if pd.isna(val) or str(val).strip() in ["", "None", "-   -", "NaT"]:
                return ""
            try:
                return pd.to_datetime(val, dayfirst=True, errors="coerce").strftime("%Y-%m-%d")
            except:
                return str(val).strip()

        fec_not = fmt_fecha(row.get("fec_not", ""))
        fec_con = fmt_fecha(row.get("fec_con_", ""))
        fec_hos = fmt_fecha(row.get("fec_hos_", ""))

        # --- Semana ---
        try:
            semana = int(float(str(row.get("semana", 0)).replace(":", "").strip()))
        except:
            semana = 0

        # --- Número de documento ---
        num_doc = str(row.get("num_ide_", "")).strip().replace(".0", "").split(".")[0]

        registro = {
            "id": generar_id(),
            "fecha_digitacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "funcionario_reporta": "CARGA MASIVA",
            "eps_reporta": eps_final,
            "semana_epidemiologica": str(semana),
            "ciclo_vital": curso,
            "intento_previo": intento,
            "nombres": nombres,
            "apellidos": apellidos,
            "tipo_documento": str(row.get("tip_ide_", "CC")).strip().upper(),
            "numero_documento": num_doc,
            "edad": str(edad),
            "sexo": sexo,
            "municipio_residencia": mun,
            "fecha_notificacion_sivigila": fec_not,
            "fecha_atencion_medicina": fec_con,
            "hospitalizacion": hosp,
            "fecha_alta": fec_hos if hosp == "SI" else "",
            "valoracion_psicologia": val_psic,
            "fecha_psicologia": "",
            "valoracion_psiquiatria": val_psiq,
            "fecha_psiquiatria": "",
            "seguimiento_1": "", "seguimiento_2": "", "seguimiento_3": "",
            "ruta_salud_mental": "EN PROCESO",
            "asiste_servicios": "SIN CONTACTO",
            "seguimiento_7dias_postalta": "NO APLICA",
            "fecha_seguimiento_postalta": "",
            "num_seguimientos_realizados": "0",
            "abandono_tratamiento": "SIN INFORMACIÓN",
            "reintento_posterior": "SIN INFORMACIÓN",
            "estado_caso": "ACTIVO",
            "observaciones": f"Carga masiva ({tipo_base}) - {datetime.now().strftime('%Y-%m-%d')}",
            "ultima_modificacion_por": st.session_state.get("nombre_completo", ""),
            "ultima_modificacion_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        registros.append(registro)
        # Pequeña pausa para IDs únicos
        time.sleep(0.001)

    return pd.DataFrame(registros)


def modulo_carga_masiva(spreadsheet):
    """Módulo para carga masiva de bases SIVIGILA (Completa o SAT)."""
    st.markdown("""
    <div class="main-header">
        <h1>📤 Carga Masiva de Casos</h1>
        <p>Importe bases del SIVIGILA (Completa o SAT) al sistema de seguimiento</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("rol") != "SECRETARIA":
        st.error("⛔ Solo el rol SECRETARÍA puede realizar cargas masivas.")
        return

    st.markdown("""
    **Instrucciones:**
    - Suba un archivo Excel (.xlsx/.xls) o CSV con la base de datos del SIVIGILA Evento 356.
    - El sistema detecta automáticamente si es **Base Completa** (con etiquetas y columna EAPB) o **Base SAT** (códigos numéricos).
    - Se verifican duplicados contra los registros existentes usando **número de documento + fecha de notificación**.
    - Solo se insertan los registros nuevos.
    """)

    archivo = st.file_uploader("Seleccione el archivo", type=["xlsx", "xls", "csv"],
                                key="carga_masiva_file")

    if archivo is None:
        return

    # --- Leer archivo ---
    try:
        if archivo.name.endswith(".csv"):
            df_raw = pd.read_csv(archivo, encoding="utf-8-sig")
        else:
            df_raw = pd.read_excel(archivo)
        st.success(f"✅ Archivo leído: **{len(df_raw)}** registros, **{len(df_raw.columns)}** columnas.")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        return

    # --- Detectar tipo ---
    tipo = detectar_tipo_base(df_raw)
    st.info(f"📋 Tipo de base detectado: **{tipo}**")

    if df_raw.empty:
        st.warning("No hay registros para procesar.")
        return

    # --- Transformar ---
    with st.spinner("Transformando datos al esquema del aplicativo..."):
        df_transformado = transformar_base(df_raw, tipo)

    st.success(f"✅ **{len(df_transformado)}** registros transformados.")

    # --- Cargar datos existentes y detectar duplicados ---
    with st.spinner("Verificando duplicados contra la base existente..."):
        df_existente = cargar_datos(spreadsheet, forzar=True)

    if not df_existente.empty:
        # Llave: numero_documento + fecha_notificacion_sivigila
        df_existente["_llave_dup"] = (
            df_existente["numero_documento"].astype(str).str.strip() + "_" +
            df_existente["fecha_notificacion_sivigila"].astype(str).str.strip()
        )
        df_transformado["_llave_dup"] = (
            df_transformado["numero_documento"].astype(str).str.strip() + "_" +
            df_transformado["fecha_notificacion_sivigila"].astype(str).str.strip()
        )

        llaves_existentes = set(df_existente["_llave_dup"].tolist())
        mascara_nuevos = ~df_transformado["_llave_dup"].isin(llaves_existentes)

        n_duplicados = (~mascara_nuevos).sum()
        df_nuevos = df_transformado[mascara_nuevos].drop(columns=["_llave_dup"])
    else:
        n_duplicados = 0
        df_nuevos = df_transformado.drop(columns=["_llave_dup"], errors="ignore")

    # --- Resumen ---
    st.markdown("---")
    st.markdown("### 📊 Resumen de la carga")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Registros en el archivo", len(df_raw))
    with col2:
        st.metric("Duplicados descartados", n_duplicados)
    with col3:
        st.metric("Registros nuevos a insertar", len(df_nuevos))

    if df_nuevos.empty:
        st.warning("⚠️ Todos los registros ya existen en la base de datos. No hay nada nuevo que insertar.")
        return

    # Vista previa
    with st.expander("👁️ Vista previa de registros nuevos"):
        cols_preview = ["nombres", "apellidos", "numero_documento", "eps_reporta",
                        "municipio_residencia", "edad", "sexo", "intento_previo",
                        "fecha_notificacion_sivigila"]
        cols_disp = [c for c in cols_preview if c in df_nuevos.columns]
        st.dataframe(df_nuevos[cols_disp], use_container_width=True, hide_index=True)

    # --- Confirmación e inserción ---
    st.markdown("---")
    confirmar = st.button(f"✅ Confirmar e insertar {len(df_nuevos)} registros",
                          type="primary", use_container_width=True)

    if confirmar:
        hoja = obtener_hoja_datos(spreadsheet)
        progreso = st.progress(0)
        estado = st.empty()

        # Preparar todas las filas
        todas_filas = []
        for _, row in df_nuevos.iterrows():
            fila = [str(row.get(col, "")) for col in COLUMNAS_DATOS]
            todas_filas.append(fila)

        # Insertar en lotes de 50 para no exceder cuota de API
        TAMANO_LOTE = 50
        errores = 0
        insertados = 0

        for i in range(0, len(todas_filas), TAMANO_LOTE):
            lote = todas_filas[i:i + TAMANO_LOTE]
            try:
                hoja.append_rows(lote, value_input_option="USER_ENTERED", table_range="A1")
                insertados += len(lote)
            except Exception as e:
                errores += len(lote)
                st.warning(f"Error en lote {i//TAMANO_LOTE + 1}: {e}")
                # Esperar más tiempo si hay error de cuota
                time.sleep(30)
                try:
                    hoja.append_rows(lote, value_input_option="USER_ENTERED", table_range="A1")
                    insertados += len(lote)
                    errores -= len(lote)
                except:
                    pass

            progreso.progress(min((i + len(lote)) / len(todas_filas), 1.0))
            estado.text(f"Insertando lote {i//TAMANO_LOTE + 1} de {(len(todas_filas)-1)//TAMANO_LOTE + 1}...")
            time.sleep(2)

        progreso.empty()
        estado.empty()

        # Invalidar caché
        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        if errores == 0:
            st.success(f"🎉 **{insertados}** registros insertados exitosamente.")
            st.balloons()
        else:
            st.warning(f"⚠️ Insertados {insertados} registros. {errores} con errores.")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    """Función principal que controla el flujo del aplicativo."""

    # Verificar autenticación
    if not st.session_state.get("autenticado", False):
        mostrar_login()
        return

    # Conectar a Google Sheets
    spreadsheet = obtener_conexion_gsheets()
    if not spreadsheet:
        st.error("No se pudo conectar a Google Sheets. Verifique la configuración.")
        return

    # Sidebar y navegación
    pagina = mostrar_sidebar()

    # Enrutar a la página correspondiente
    if pagina == "📊 Tablero de Control":
        modulo_dashboard(spreadsheet)
    elif pagina == "📝 Registrar Nuevo Caso":
        modulo_formulario(spreadsheet)
    elif pagina == "✏️ Editar / Actualizar Caso":
        modulo_edicion(spreadsheet)
    elif pagina == "📥 Exportar Datos":
        modulo_exportacion(spreadsheet)
    elif pagina == "📤 Carga Masiva":
        modulo_carga_masiva(spreadsheet)
    elif pagina == "⚙️ Gestionar Usuarios":
        modulo_gestion_usuarios(spreadsheet)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()
