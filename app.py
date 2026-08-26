# -*- coding: utf-8 -*--
import os
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import streamlit as st
from io import BytesIO

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO CORPORATIVO
# ==========================================
st.set_page_config(
    page_title="DC Control - Sistema de Trazabilidad y Gobierno Corporativo",
    layout="wide",
    page_icon="🏗️"
)

# Estilo general minimalista y corporativo para DC Control (Componentes 100% nativos)
st.markdown("""
<style>
    /* Estilo del encabezado principal */
    .main-header {
        background-color: #111827;
        color: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        border-left: 8px solid #00C875;
    }
    .main-title {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
    }
    .main-subtitle {
        color: #9ca3af;
        font-size: 14px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONSTANTES Y CONFIGURACIÓN
# ==========================================
DB_FILE = "pipeline_cotizaciones.db"

ESTADOS_MEXICO = {
    "CDMX": "Líder Regional - Sur",
    "Estado de México": "Líder Regional - Sur",
    "Querétaro": "Líder Regional - Sur",
    "Guanajuato": "Líder Regional - Sur",
    "Jalisco": "Líder Regional - Sur",
    "Michoacán": "Líder Regional - Sur",
    "Puebla": "Líder Regional - Sur",
    "Veracruz": "Líder Regional - Sur",
    "Hidalgo": "Líder Regional - Sur",
    "Morelos": "Líder Regional - Sur",
    "Guerrero": "Líder Regional - Sur",
    "Oaxaca": "Líder Regional - Sur",
    "Chiapas": "Líder Regional - Sur",
    "Tabasco": "Líder Regional - Sur",
    "Campeche": "Líder Regional - Sur",
    "Yucatán": "Líder Regional - Sur",
    "Quintana Roo": "Líder Regional - Sur",
    "Tlaxcala": "Líder Regional - Sur",
    "Colima": "Líder Regional - Sur",
    "Nayarit": "Líder Regional - Sur",
    "Nuevo León": "Líder Regional - Norte",
    "Chihuahua": "Líder Regional - Norte",
    "Coahuila": "Líder Regional - Norte",
    "Sonora": "Líder Regional - Norte",
    "Baja California": "Líder Regional - Norte",
    "Baja California Sur": "Líder Regional - Norte",
    "San Luis Potosí": "Líder Regional - Norte",
    "Aguascalientes": "Líder Regional - Norte",
    "Durango": "Líder Regional - Norte",
    "Sinaloa": "Líder Regional - Norte",
    "Zacatecas": "Líder Regional - Norte",
    "Tamaulipas": "Líder Regional - Norte"
}

EMAIL_MAP = {
    "Ventas": "ventas@dccontrol.com",
    "Líder Regional - Sur": "lider.sur@dccontrol.com",
    "Líder Regional - Norte": "lider.norte@dccontrol.com",
    "Analista de Costos Jefe": "costos.jefe@dccontrol.com",
    "Analista de Costos Junior 1": "costos.jr1@dccontrol.com",
    "Analista de Costos Junior 2": "costos.jr2@dccontrol.com",
    "Ingeniero": "ingenieria@dccontrol.com",
    "Admin/Director": "director@dccontrol.com"
}

# ==========================================
# FUNCIONES DE BASE DE DATOS
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(insert_demos=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Configuración General
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # 2. Tabla de Proyectos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            client TEXT,
            total_amount REAL,
            state TEXT,
            zone TEXT,
            assigned_lider TEXT,
            assigned_costos TEXT,
            status TEXT,
            current_stage INTEGER DEFAULT 1,
            lose_percentage_gap REAL DEFAULT 0.0,
            director_review_required INTEGER DEFAULT 0,
            created_at TEXT,
            target_date TEXT
        )
    ''')
    
    # 3. Tabla de Tareas (Compuertas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            stage INTEGER,
            title TEXT,
            assigned_role TEXT,
            is_completed INTEGER DEFAULT 0,
            completed_by TEXT,
            completed_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    
    # 4. Tabla de Auditoría (Audit Trail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            user_name TEXT,
            role TEXT,
            action TEXT,
            timestamp TEXT
        )
    ''')
    
    # 5. Tabla de Usuarios (Con columna de email individual)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            full_name TEXT,
            role TEXT,
            email TEXT
        )
    ''')
    
    # --- PROCESO DE MIGRACIÓN AUTÓNOMA (Auto-Healing) ---
    def get_columns(table_name):
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
        
    try:
        proj_cols = get_columns('projects')
        if 'director_review_required' not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN director_review_required INTEGER DEFAULT 0")
        if 'target_date' not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN target_date TEXT")
        if 'lose_percentage_gap' not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN lose_percentage_gap REAL DEFAULT 0.0")
            
        task_cols = get_columns('tasks')
        if 'stage' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN stage INTEGER DEFAULT 1")
        if 'completed_by' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN completed_by TEXT")
        if 'completed_at' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
            
        user_cols = get_columns('users')
        if 'email' not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except Exception as e:
        pass
        
    # Inicialización del estatus en system_settings
    cursor.execute("SELECT COUNT(*) FROM system_settings WHERE key = 'initialized'")
    is_initialized = cursor.fetchone()[0] > 0
    
    # Inicialización de Usuarios (Siempre deben existir para el Login)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        demo_users = [
            ("admin", "admin123", "Director General", "Admin/Director", "director@dccontrol.com"),
            ("ventas1", "ventas123", "Ing. Carlos (Ventas)", "Ventas", "ventas@dccontrol.com"),
            ("lider_sur", "sur123", "Ing. Sofía (Líder Regional Sur)", "Líder Regional - Sur", "lider.sur@dccontrol.com"),
            ("lider_norte", "norte123", "Ing. Alejandro (Líder Regional Norte)", "Líder Regional - Norte", "lider.norte@dccontrol.com"),
            ("costos_jefe", "jefe123", "Lic. Roberto (Director de Costos)", "Analista de Costos Jefe", "costos.jefe@dccontrol.com"),
            ("costos_jr1", "jr1123", "Ing. Manuel (Analista Jr 1)", "Analista de Costos Junior 1", "costos.jr1@dccontrol.com"),
            ("costos_jr2", "jr2123", "Ing. Gabriel (Analista Jr 2)", "Analista de Costos Junior 2", "costos.jr2@dccontrol.com")
        ]
        cursor.executemany("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)", demo_users)
        
    # Cargar proyectos de demostración SOLO en la primera instalación y si insert_demos es True
    if not is_initialized and insert_demos:
        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            demo_projects = [
                ("PRJ-101", "Ampliación Planta Monterrey", "Aceros de Monterrey S.A.", 1250000.0, "Nuevo León", "Norte", "Líder Regional - Norte", "Analista de Costos Jefe", "En Proceso", 3, 0.0, 1, "2026-08-01", "2026-09-15"),
                ("PRJ-102", "Instalación Eléctrica Querétaro", "Logística del Centro", 450000.0, "Querétaro", "Sur", "Líder Regional - Sur", "Analista de Costos Junior 1", "Ganado", 5, 0.0, 0, "2026-08-05", "2026-10-10"),
                ("PRJ-103", "Mantenimiento Preventivo Chiapas", "Cervecería del Sur", 850000.0, "Chiapas", "Sur", "Líder Regional - Sur", "Analista de Costos Junior 2", "Perdido", 5, 15.0, 0, "2026-08-10", "2026-09-01"),
                ("PRJ-104", "Subestación Baja California", "Energía del Norte", 3200000.0, "Baja California", "Norte", "Líder Regional - Norte", "Analista de Costos Jefe", "En Proceso", 2, 0.0, 1, "2026-08-20", "2026-11-30")
            ]
            cursor.executemany("INSERT OR REPLACE INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", demo_projects)
            
            demo_tasks = [
                (None, "PRJ-101", 1, "Registrar ficha técnica y alcance inicial", "Ventas", 1, "Ing. Carlos (Ventas)", "2026-08-02 10:00:00"),
                (None, "PRJ-101", 2, "Realizar reunión de alineación y minuta", "Líder Regional - Norte", 1, "Ing. Alejandro (Líder Regional Norte)", "2026-08-05 15:30:00"),
                (None, "PRJ-101", 3, "Generar catálogo de conceptos técnico", "Ingeniero", 0, None, None),
                (None, "PRJ-101", 3, "Elaborar análisis de precios unitarios", "Analista de Costos Jefe", 0, None, None),
                (None, "PRJ-101", 4, "Revisión técnica de dossier de obra", "Líder Regional - Norte", 0, None, None),
                (None, "PRJ-101", 5, "Firma de aprobación final y envío", "Admin/Director", 0, None, None),
                
                (None, "PRJ-102", 1, "Registrar ficha técnica y alcance inicial", "Ventas", 1, "Ing. Carlos (Ventas)", "2026-08-06 09:12:00"),
                (None, "PRJ-102", 2, "Realizar reunión de alineación y minuta", "Líder Regional - Sur", 1, "Ing. Sofía (Líder Regional Sur)", "2026-08-07 14:00:00"),
                (None, "PRJ-102", 3, "Generar catálogo de conceptos técnico", "Ingeniero", 1, "Ingeniero Mendoza", "2026-08-15 11:45:00"),
                (None, "PRJ-102", 4, "Revisión técnica de dossier de obra", "Líder Regional - Sur", 1, "Ing. Sofía (Líder Regional Sur)", "2026-08-18 16:30:00"),
                (None, "PRJ-102", 5, "Firma de aprobación final y envío", "Admin/Director", 1, "Director General", "2026-08-20 18:00:00"),
            ]
            cursor.executemany("INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", demo_tasks)
            
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('initialized', '1')")
        
    conn.commit()
    conn.close()

# Inicialización al vuelo del sistema
init_db(insert_demos=True)

# ==========================================
# FUNCIONES AUXILIARES DE GOBIERNO
# ==========================================
def log_audit(project_id, user_name, role, action):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO audit_log (project_id, user_name, role, action, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, user_name, role, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_email_for_role(role_name):
    """Consulta el correo electrónico real configurado en la base de datos para un puesto."""
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT email FROM users WHERE role = ? LIMIT 1", (role_name,)).fetchone()
        conn.close()
        if row and row['email']:
            return row['email']
    except Exception:
        pass
    # Respaldo si no hay un usuario registrado con ese rol
    return EMAIL_MAP.get(role_name, "soporte@dccontrol.com")

def enviar_correo_alerta(destinatario, rol_dest, asunto, proyecto_nombre, tarea_desc):
    st.toast(f"📧 Correo simulado enviado a: {destinatario} ({rol_dest})", icon="📨")
    st.info(f"**Correo enviado a {rol_dest} ({destinatario}):** {asunto} - Tarea: *{tarea_desc}* para el proyecto *{proyecto_nombre}*")

# ==========================================
# INICIO DE SESIÓN Y LOGIN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.full_name = ""

def logout():
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.full_name = ""
    st.rerun()

# --- Interfaz de Autenticación Mínima y Limpia ---
if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; margin-top: 50px;'>
        <h1 style='color: #1f2937;'>🏗️ DC Control</h1>
        <h3 style='color: #4b5563;'>Sistema de Trazabilidad y Gobierno Corporativo</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        with st.container(border=True):
            st.write("### 🔐 Acceso al Sistema")
            username_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            btn_login = st.button("Ingresar 🚀", use_container_width=True)
            
            if btn_login:
                conn = get_db_connection()
                user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username_input, password_input)).fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user['username']
                    st.session_state.user_role = user['role']
                    st.session_state.full_name = user['full_name']
                    st.success("¡Acceso autorizado!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.markdown(f"### 👤 {st.session_state.full_name}")
st.sidebar.markdown(f"**Puesto / Rol:** {st.session_state.user_role}")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout()

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **DC Control Workspace**\n\n"
    "Portal ejecutivo centralizado para el monitoreo, asignación y auditoría de licitaciones y proyectos."
)

# ==========================================
# CABECERA PRINCIPAL EN PANTALLA
# ==========================================
st.markdown(f"""
<div class="main-header">
    <div class="main-title">🏗️ DC Control Workspace</div>
    <div class="main-subtitle">Control de Trazabilidad y Gobierno de Proyectos • Rol activo: {st.session_state.user_role}</div>
</div>
""", unsafe_allow_html=True)

# Definir pestañas de control según el Rol
role = st.session_state.user_role
tabs_config = []

if role == "Admin/Director":
    tabs_config = ["📊 Dashboard", "📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual", "👥 Usuarios y Seguridad", "📜 Bitácora Auditoría"]
else:
    tabs_config = ["📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual"]

tabs = st.tabs(tabs_config)
tab_dict = {name: tab_obj for name, tab_obj in zip(tabs_config, tabs)}

# ==========================================
# MÓDULO 1: DASHBOARD EJECUTIVO
# ==========================================
if "📊 Dashboard" in tab_dict:
    with tab_dict["📊 Dashboard"]:
        st.subheader("📊 Panel de Gobierno Ejecutivo")
        
        # Conexión DB y extracción rápida
        conn = get_db_connection()
        total_p = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        monto_total = conn.execute("SELECT SUM(total_amount) FROM projects").fetchone()[0] or 0.0
        ganados_n = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'Ganado'").fetchone()[0]
        perdidos_n = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'Perdido'").fetchone()[0]
        projs_all = conn.execute("SELECT * FROM projects").fetchall()
        alertas_p = conn.execute("SELECT COUNT(*) FROM tasks WHERE is_completed = 0").fetchone()[0]
        conn.close()
        
        # Tarjetas KPI elegantes nativas
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            st.metric("Proyectos Registrados", total_p)
        with col_k2:
            st.metric("Monto Total Cotizado", f"${monto_total:,.2f}")
        with col_k3:
            denom_exito = (ganados_n + perdidos_n)
            tasa_exito = (ganados_n / denom_exito * 100) if denom_exito > 0 else 0.0
            st.metric("Efectividad Comercial", f"{tasa_exito:.1f}%")
        with col_k4:
            st.metric("Alertas Pendientes", alertas_p)
            
        st.markdown("---")
        
        # Gráficos dinámicos nativos de Plotly
        col_g1, col_g2 = st.columns(2)
        df_p = pd.DataFrame([dict(p) for p in projs_all]) if projs_all else pd.DataFrame()
        
        with col_g1:
            st.markdown("##### 📍 Monto Cotizado por Región")
            if not df_p.empty:
                fig_reg = px.bar(
                    df_p, 
                    x="zone", 
                    y="total_amount", 
                    color="zone", 
                    labels={"total_amount": "Monto ($)", "zone": "Región"},
                    color_discrete_map={"Norte": "#3b82f6", "Sur": "#8b5cf6"},
                    text_auto='.2s'
                )
                fig_reg.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_reg, use_container_width=True)
            else:
                st.caption("Sin datos para graficar")
                
        with col_g2:
            st.markdown("##### 📈 Distribución Comercial de Proyectos")
            if not df_p.empty:
                fig_stat = px.pie(
                    df_p, 
                    names="status", 
                    color="status",
                    color_discrete_map={"En Proceso": "#f59e0b", "Ganado": "#10b981", "Perdido": "#ef4444", "Cancelado": "#6b7280"},
                    hole=0.4
                )
                fig_stat.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_stat, use_container_width=True)
            else:
                st.caption("Sin datos para graficar")

# ==========================================
# MÓDULO 2: PIPELINE COMERCIAL (NATIVO, ESTABLE)
# ==========================================
if "📋 Tablero de Proyectos" in tab_dict:
    with tab_dict["📋 Tablero de Proyectos"]:
        st.subheader("📋 Pipeline de Obras y Proyectos")
        
        # Solo Ventas y Admin pueden crear proyectos
        if role in ["Admin/Director", "Ventas"]:
            with st.expander("➕ Registrar Nuevo Proyecto"):
                with st.form("Add Project Form"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        p_id = st.text_input("ID Proyecto (Ej: PRJ-105)")
                        p_name = st.text_input("Nombre de la Obra")
                        p_client = st.text_input("Cliente")
                        p_amount = st.number_input("Monto Cotizado ($)", min_value=0.0, step=10000.0)
                    with col_f2:
                        p_state = st.selectbox("Estado de la República", list(ESTADOS_MEXICO.keys()))
                        p_costos = st.selectbox("Analista de Costos Asignado", [
                            "Analista de Costos Jefe", 
                            "Analista de Costos Junior 1", 
                            "Analista de Costos Junior 2"
                        ])
                        p_target = st.date_input("Fecha Compromiso de Entrega")
                    
                    btn_add_proj = st.form_submit_button("Guardar Proyecto en Pipeline 📂")
                    
                    if btn_add_proj:
                        if not p_id or not p_name:
                            st.error("El ID del Proyecto y Nombre de la Obra son obligatorios.")
                        else:
                            region_auto = ESTADOS_MEXICO[p_state]
                            zone_auto = "Sur" if "Sur" in region_auto else "Norte"
                            rev_dir_auto = 1 if p_amount >= 1000000.0 else 0
                            
                            conn = get_db_connection()
                            try:
                                conn.execute('''
                                    INSERT INTO projects (id, name, client, total_amount, state, zone, assigned_lider, assigned_costos, status, current_stage, created_at, target_date, director_review_required)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (p_id, p_name, p_client, p_amount, p_state, zone_auto, region_auto, p_costos, "En Proceso", 1, date.today().strftime("%Y-%m-%d"), p_target.strftime("%Y-%m-%d"), rev_dir_auto))
                                
                                # Autogenerar las 5 compuertas
                                compuertas_def = [
                                    (1, "Registrar ficha técnica y alcance inicial", "Ventas"),
                                    (2, "Realizar reunión de alineación y minuta", region_auto),
                                    (3, "Generar catálogo de conceptos técnico", "Ingeniero"),
                                    (4, "Revisión técnica de dossier de obra", region_auto),
                                    (5, "Firma de aprobación final y envío", "Admin/Director")
                                ]
                                for stage_num, task_title, resp_role in compuertas_def:
                                    conn.execute('''
                                        INSERT INTO tasks (project_id, stage, title, assigned_role, is_completed)
                                        VALUES (?, ?, ?, ?, 0)
                                    ''', (p_id, stage_num, task_title, resp_role))
                                    
                                conn.commit()
                                log_audit(p_id, st.session_state.full_name, role, f"Registró nuevo proyecto: '{p_name}'")
                                st.success(f"Proyecto {p_id} registrado con éxito.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"El ID de proyecto {p_id} ya existe.")
                            finally:
                                conn.close()

        # Presentación de datos 100% nativa con st.dataframe (Cero código HTML a la vista)
        conn = get_db_connection()
        proyectos = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        if not proyectos:
            st.warning("No hay proyectos registrados en este momento.")
        else:
            df_display = pd.DataFrame([dict(p) for p in proyectos])
            
            # Renombrar columnas para la vista ejecutiva
            df_display_renamed = df_display.rename(columns={
                'id': 'ID Proyecto',
                'name': 'Obra / Proyecto',
                'client': 'Cliente',
                'total_amount': 'Monto Cotizado ($)',
                'state': 'Estado',
                'zone': 'Región',
                'assigned_costos': 'Analista Costos',
                'status': 'Estado Comercial',
                'current_stage': 'Etapa',
                'director_review_required': 'Rev. Dirección'
            })
            
            # Ajustar la columna de Revisión de Dirección
            df_display_renamed['Rev. Dirección'] = df_display_renamed['Rev. Dirección'].apply(lambda x: 'REQUERIDA' if x == 1 else 'No requerida')
            
            # Ordenar columnas deseadas
            cols_order = ['ID Proyecto', 'Obra / Proyecto', 'Cliente', 'Monto Cotizado ($)', 'Estado', 'Región', 'Analista Costos', 'Estado Comercial', 'Etapa', 'Rev. Dirección']
            df_display_renamed = df_display_renamed[cols_order]
            
            st.markdown("##### 📋 Listado Ejecutivo de Proyectos")
            st.dataframe(
                df_display_renamed,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Monto Cotizado ($)": st.column_config.NumberColumn(format="$%,.2f"),
                    "Etapa": st.column_config.ProgressColumn("Avance Etapa", min_value=1, max_value=5, format="Etapa %d/5"),
                    "Estado Comercial": st.column_config.SelectboxColumn("Estatus", options=["En Proceso", "Ganado", "Perdido", "Cancelado"])
                }
            )
            
            # Acciones rápidas de cambio de estatus y eliminación en un panel limpio
            st.markdown("---")
            with st.expander("⚙️ Acciones Rápidas - Modificar o Eliminar Obra"):
                col_sel_p, col_sel_s, col_sel_e = st.columns([2, 1, 1])
                with col_sel_p:
                    proj_select = st.selectbox("Seleccionar Proyecto para Editar", [f"{p['id']} - {p['name']}" for p in proyectos], key="action_proj_sel")
                    sel_id = proj_select.split(" - ")[0]
                    proj_data = next(p for p in proyectos if p['id'] == sel_id)
                with col_sel_s:
                    nuevo_est = st.selectbox("Estatus Comercial", ["En Proceso", "Ganado", "Perdido", "Cancelado"], index=["En Proceso", "Ganado", "Perdido", "Cancelado"].index(proj_data['status']), key="action_est_sel")
                with col_sel_e:
                    nueva_etapa = st.slider("Etapa Actual", 1, 5, int(proj_data['current_stage']), key="action_etp_slider")
                
                col_btn_save, col_btn_del = st.columns(2)
                with col_btn_save:
                    if st.button("Guardar Cambios 💾", use_container_width=True):
                        conn = get_db_connection()
                        conn.execute("UPDATE projects SET status = ?, current_stage = ? WHERE id = ?", (nuevo_est, nueva_etapa, sel_id))
                        conn.commit()
                        conn.close()
                        log_audit(sel_id, st.session_state.full_name, role, f"Actualizó Estatus comercial a '{nuevo_est}' y Etapa a '{nueva_etapa}'")
                        st.success(f"Proyecto {sel_id} actualizado.")
                        st.rerun()
                        
                with col_btn_del:
                    confirm_del_proj = st.checkbox(f"Confirmar eliminación completa de {sel_id} ⚠️", value=False, key="chk_del_proj")
                    btn_del_proj = st.button("Eliminar Proyecto Seleccionado 🗑️", type="primary", use_container_width=True, disabled=not confirm_del_proj)
                    if btn_del_proj:
                        conn = get_db_connection()
                        # Borrar tareas de compuertas
                        conn.execute("DELETE FROM tasks WHERE project_id = ?", (sel_id,))
                        # Borrar proyecto
                        conn.execute("DELETE FROM projects WHERE id = ?", (sel_id,))
                        conn.commit()
                        conn.close()
                        log_audit(sel_id, st.session_state.full_name, role, f"Eliminó el proyecto '{proj_data['name']}' y sus compuertas.")
                        st.success(f"Proyecto {sel_id} eliminado exitosamente del sistema.")
                        st.rerun()

# ==========================================
# MÓDULO 3: COMPUERTAS TÉCNICAS (ORGANIZACIÓN LIMPIA TAREA POR TAREA)
# ==========================================
if "✔️ Compuertas Técnicas" in tab_dict:
    with tab_dict["✔️ Compuertas Técnicas"]:
        st.subheader("✔️ Compuertas Técnicas de Control (Gobernanza)")
        st.write("Gestiona las compuertas técnicas del proyecto etapa por etapa:")
        
        conn = get_db_connection()
        projs = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        if not projs:
            st.info("No hay proyectos registrados.")
        else:
            proj_options = {f"{p['id']} - {p['name']} ({p['zone']})": p for p in projs}
            selected_proj_label = st.selectbox("📁 Seleccionar Proyecto", list(proj_options.keys()), key="compuertas_proj_select")
            p = proj_options[selected_proj_label]
            
            # Métricas ejecutivas nativas
            col_pm1, col_pm2, col_pm3, col_pm4 = st.columns(4)
            with col_pm1:
                st.metric("Cliente", p['client'])
            with col_pm2:
                st.metric("Monto Cotizado", f"${p['total_amount']:,.2f}")
            with col_pm3:
                st.metric("Estatus Comercial", p['status'])
            with col_pm4:
                st.write("**Avance General**")
                st.progress(p['current_stage'] / 5.0)
                st.caption(f"Etapa {p['current_stage']} de 5")
                
            st.markdown("---")
            st.markdown("##### 🏁 Validación del Flujo de Trabajo (Etapa por Etapa)")
            
            conn = get_db_connection()
            tasks_p = conn.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY stage ASC", (p['id'],)).fetchall()
            conn.close()
            
            # Pestañas horizontales nativas por Etapa
            stage_names = [
                "Etapa 1: Registro 📋",
                "Etapa 2: Alineación 🤝",
                "Etapa 3: Ingeniería ⚙️",
                "Etapa 4: Dossier 📝",
                "Etapa 5: Cierre 🚀"
            ]
            task_tabs = st.tabs(stage_names)
            
            for stage_idx in range(1, 6):
                with task_tabs[stage_idx - 1]:
                    stage_tasks = [t for t in tasks_p if t['stage'] == stage_idx]
                    
                    if not stage_tasks:
                        st.info("No hay tareas configuradas para esta etapa.")
                    else:
                        for t in stage_tasks:
                            with st.container(border=True):
                                col_task_info, col_task_status = st.columns([3, 1])
                                with col_task_info:
                                    st.markdown(f"#### {t['title']}")
                                    st.write(f"👤 **Rol Responsable:** {t['assigned_role']}")
                                    email_dest = get_email_for_role(t['assigned_role'])
                                    st.write(f"📧 **Correo del Responsable:** {email_dest}")
                                with col_task_status:
                                    if t['is_completed'] == 1:
                                        st.success("✔️ COMPLETADA")
                                        st.caption(f"Por: {t['completed_by']}\nFecha: {t['completed_at']}")
                                    else:
                                        st.error("⏳ PENDIENTE")
                                
                                # Botón de acción estable
                                puesto_usuario = st.session_state.user_role
                                puesto_es_valido = (t['assigned_role'] == puesto_usuario or puesto_usuario == "Admin/Director")
                                
                                if t['is_completed'] == 0:
                                    btn_comp = st.button("Validar y Completar Tarea ✔️", key=f"btn_comp_{t['id']}", disabled=not puesto_es_valido, use_container_width=True)
                                    if btn_comp:
                                        conn_up = get_db_connection()
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        conn_up.execute('''
                                            UPDATE tasks 
                                            SET is_completed = 1, completed_by = ?, completed_at = ?
                                            WHERE id = ?
                                        ''', (st.session_state.full_name, now_str, t['id']))
                                        conn_up.commit()
                                        conn_up.close()
                                        log_audit(p['id'], st.session_state.full_name, role, f"Completó la compuerta técnica Etapa {t['stage']}: '{t['title']}'")
                                        st.success("¡Tarea completada con éxito!")
                                        st.rerun()
                                else:
                                    st.caption("Esta tarea ha sido validada.")

# ==========================================
# MÓDULO 4: KANBAN VISUAL (100% NATIVO)
# ==========================================
if "🗺️ Kanban Visual" in tab_dict:
    with tab_dict["🗺️ Kanban Visual"]:
        st.subheader("🗺️ Tablero Kanban Dinámico")
        
        conn = get_db_connection()
        projects_k = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        # Columnas Kanban usando contenedores nativos
        col_kp, col_kg, col_kd = st.columns(3)
        
        with col_kp:
            st.info("⏳ EN PROCESO")
            for p in projects_k:
                if p['status'] == "En Proceso":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.write(f"💰 Monto: ${p['total_amount']:,.2f}")
                        st.write(f"👤 Líder: {p['assigned_lider']}")
                        st.progress(p['current_stage'] / 5.0)
                        
        with col_kg:
            st.success("✔️ GANADOS")
            for p in projects_k:
                if p['status'] == "Ganado":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.write(f"💰 Monto: ${p['total_amount']:,.2f}")
                        st.write(f"👤 Líder: {p['assigned_lider']}")
                        st.progress(1.0)
                        
        with col_kd:
            st.error("🚨 PERDIDOS")
            for p in projects_k:
                if p['status'] == "Perdido":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.write(f"💰 Monto: ${p['total_amount']:,.2f}")
                        st.write(f"Desfase: {p['lose_percentage_gap']}%")
                        st.progress(p['current_stage'] / 5.0)

# ==========================================
# MÓDULO 5: USUARIOS Y SEGURIDAD
# ==========================================
if "👥 Usuarios y Seguridad" in tab_dict:
    with tab_dict["👥 Usuarios y Seguridad"]:
        st.subheader("👥 Configuración de Usuarios e Involucrados")
        
        conn = get_db_connection()
        users_list = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        
        st.markdown("##### 👥 Directorio Oficial de Colaboradores")
        
        # Presentación en tarjetas visuales de alto nivel (Cero HTML crudo a la vista)
        for u in users_list:
            with st.container(border=True):
                col_u_info, col_u_role, col_u_mail, col_u_action = st.columns([2, 2, 3, 1])
                with col_u_info:
                    st.markdown(f"**{u['full_name']}**")
                    st.caption(f"Usuario: `{u['username']}`")
                with col_u_role:
                    st.markdown(f"💼 **Puesto:** {u['role']}")
                with col_u_mail:
                    user_email = u['email'] if ('email' in u.keys() and u['email']) else "No configurado"
                    st.markdown(f"📧 **Correo:** `{user_email}`")
                with col_u_action:
                    # Protección del admin maestro o de sí mismo
                    is_protected = (u['username'] == 'admin' or u['username'] == st.session_state.user_name)
                    if st.button("🗑️", key=f"del_user_{u['username']}", disabled=is_protected, help="Eliminar Usuario"):
                        conn_del = get_db_connection()
                        conn_del.execute("DELETE FROM users WHERE username = ?", (u['username'],))
                        conn_del.commit()
                        conn_del.close()
                        log_audit("SISTEMA", st.session_state.full_name, role, f"Eliminó la cuenta de usuario: '{u['username']}'")
                        st.success(f"Usuario '{u['username']}' eliminado del sistema.")
                        st.rerun()
                        
        # Registrar nuevo usuario con correo individual
        with st.expander("➕ Registrar Nuevo Usuario"):
            with st.form("Add User"):
                nu_user = st.text_input("Usuario (Login)")
                nu_pass = st.text_input("Contraseña", type="password")
                nu_name = st.text_input("Nombre Completo")
                nu_role = st.selectbox("Puesto / Rol", list(EMAIL_MAP.keys()))
                nu_email = st.text_input("Correo Electrónico Individual")
                
                btn_nu = st.form_submit_button("Crear Cuenta")
                if btn_nu:
                    if not nu_user or not nu_pass or not nu_name or not nu_email:
                        st.error("Todos los campos (incluyendo el correo electrónico) son obligatorios.")
                    else:
                        conn = get_db_connection()
                        try:
                            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (nu_user, nu_pass, nu_name, nu_role, nu_email))
                            conn.commit()
                            log_audit("SISTEMA", st.session_state.full_name, role, f"Creó nueva cuenta de usuario: '{nu_user}'")
                            st.success(f"Usuario {nu_user} creado con éxito.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("El nombre de usuario ya existe.")
                        finally:
                            conn.close()
        
        # --- SECCIÓN DE MANTENIMIENTO: RESTABLECIMIENTO DE BASE DE DATOS (Solo Admin) ---
        if st.session_state.user_role == "Admin/Director":
            st.markdown("---")
            st.markdown("##### ⚙️ Mantenimiento de la Base de Datos")
            with st.expander("🚨 Restablecer Base de Datos a Cero"):
                st.warning("Esta acción borrará de manera permanente todos los proyectos, tareas de compuertas técnicas y bitácoras de auditoría. Las cuentas de usuario y contraseñas se conservarán intactas.")
                confirm_reset = st.checkbox("Entiendo las consecuencias y confirmo que deseo borrar todos los datos del pipeline.")
                
                if st.button("Proceder con el Borrado Completo ⚠️", type="primary", disabled=not confirm_reset):
                    try:
                        conn_res = get_db_connection()
                        cursor_res = conn_res.cursor()
                        # Limpiar los registros de las tablas operativas
                        cursor_res.execute("DELETE FROM projects")
                        cursor_res.execute("DELETE FROM tasks")
                        cursor_res.execute("DELETE FROM audit_log")
                        # Forzar la marca 'initialized' a '1' en system_settings para que init_db() sepa que NO debe rellenar los demos
                        cursor_res.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('initialized', '1')")
                        conn_res.commit()
                        conn_res.close()
                        
                        st.success("¡Base de datos de proyectos, tareas de compuertas y bitácoras de auditoría restablecida a cero con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al restablecer la base de datos: {e}")

# ==========================================
# MÓDULO 6: BITÁCORA HISTÓRICA (AUDIT TRAIL)
# ==========================================
if "📜 Bitácora Auditoría" in tab_dict:
    with tab_dict["📜 Bitácora Auditoría"]:
        st.subheader("📜 Bitácora de Trazabilidad (Audit Trail)")
        st.write("Conteo histórico e inalterable de acciones realizadas:")
        
        conn = get_db_connection()
        logs = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
        conn.close()
        
        if not logs:
            st.info("No se han registrado acciones aún.")
        else:
            df_logs = pd.DataFrame([dict(l) for l in logs])
            
            # Renombrar columnas para la vista ejecutiva
            df_logs_display = df_logs.rename(columns={
                'project_id': 'Proyecto ID',
                'user_name': 'Usuario Responsable',
                'role': 'Puesto / Rol',
                'action': 'Acción Realizada',
                'timestamp': 'Fecha y Hora'
            })[['Proyecto ID', 'Usuario Responsable', 'Puesto / Rol', 'Acción Realizada', 'Fecha y Hora']]
            
            st.dataframe(df_logs_display, use_container_width=True, hide_index=True)

# Footer Corporativo
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #9ca3af; font-size: 12px;'>"
    "DC Control S.A. de C.V. • Sistema de Trazabilidad y Gobernanza de Proyectos"
    "</p>", 
    unsafe_allow_html=True
)
