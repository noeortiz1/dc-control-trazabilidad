# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO MONDAY.COM
# ==========================================
st.set_page_config(
    page_title="DC Control - Sistema de Trazabilidad Súper-Gobernado v18",
    layout="wide",
    page_icon="🏗️"
)

# Inyección de CSS para simular la interfaz limpia, moderna y colorida de Monday.com
st.markdown("""
<style>
    /* Estilo general */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    
    /* Cabeceras estilo Monday */
    .monday-header {
        background: linear-gradient(135deg, #1f2937, #111827);
        color: white;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 25px;
        border-left: 10px solid #00C875;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .monday-title {
        font-size: 32px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .monday-subtitle {
        color: #9ca3af;
        margin-top: 5px;
        font-size: 16px;
    }
    
    /* Tarjetas de Métricas (KPIs) */
    .kpi-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #0085FF;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        text-align: left;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
    }
    .kpi-title {
        color: #6b7280;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        color: #1f2937;
        font-size: 26px;
        font-weight: 700;
    }
    
    /* Botones de estatus estilo Monday.com */
    .badge {
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: bold;
        color: white;
        text-align: center;
        display: inline-block;
        font-size: 13px;
    }
    .status-completado { background-color: #00C875; }  /* Verde Monday */
    .status-proceso { background-color: #FDAB3D; }     /* Naranja/Amarillo Monday */
    .status-bloqueado { background-color: #E2445C; }   /* Rojo Monday */
    .status-pendiente { background-color: #797E93; }   /* Gris Monday */
    .status-revision { background-color: #0085FF; }    /* Azul Monday */
    
    /* Estructuras de grupo colapsables (Monday Groups) */
    .group-header {
        font-size: 18px;
        font-weight: bold;
        padding: 10px 15px;
        border-radius: 6px;
        color: white;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .group-norte { background-color: #579BFC; }
    .group-sur { background-color: #A25DDC; }
    .group-admin { background-color: #111827; }

    /* Estilo de tabla de monday.com */
    .monday-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .monday-table th {
        background-color: #f8f9fa;
        color: #323338;
        font-weight: 600;
        text-align: left;
        padding: 12px 16px;
        font-size: 14px;
        border-bottom: 2px solid #e2e4e9;
    }
    .monday-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #e2e4e9;
        font-size: 14px;
        color: #323338;
    }
    .monday-table tr:hover {
        background-color: #fcfcfd;
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

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Configuración de Correo
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
            meeting_minutes_date TEXT,
            meeting_minutes_attendance TEXT,
            meeting_minutes_decisions TEXT,
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
    ''''')
    
    # Insertar usuarios demo si no existen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            full_name TEXT,
            role TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        demo_users = [
            ("admin", "admin123", "Director General", "Admin/Director"),
            ("ventas", "ventas123", "Pedro Sánchez", "Ventas"),
            ("lider.sur", "sur123", "Ing. Sofía Romero", "Líder Regional - Sur"),
            ("lider.norte", "norte123", "Ing. Marcos Ortiz", "Líder Regional - Norte"),
            ("costos.jefe", "jefe123", "Lic. Fernando Ruiz", "Analista de Costos Jefe"),
            ("ingeniero", "ing123", "Ing. Alejandro Mendoza", "Ingeniero")
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", demo_users)
        
    # Insertar proyectos demo si no hay datos
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        demo_projects = [
            ("PRJ-101", "Ampliación Planta Monterrey", "Aceros de Monterrey S.A.", 1250000.0, "Nuevo León", "Norte", "Líder Regional - Norte", "Analista de Costos Jefe", "En Proceso", 3, 0.0, 1, "2026-08-05", "Marcos Ortiz, Pedro Sánchez", "Se acordó alcance de obra y fecha de cotización técnica.", "2026-08-01", "2026-09-15"),
            ("PRJ-102", "Instalación Eléctrica Querétaro", "Logística del Centro", 450000.0, "Querétaro", "Sur", "Líder Regional - Sur", "Analista de Costos Junior 1", "Ganado", 5, 0.0, 0, "2026-08-06", "Sofía Romero, Pedro Sánchez", "Cliente acepta el catálogo técnico.", "2026-08-05", "2026-10-10"),
            ("PRJ-103", "Mantenimiento Preventivo Chiapas", "Cervecería del Sur", 850000.0, "Chiapas", "Sur", "Líder Regional - Sur", "Analista de Costos Junior 2", "Perdido", 5, 15.0, 0, "2026-08-11", "Sofía Romero, Pedro Sánchez", "Revisión de costos fuera de presupuesto del cliente.", "2026-08-10", "2026-09-01"),
            ("PRJ-104", "Subestación Baja California", "Energía del Norte", 3200000.0, "Baja California", "Norte", "Líder Regional - Norte", "Analista de Costos Jefe", "En Proceso", 2, 0.0, 1, "2026-08-21", "Marcos Ortiz", "Alineación inicial sobre planos eléctricos.", "2026-08-20", "2026-11-30")
        ]
        cursor.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", demo_projects)
        
        # Insertar tareas de compuertas demo correspondientes
        demo_tasks = [
            # PRJ-101
            (None, "PRJ-101", 1, "Registrar ficha técnica y alcance inicial", "Ventas", 1, "Pedro Sánchez", "2026-08-02 10:00:00"),
            (None, "PRJ-101", 2, "Realizar reunión de alineación y minuta", "Líder Regional - Norte", 1, "Ing. Marcos Ortiz", "2026-08-05 15:30:00"),
            (None, "PRJ-101", 3, "Generar catálogo de conceptos técnico", "Ingeniero", 0, None, None),
            (None, "PRJ-101", 3, "Elaborar análisis de precios unitarios", "Analista de Costos Jefe", 0, None, None),
            (None, "PRJ-101", 4, "Revisión técnica de dossier de obra", "Líder Regional - Norte", 0, None, None),
            (None, "PRJ-101", 5, "Firma de aprobación final y envío", "Admin/Director", 0, None, None),
            # PRJ-102
            (None, "PRJ-102", 1, "Registrar ficha técnica y alcance inicial", "Ventas", 1, "Pedro Sánchez", "2026-08-06 09:12:00"),
            (None, "PRJ-102", 2, "Realizar reunión de alineación y minuta", "Líder Regional - Sur", 1, "Ing. Sofía Romero", "2026-08-07 14:00:00"),
            (None, "PRJ-102", 3, "Generar catálogo de conceptos técnico", "Ingeniero", 1, "Ing. Alejandro Mendoza", "2026-08-15 11:45:00"),
            (None, "PRJ-102", 4, "Revisión técnica de dossier de obra", "Líder Regional - Sur", 1, "Ing. Sofía Romero", "2026-08-18 16:30:00"),
            (None, "PRJ-102", 5, "Firma de aprobación final y envío", "Admin/Director", 1, "Director General", "2026-08-20 18:00:00"),
        ]
        cursor.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", demo_tasks)
        
    conn.commit()
    conn.close()

init_db()

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

def enviar_correo_alerta(destinatario, rol_dest, asunto, proyecto_nombre, tarea_desc):
    # En Streamlit local, si no está configurado SMTP real, simulamos el correo
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

if not st.session_state.logged_in:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background-color:#1e3a8a; padding:30px; border-radius:15px; text-align:center; margin-bottom:20px; border-left: 8px solid #00C875; box-shadow: 0 4px 10px rgba(0,0,0,0.1);'>
            <h1 style='color:white; margin:0; font-family:sans-serif; letter-spacing: 2px; font-size: 32px;'>DC CONTROL</h1>
            <p style='color:#93c5fd; font-family:sans-serif; font-weight: bold; margin: 5px 0 0 0;'>Sistema de Trazabilidad y Gobierno Corporativo v18</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("Login Form"):
            st.markdown("<h4 style='text-align: center; color: #1f2937;'>Ingreso de Colaboradores</h4>", unsafe_allow_html=True)
            u_name = st.text_input("Usuario")
            u_pass = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Iniciar Sesión 🚪", use_container_width=True)
            
            if btn_login:
                conn = get_db_connection()
                user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (u_name, u_pass)).fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user['username']
                    st.session_state.user_role = user['role']
                    st.session_state.full_name = user['full_name']
                    st.success(f"¡Bienvenido, {user['full_name']}!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Intenta de nuevo.")
        
        st.markdown("""
        <div style='text-align: center; margin-top: 20px; background-color: #f3f4f6; padding: 15px; border-radius: 8px; font-size: 13px; color: #4b5563;'>
            <strong>Usuarios Demo de Acceso Rápido:</strong><br>
            • Admin: <code>admin</code> / <code>admin123</code><br>
            • Ventas: <code>ventas</code> / <code>ventas123</code><br>
            • Líder Norte: <code>lider.norte</code> / <code>norte123</code>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

# ==========================================
# MENÚ COLABORATIVO (SIDEBAR)
# ==========================================
# Cabecera Lateral
st.sidebar.markdown("""
<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px; border-left: 5px solid #00C875;'>
    <h3 style='color:white; margin:0; font-family:sans-serif; letter-spacing: 1px;'>DC CONTROL</h3>
    <small style='color:#93c5fd;'>Control de Obras & Trazabilidad</small>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
👤 **Sesión Activa:** 
* **Nombre:** {st.session_state.full_name}
* **Puesto:** `{st.session_state.user_role}`
""")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Inspirado en Monday.com**\n\nEste sistema agrupa los proyectos por región y te permite ver el avance de sus compuertas técnicas de manera limpia y colorida.")

# ==========================================
# PANEL PRINCIPAL Y PESTAÑAS (TABS)
# ==========================================
st.markdown(f"""
<div class="monday-header">
    <div class="monday-title">🏗️ DC Control Workspace</div>
    <div class="monday-subtitle">Trazabilidad Súper-Gobernada • Rol activo: {st.session_state.user_role}</div>
</div>
""", unsafe_allow_html=True)

# Definir pestañas de Monday según el Rol
role = st.session_state.user_role
tabs_config = []

if role == "Admin/Director":
    tabs_config = ["📊 Dashboard", "📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual", "👥 Usuarios y Seguridad", "📜 Bitácora Auditoría"]
elif role == "Ventas":
    tabs_config = ["📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual"]
elif "Líder Regional" in role or role == "Ingeniero":
    tabs_config = ["📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual"]
elif "Analista de Costos" in role:
    tabs_config = ["📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual"]

tabs = st.tabs(tabs_config)
tab_dict = {name: tab_obj for name, tab_obj in zip(tabs_config, tabs)}

# ==========================================
# MÓDULO 1: DASHBOARD EJECUTIVO
# ==========================================
if "📊 Dashboard" in tab_dict:
    with tab_dict["📊 Dashboard"]:
        st.subheader("📊 Indicadores de Desempeño y Estado Comercial")
        
        # Cargar datos de la base de datos
        conn = get_db_connection()
        df_proj = pd.read_sql_query("SELECT * FROM projects", conn)
        df_tasks = pd.read_sql_query("SELECT * FROM tasks", conn)
        conn.close()
        
        # KPIs en tarjetas estilo Monday
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        
        total_p = len(df_proj)
        total_amount = df_proj['total_amount'].sum()
        ganados = len(df_proj[df_proj['status'] == 'Ganado'])
        perdidos = len(df_proj[df_proj['status'] == 'Perdido'])
        efectividad = (ganados / (ganados + perdidos) * 100) if (ganados + perdidos) > 0 else 0.0
        tareas_pendientes = len(df_tasks[df_tasks['is_completed'] == 0])
        
        with col_kpi1:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #579BFC;">
                <div class="kpi-title">Proyectos Totales</div>
                <div class="kpi-value">{total_p} Obras</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi2:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #00C875;">
                <div class="kpi-title">Monto Total Cotizado</div>
                <div class="kpi-value">${total_amount:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi3:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #FDAB3D;">
                <div class="kpi-title">Efectividad Comercial</div>
                <div class="kpi-value">{efectividad:.1f}% Éxito</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi4:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #E2445C;">
                <div class="kpi-title">Compuertas Técnicas Pendientes</div>
                <div class="kpi-value">{tareas_pendientes} Alertas</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Gráficas dinámicas
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("##### Distribución del Monto por Región ($)")
            df_g_region = df_proj.groupby('zone')['total_amount'].sum().reset_index()
            fig_region = px.bar(
                df_g_region, 
                x='zone', 
                y='total_amount', 
                color='zone',
                color_discrete_map={"Norte": "#579BFC", "Sur": "#A25DDC"},
                labels={'total_amount': 'Monto ($)', 'zone': 'Región'},
                text_auto='.2s'
            )
            fig_region.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_region, use_container_width=True)
            
        with col_g2:
            st.markdown("##### Pipeline: Estados Comerciales")
            df_g_status = df_proj.groupby('status').size().reset_index(name='count')
            fig_status = px.pie(
                df_g_status, 
                values='count', 
                names='status',
                color='status',
                color_discrete_map={"En Proceso": "#FDAB3D", "Ganado": "#00C875", "Perdido": "#E2445C", "Cancelado": "#797E93"},
                hole=0.4
            )
            fig_status.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_status, use_container_width=True)

# ==========================================
# MÓDULO 2: TABLERO DE PROYECTOS (MONDAY STYLE)
# ==========================================
if "📋 Tablero de Proyectos" in tab_dict:
    with tab_dict["📋 Tablero de Proyectos"]:
        st.subheader("📋 Tablero de Control de Proyectos")
        
        # Botón para añadir nuevo proyecto (Solo Ventas y Admin)
        if role in ["Admin/Director", "Ventas"]:
            with st.expander("➕ Registrar Nuevo Proyecto / Obra"):
                with st.form("Agregar Proyecto Form"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        p_id = st.text_input("ID del Proyecto (ej. PRJ-105)")
                        p_name = st.text_input("Nombre de la Obra")
                        p_client = st.text_input("Cliente")
                        p_amount = st.number_input("Monto Cotizado ($)", min_value=0.0, format="%.2f")
                    with col_f2:
                        p_state = st.selectbox("Estado de la República", list(ESTADOS_MEXICO.keys()))
                        p_costos = st.selectbox("Analista de Costos Asignado", ["Analista de Costos Jefe", "Analista de Costos Junior 1", "Analista de Costos Junior 2"])
                        p_target = st.date_input("Fecha Compromiso de Entrega")
                    
                    btn_add_proj = st.form_submit_button("Guardar Proyecto en Pipeline 📂")
                    
                    if btn_add_proj:
                        if not p_id or not p_name:
                            st.error("El ID del Proyecto y Nombre de la Obra son obligatorios.")
                        else:
                            # Calcular automáticamente la Región y Líder
                            region_auto = ESTADOS_MEXICO[p_state]
                            zone_auto = "Sur" if "Sur" in region_auto else "Norte"
                            
                            # Validar si requiere revisión de dirección (Monto >= $1,000,000)
                            rev_dir_auto = 1 if p_amount >= 1000000.0 else 0
                            
                            conn = get_db_connection()
                            try:
                                conn.execute('''
                                    INSERT INTO projects (id, name, client, total_amount, state, zone, assigned_lider, assigned_costos, status, current_stage, created_at, target_date, director_review_required)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (p_id, p_name, p_client, p_amount, p_state, zone_auto, region_auto, p_costos, "En Proceso", 1, date.today().strftime("%Y-%m-%d"), p_target.strftime("%Y-%m-%d"), rev_dir_auto))
                                
                                # Autogenerar las 5 compuertas de control por defecto
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
                                log_audit(p_id, st.session_state.full_name, role, f"Registró nuevo proyecto: '{p_name}' con monto ${p_amount:,.2f}")
                                st.success(f"Proyecto {p_id} registrado exitosamente y compuertas de control asignadas.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"El ID de proyecto {p_id} ya existe en la base de datos.")
                            finally:
                                conn.close()

        # Mostrar proyectos agrupados por región (Norte / Sur) estilo Monday Groups
        conn = get_db_connection()
        proyectos = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        if not proyectos:
            st.warning("No hay proyectos registrados en este momento.")
        else:
            for region_name, color_class in [("Norte", "group-norte"), ("Sur", "group-sur")]:
                projs_reg = [p for p in proyectos if p['zone'] == region_name]
                
                # Cabecera de grupo estilo Monday
                st.markdown(f"""
                <div class="group-header {color_class}">
                    <span>📍 Región {region_name}</span>
                    <span style="font-size: 13px;">{len(projs_reg)} proyectos</span>
                </div>
                """, unsafe_allow_html=True)
                
                if not projs_reg:
                    st.caption("No hay proyectos en esta región.")
                    continue
                
                # Tabla Monday construida dinámicamente con HTML para lograr el look limpio
                table_html = """
                <table class="monday-table">
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Nombre de la Obra</th>
                            <th>Cliente</th>
                            <th>Monto ($)</th>
                            <th>Estado de Rep.</th>
                            <th>Líder Regional</th>
                            <th>Estatus Comercial</th>
                            <th>Etapa Actual</th>
                            <th>Revisión Dir.</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for p in projs_reg:
                    # Formateo de estatus con color de Monday
                    status_class = "status-pendiente"
                    if p['status'] == 'Ganado': status_class = "status-completado"
                    elif p['status'] == 'En Proceso': status_class = "status-proceso"
                    elif p['status'] == 'Perdido': status_class = "status-bloqueado"
                    
                    status_badge = f'<span class="badge {status_class}">{p["status"]}</span>'
                    
                    # Formateo de Revisión de Dirección
                    rev_badge = ""
                    if p['director_review_required'] == 1:
                        rev_badge = '<span class="badge status-revision">⚠️ Requerida</span>'
                    else:
                        rev_badge = '<span class="badge status-pendiente" style="opacity:0.5;">No req.</span>'
                        
                    table_html += f"""
                        <tr>
                            <td><strong>{p['id']}</strong></td>
                            <td>{p['name']}</td>
                            <td>{p['client']}</td>
                            <td>${p['total_amount']:,.2f}</td>
                            <td>{p['state']}</td>
                            <td>{p['assigned_lider']}</td>
                            <td>{status_badge}</td>
                            <td><span class="badge" style="background-color: #3f51b5; color: white;">Etapa {p['current_stage']}/5</span></td>
                            <td>{rev_badge}</td>
                        </tr>
                    """
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
                
                # Acciones rápidas del tablero para editar estatus
                with st.expander(f"⚙️ Acciones Rápidas - Región {region_name}"):
                    for p in projs_reg:
                        col_e1, col_e2, col_e3 = st.columns([1, 1, 2])
                        with col_e1:
                            st.write(f"**{p['id']}** - {p['name']}")
                        with col_e2:
                            # Cambiar estatus comercial
                            nuevo_est = st.selectbox("Estatus", ["En Proceso", "Ganado", "Perdido", "Cancelado"], index=["En Proceso", "Ganado", "Perdido", "Cancelado"].index(p['status']), key=f"est_sel_{p['id']}")
                        with col_e3:
                            # Cambiar etapa actual
                            nueva_etapa = st.slider("Etapa Actual", 1, 5, p['current_stage'], key=f"etp_sel_{p['id']}")
                            
                        # Si cambia, actualizar DB
                        if nuevo_est != p['status'] or nueva_etapa != p['current_stage']:
                            conn = get_db_connection()
                            conn.execute("UPDATE projects SET status = ?, current_stage = ? WHERE id = ?", (nuevo_est, nueva_etapa, p['id']))
                            conn.commit()
                            conn.close()
                            log_audit(p['id'], st.session_state.full_name, role, f"Actualizó Estatus comercial a '{nuevo_est}' y Etapa a '{nueva_etapa}'")
                            st.success(f"Cambios guardados para {p['id']}.")
                            st.rerun()

# ==========================================
# MÓDULO 3: COMPUERTAS TÉCNICAS (ALERTAS)
# ==========================================
if "✔️ Compuertas Técnicas" in tab_dict:
    with tab_dict["✔️ Compuertas Técnicas"]:
        st.subheader("✔️ Compuertas Técnicas de Control (Gobernanza)")
        st.write("Cada etapa del proyecto debe ser aprobada y validada por su rol correspondiente. Las compuertas pendientes generan **alertas activas**.")
        
        conn = get_db_connection()
        projs = conn.execute("SELECT * FROM projects").fetchall()
        
        for p in projs:
            tasks_p = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (p['id'],)).fetchall()
            
            st.markdown(f"""
            <div style='background-color: #f3f4f6; padding: 10px 15px; border-radius: 6px; margin-top: 15px; border-left: 4px solid #1e3a8a;'>
                <strong>{p['id']} - {p['name']}</strong> | Cliente: {p['client']} | Región: {p['zone']}
            </div>
            """, unsafe_allow_html=True)
            
            # Dibujar tareas asociadas
            for t in tasks_p:
                col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1, 1, 1])
                
                with col_t1:
                    st.write(f"📌 **Etapa {t['stage']}:** {t['title']} (`{t['assigned_role']}`)")
                
                with col_t2:
                    if t['is_completed'] == 1:
                        st.markdown('<span class="badge status-completado">✔️ COMPLETADA</span>', unsafe_allow_html=True)
                        st.caption(f"Por: {t['completed_by']} el {t['completed_at']}")
                    else:
                        st.markdown('<span class="badge status-bloqueado">⏳ PENDIENTE</span>', unsafe_allow_html=True)
                        
                with col_t3:
                    # Habilitar botón para completarla si el usuario tiene ese rol
                    puesto_usuario = st.session_state.user_role
                    puesto_es_valido = (t['assigned_role'] == puesto_usuario or puesto_usuario == "Admin/Director")
                    
                    if t['is_completed'] == 0:
                        btn_comp = st.button("Marcar completada ✔️", key=f"btn_comp_{t['id']}", disabled=not puesto_es_valido)
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
                            st.success(f"Tarea marcada como completada.")
                            st.rerun()
                    else:
                        st.write("")
                        
                with col_t4:
                    # Enviar recordatorio si está pendiente
                    if t['is_completed'] == 0:
                        # Obtener correo destino de los catálogos
                        email_dest = EMAIL_MAP.get(t['assigned_role'], "soporte@dccontrol.com")
                        btn_mail = st.button("📧 Enviar Recordatorio", key=f"btn_mail_{t['id']}")
                        if btn_mail:
                            enviar_correo_alerta(
                                destinatario=email_dest,
                                rol_dest=t['assigned_role'],
                                asunto=f"Compuerta Técnica Pendiente - {p['id']}",
                                proyecto_nombre=p['name'],
                                tarea_desc=t['title']
                            )
        conn.close()

# ==========================================
# MÓDULO 4: KANBAN VISUAL (MONDAY VIEW)
# ==========================================
if "🗺️ Kanban Visual" in tab_dict:
    with tab_dict["🗺️ Kanban Visual"]:
        st.subheader("🗺️ Tablero Kanban Dinámico")
        st.write("Visualización de arrastre comercial y avance de las obras activas.")
        
        conn = get_db_connection()
        projects_k = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        # Columnas Kanban estilo Monday
        col_kp, col_kg, col_kd = st.columns(3)
        
        with col_kp:
            st.markdown("<div style='background-color:#FDAB3D; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>⏳ EN PROCESO</div>", unsafe_allow_html=True)
            for p in projects_k:
                if p['status'] == "En Proceso":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.caption(f"💰 Monto: ${p['total_amount']:,.2f}\n\n👤 Líder: {p['assigned_lider']}")
                        st.progress(p['current_stage'] / 5.0)
                        
        with col_kg:
            st.markdown("<div style='background-color:#00C875; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>✔️ GANADOS</div>", unsafe_allow_html=True)
            for p in projects_k:
                if p['status'] == "Ganado":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.caption(f"💰 Monto: ${p['total_amount']:,.2f}\n\n👤 Líder: {p['assigned_lider']}")
                        st.progress(1.0)
                        
        with col_kd:
            st.markdown("<div style='background-color:#E2445C; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>🚨 PERDIDOS</div>", unsafe_allow_html=True)
            for p in projects_k:
                if p['status'] == "Perdido":
                    with st.container(border=True):
                        st.markdown(f"**{p['id']} - {p['name']}**")
                        st.caption(f"💰 Monto: ${p['total_amount']:,.2f}\n\nDesfase: {p['lose_percentage_gap']}%")
                        st.progress(p['current_stage'] / 5.0)

# ==========================================
# MÓDULO 5: USUARIOS Y SEGURIDAD (Solo Admin)
# ==========================================
if "👥 Usuarios y Seguridad" in tab_dict:
    with tab_dict["👥 Usuarios y Seguridad"]:
        st.subheader("👥 Configuración de Usuarios e Involucrados")
        
        conn = get_db_connection()
        users_list = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        
        st.markdown("##### Directorio Oficial del Proyecto")
        
        # Crear tabla HTML del directorio
        dir_html = """
        <table class="monday-table">
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Nombre Completo</th>
                    <th>Puesto / Rol</th>
                    <th>Correo Electrónico</th>
                </tr>
            </thead>
            <tbody>
        """
        for u in users_list:
            email_val = EMAIL_MAP.get(u['role'], "No configurado")
            dir_html += f"""
                <tr>
                    <td><code>{u['username']}</code></td>
                    <td>{u['full_name']}</td>
                    <td><span class="badge" style="background-color: #797E93;">{u['role']}</span></td>
                    <td><a href="mailto:{email_val}">{email_val}</a></td>
                </tr>
            """
        dir_html += "</tbody></table>"
        st.markdown(dir_html, unsafe_allow_html=True)
        
        # Registrar nuevo usuario
        with st.expander("➕ Registrar Nuevo Usuario"):
            with st.form("Add User"):
                nu_user = st.text_input("Usuario (Login)")
                nu_pass = st.text_input("Contraseña (Password)", type="password")
                nu_name = st.text_input("Nombre Completo")
                nu_role = st.selectbox("Puesto / Rol", list(EMAIL_MAP.keys()))
                
                btn_nu = st.form_submit_button("Crear Cuenta")
                if btn_nu:
                    if not nu_user or not nu_pass or not nu_name:
                        st.error("Todos los campos son obligatorios.")
                    else:
                        conn = get_db_connection()
                        try:
                            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (nu_user, nu_pass, nu_name, nu_role))
                            conn.commit()
                            st.success(f"Usuario {nu_user} creado con éxito.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("El nombre de usuario ya existe.")
                        finally:
                            conn.close()

# ==========================================
# MÓDULO 6: BITÁCORA HISTÓRICA (AUDIT TRAIL)
# ==========================================
if "📜 Bitácora Auditoría" in tab_dict:
    with tab_dict["📜 Bitácora Auditoría"]:
        st.subheader("📜 Bitácora Inmutable de Trazabilidad (Audit Trail)")
        st.write("Registro oficial para el gobierno corporativo de la empresa. Las entradas no se pueden editar ni borrar.")
        
        conn = get_db_connection()
        logs = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
        conn.close()
        
        if not logs:
            st.info("No se han registrado acciones de trazabilidad aún.")
        else:
            df_logs = pd.DataFrame([dict(l) for l in logs])
            st.dataframe(df_logs, use_container_width=True)

# Footer Corporativo
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #9ca3af; font-size: 12px;'>"
    "Generated 2026-08-26 | v18.0.0 • DC Control S.A. de C.V. • Sistema de Trazabilidad y Gobernanza Total"
    "</p>", 
    unsafe_allow_html=True
)


