# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import streamlit as st
from io import BytesIO
import shutil

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO CORPORATIVO
# ==========================================
st.set_page_config(
    page_title="Control de Cotizaciones - DC Control",
    layout="wide",
    page_icon="🏗️"
)

# Estilos CSS Limpios, Ejecutivos y 100% Libres de Monday/Control de Cotizaciones/etc.
st.markdown("""
<style>
    /* Cabecera Principal */
    .system-header {
        background-color: #111827;
        color: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        border-left: 8px solid #00C875;
    }
    .system-title {
        font-size: 26px;
        font-weight: 700;
        margin: 0;
    }
    .system-subtitle {
        color: #9ca3af;
        font-size: 13px;
        margin-top: 5px;
    }
    
    /* Tarjetas de Estados / Badges Nativos */
    .badge-status {
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
        color: white;
        display: inline-block;
        font-size: 12px;
        text-align: center;
    }
    .bg-proceso { background-color: #FDAB3D; }
    .bg-ganado { background-color: #00C875; }
    .bg-perdido { background-color: #E2445C; }
    .bg-cancelado { background-color: #797E93; }
    .bg-revision { background-color: #0085FF; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONSTANTES Y CONFIGURACIONES
# ==========================================
DB_FILE = "pipeline_cotizaciones.db"
UPLOAD_DIR = "uploads"

# Asegurar que exista el directorio de cargas
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

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

# ==========================================
# GESTIÓN DE BASE DE DATOS SQLITE
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(insert_demos=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Proyectos (Esquema de Flujo Secuencial)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            client TEXT,
            total_amount REAL DEFAULT 0.0,
            final_amount REAL DEFAULT 0.0,
            state TEXT,
            zone TEXT,
            assigned_lider TEXT,
            assigned_costos TEXT,
            assigned_ventas TEXT,
            status TEXT DEFAULT 'En Proceso',
            current_stage INTEGER DEFAULT 1,
            lose_reason TEXT,
            lose_percentage_gap REAL DEFAULT 0.0,
            created_at TEXT,
            target_date TEXT,
            step1_completed INTEGER DEFAULT 0,
            step2_ventas_done INTEGER DEFAULT 0,
            step2_lider_done INTEGER DEFAULT 0,
            step2_completed INTEGER DEFAULT 0,
            step3_completed INTEGER DEFAULT 0,
            step4_completed INTEGER DEFAULT 0,
            step5_completed INTEGER DEFAULT 0,
            step6_completed INTEGER DEFAULT 0
        )
    ''')
    
    # 2. Tabla de Archivos Adjuntos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            step_name TEXT,
            filename TEXT,
            file_path TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT
        )
    ''')
    
    # 3. Tabla de Usuarios (with email column included from scratch for new DBs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            full_name TEXT,
            role TEXT,
            email TEXT
        )
    ''')
    
    # 4. Tabla de Auditoría
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
    
    # --- PROCESO DE MIGRACIÓN AUTÓNOMA ULTRA-ROBUSTA (Auto-Healing Individual) ---
    def get_columns(table_name):
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except Exception:
            return []
            
    proj_cols = get_columns('projects')
    needed_cols = {
        'final_amount': 'REAL DEFAULT 0.0',
        'assigned_ventas': 'TEXT',
        'lose_reason': 'TEXT',
        'lose_percentage_gap': 'REAL DEFAULT 0.0',
        'target_date': 'TEXT',
        'step1_completed': 'INTEGER DEFAULT 0',
        'step2_ventas_done': 'INTEGER DEFAULT 0',
        'step2_lider_done': 'INTEGER DEFAULT 0',
        'step2_completed': 'INTEGER DEFAULT 0',
        'step3_completed': 'INTEGER DEFAULT 0',
        'step4_completed': 'INTEGER DEFAULT 0',
        'step5_completed': 'INTEGER DEFAULT 0',
        'step6_completed': 'INTEGER DEFAULT 0'
    }
    
    # Migrate projects columns one by one in its own try-catch
    for col_name, col_type in needed_cols.items():
        if col_name not in proj_cols:
            try:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                pass # Silently proceed to next columns if any error occurs
                
    # Ensure uploads table has uploaded_by column
    upload_cols = get_columns('uploads')
    if 'uploaded_by' not in upload_cols:
        try:
            cursor.execute("ALTER TABLE uploads ADD COLUMN uploaded_by TEXT")
        except Exception:
            pass
            
    # Ensure users has email column
    user_cols = get_columns('users')
    if 'email' not in user_cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except Exception:
            pass

    # Clean up ALL old demo accounts and previous admin account to make space for the official Noe Ortiz admin
    try:
        cursor.execute("DELETE FROM users WHERE username IN ('admin', 'ventas1', 'lider_sur', 'lider_norte', 'costos_jefe', 'costos_jr1', 'costos_jr2', 'ingeniero')")
    except Exception:
        pass
        
    # Always ensure the admin account is set to the requested Noe Ortiz with the secure credentials (if it doesn't already exist)
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'noe.ortizadm'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (username, password, full_name, role, email)
                VALUES ('noe.ortizadm', 'jaeldiaz251', 'Noe Ortiz (Director General)', 'Admin/Director', 'director@dccontrol.com')
            """)
    except Exception as e:
        pass
        
    # Since the user wants a clean production start, we default insert_demos=False.
    # No demo projects or other users will be inserted, keeping it 100% clean.
    if insert_demos:
        try:
            cursor.execute("SELECT COUNT(*) FROM projects")
            if cursor.fetchone()[0] == 0:
                demo_projects = [
                    ("DCC-202608-N-001", "Ampliación Planta Monterrey", "Aceros de Monterrey S.A.", 1250000.0, 1250000.0, "Nuevo León", "Norte", "Ing. Alejandro Mendoza", "Analista de Costos Jefe", "Ing. Carlos", "En Proceso", 4, None, 0.0, "2026-08-01", "2026-09-15", 1, 1, 1, 1, 1, 0, 0, 0),
                    ("DCC-202608-S-001", "Instalación Eléctrica Querétaro", "Logística del Centro", 450000.0, 450000.0, "Querétaro", "Sur", "Ing. Sofía Romero", "Analista de Costos Junior 1", "Ing. Carlos", "Ganado", 7, None, 0.0, "2026-08-05", "2026-10-10", 1, 1, 1, 1, 1, 1, 1, 1)
                ]
                cursor.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", demo_projects)
        except Exception:
            pass
            
    conn.commit()
    conn.close()

init_db(insert_demos=False)

def log_audit(project_id, user_name, role, action):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO audit_log (project_id, user_name, role, action, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, user_name, role, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def generate_next_project_id(state):
    # Obtener prefijos
    year_month = datetime.now().strftime("%Y%m")
    region_auto = ESTADOS_MEXICO[state]
    zone_code = "S" if "Sur" in region_auto else "N"
    prefix = f"DCC-{year_month}-{zone_code}-"
    
    # Consultar último consecutivo
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM projects WHERE id LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",)).fetchone()
    conn.close()
    
    if row:
        last_id = row['id']
        try:
            last_num = int(last_id.split("-")[-1])
            next_num = last_num + 1
        except:
            next_num = 1
    else:
        next_num = 1
        
    return f"{prefix}{next_num:03d}"

# ==========================================
# INICIO DE SESIÓN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.full_name = ""

# Reset de seguridad para el pin de edición de perfil antes de instanciar el widget
if st.session_state.get('clear_profile_pin', False):
    st.session_state["sec_key_prof"] = ""
    st.session_state['clear_profile_pin'] = False

def logout():
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.full_name = ""
    st.rerun()

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.container(border=True):
            # Cargar logo si existe en el directorio de trabajo
            if os.path.exists("logo.png"):
                # Squeezed columns inside container to make logo centered and beautifully resized (not oversized)
                col_logo_l, col_logo_c, col_logo_r = st.columns([1, 1.5, 1])
                with col_logo_c:
                    st.image("logo.png", use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center; color: #111827; margin-bottom: 20px;'>🏗️ DC Control</h1>", unsafe_allow_html=True)
                
            st.markdown("<h4 style='text-align: center; color: #4b5563; margin-top:0;'>Control de Cotizaciones</h4>", unsafe_allow_html=True)
            st.write("---")
            username_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            btn_login = st.button("Ingresar al Sistema 🚀", use_container_width=True)
            
            if btn_login:
                conn = get_db_connection()
                user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username_input, password_input)).fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user['username']
                    st.session_state.user_role = user['role']
                    st.session_state.full_name = user['full_name']
                    st.success("Acceso autorizado con éxito")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
    st.sidebar.markdown("---")
else:
    st.sidebar.markdown("### 🏗️ DC Control")

st.sidebar.markdown(f"#### 👤 {st.session_state.full_name}")
st.sidebar.markdown(f"**Puesto:** {st.session_state.user_role}")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout()

# ==========================================
# CABECERA EJECUTIVA EN PANTALLA
# ==========================================
col_header_logo, col_header_text = st.columns([1, 6])
with col_header_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.markdown("<h1 style='margin:0; text-align:center;'>🏗️</h1>", unsafe_allow_html=True)

with col_header_text:
    st.markdown(f"""
    <div style='background-color: #111827; color: white; padding: 15px 20px; border-radius: 8px; border-left: 8px solid #00C875;'>
        <h2 style='margin:0; font-size:22px;'>Control de Cotizaciones</h2>
        <p style='margin:5px 0 0 0; color: #9ca3af; font-size:12px;'>DC Control S.A. de C.V. • Rol activo: {st.session_state.user_role}</p>
    </div>
    """, unsafe_allow_html=True)

# Definición de pestañas
role = st.session_state.user_role
if role == "Admin/Director":
    tabs_config = ["📊 Dashboard", "📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual", "👥 Usuarios y Seguridad", "📜 Bitácora Auditoría"]
else:
    tabs_config = ["📋 Tablero de Proyectos", "✔️ Compuertas Técnicas", "🗺️ Kanban Visual"]

tabs = st.tabs(tabs_config)
tab_dict = {name: tab_obj for name, tab_obj in zip(tabs_config, tabs)}

# ==========================================
# MÓDULO 1: DASHBOARD
# ==========================================
if "📊 Dashboard" in tab_dict:
    with tab_dict["📊 Dashboard"]:
        st.subheader("📊 Resumen General")
        
        conn = get_db_connection()
        total_p = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        monto_total = conn.execute("SELECT SUM(total_amount) FROM projects").fetchone()[0] or 0.0
        ganados_n = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'Ganado'").fetchone()[0]
        perdidos_n = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'Perdido'").fetchone()[0]
        projs_all = conn.execute("SELECT * FROM projects").fetchall()
        alertas_p = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'En Proceso'").fetchone()[0]
        conn.close()
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            st.metric("Licitaciones Totales", total_p)
        with col_k2:
            st.metric("Monto Total Cotizado", f"${monto_total:,.2f}")
        with col_k3:
            denom_exito = (ganados_n + perdidos_n)
            tasa_exito = (ganados_n / denom_exito * 100) if denom_exito > 0 else 0.0
            st.metric("Efectividad Comercial", f"{tasa_exito:.1f}%")
        with col_k4:
            st.metric("Cotizaciones en Curso", alertas_p)
            
        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        df_p = pd.DataFrame([dict(p) for p in projs_all]) if projs_all else pd.DataFrame()
        
        with col_g1:
            st.markdown("##### 📍 Monto por Región")
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
                fig_reg.update_layout(showlegend=False, height=280, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_reg, use_container_width=True)
            else:
                st.caption("Sin datos comerciales que mostrar")
                
        with col_g2:
            st.markdown("##### 📈 Estatus de Licitaciones")
            if not df_p.empty:
                fig_stat = px.pie(
                    df_p, 
                    names="status", 
                    color="status",
                    color_discrete_map={"En Proceso": "#f59e0b", "Ganado": "#10b981", "Perdido": "#ef4444", "Cancelado": "#6b7280"},
                    hole=0.4
                )
                fig_stat.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_stat, use_container_width=True)
            else:
                st.caption("Sin datos comerciales que mostrar")

# ==========================================
# MÓDULO 2: TABLERO DE PROYECTOS
# ==========================================
if "📋 Tablero de Proyectos" in tab_dict:
    with tab_dict["📋 Tablero de Proyectos"]:
        st.subheader("📋 Pipeline General de Proyectos")
        
        # Opciones de creación y borrado exclusivas para el Admin/Director
        if role == "Admin/Director":
            col_admin_actions = st.columns(2)
            with col_admin_actions[0]:
                with st.expander("➕ Crear Nuevo Registro de Licitación"):
                    with st.form("Add Project Form"):
                        p_name = st.text_input("Nombre de la Obra")
                        p_client = st.text_input("Cliente")
                        p_amount = st.number_input("Monto Estimado Inicial ($)", min_value=0.0, step=10000.0)
                        p_state = st.selectbox("Estado de la República", list(ESTADOS_MEXICO.keys()))
                        
                        # Cargar listas dinámicas de usuarios
                        conn = get_db_connection()
                        cost_users = [u['full_name'] for u in conn.execute("SELECT full_name FROM users WHERE role LIKE '%Costos%'").fetchall()]
                        sales_users = [u['full_name'] for u in conn.execute("SELECT full_name FROM users WHERE role = 'Ventas'").fetchall()]
                        conn.close()
                        
                        p_costos = st.selectbox("Analista de Costos Asignado", cost_users if cost_users else ["Lic. Roberto (Director de Costos)"])
                        p_ventas = st.selectbox("Agente de Ventas Responsable", sales_users if sales_users else ["Ing. Carlos"])
                        p_target = st.date_input("Fecha Compromiso de Entrega")
                        
                        # Mostrar el código inteligente que se generará
                        temp_code = generate_next_project_id(p_state)
                        st.info(f"**Código de cotización asignado:** {temp_code}")
                        
                        btn_add_proj = st.form_submit_button("Guardar en Pipeline 📂")
                        
                        if btn_add_proj:
                            if not p_name or not p_client:
                                st.error("Todos los campos obligatorios deben ser llenados.")
                            else:
                                final_code = generate_next_project_id(p_state)
                                region_auto = ESTADOS_MEXICO[p_state]
                                zone_auto = "Sur" if "Sur" in region_auto else "Norte"
                                
                                # Mapear líder automáticamente consultando la base de datos de usuarios para esa región
                                conn_lider = get_db_connection()
                                lider_db = conn_lider.execute("SELECT full_name FROM users WHERE role = ?", (region_auto,)).fetchone()
                                conn_lider.close()
                                
                                if lider_db:
                                    assigned_leader = lider_db['full_name']
                                else:
                                    assigned_leader = region_auto
                                
                                conn = get_db_connection()
                                try:
                                    conn.execute('''
                                        INSERT INTO projects (
                                            id, name, client, total_amount, final_amount, state, zone, 
                                            assigned_lider, assigned_costos, assigned_ventas, status, current_stage, 
                                            created_at, target_date
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        final_code, p_name, p_client, p_amount, p_amount, p_state, zone_auto,
                                        assigned_leader, p_costos, p_ventas, "En Proceso", 1,
                                        date.today().strftime("%Y-%m-%d"), p_target.strftime("%Y-%m-%d")
                                    ))
                                    conn.commit()
                                    log_audit(final_code, st.session_state.full_name, role, f"Creó licitación con código {final_code}")
                                    st.success(f"Proyecto {final_code} guardado con éxito.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al guardar: {e}")
                                finally:
                                    conn.close()
                                    
            with col_admin_actions[1]:
                with st.expander("🗑️ Modificar / Eliminar Registro"):
                    conn = get_db_connection()
                    all_p_db = conn.execute("SELECT * FROM projects").fetchall()
                    conn.close()
                    
                    if all_p_db:
                        p_to_del_label = st.selectbox("Seleccionar Proyecto para Operación", [f"{p['id']} - {p['name']}" for p in all_p_db])
                        sel_del_id = p_to_del_label.split(" - ")[0]
                        
                        confirm_del = st.checkbox("Confirmo que deseo ELIMINAR permanentemente esta cotización y todos sus documentos.", key="confirm_del_check")
                        if st.button("Eliminar permanentemente 🗑️", type="primary", disabled=not confirm_del):
                            conn = get_db_connection()
                            conn.execute("DELETE FROM projects WHERE id = ?", (sel_del_id,))
                            conn.execute("DELETE FROM tasks WHERE project_id = ?", (sel_del_id,))
                            
                            # Borrar archivos físicos
                            uploaded_files = conn.execute("SELECT file_path FROM uploads WHERE project_id = ?", (sel_del_id,)).fetchall()
                            for f in uploaded_files:
                                if f['file_path'] and os.path.exists(f['file_path']):
                                    try:
                                        os.remove(f['file_path'])
                                    except:
                                        pass
                            conn.execute("DELETE FROM uploads WHERE project_id = ?", (sel_del_id,))
                            conn.commit()
                            conn.close()
                            
                            log_audit(sel_del_id, st.session_state.full_name, role, "Eliminó licitación y todos sus archivos asociados.")
                            st.success(f"Proyecto {sel_del_id} eliminado.")
                            st.rerun()
                    else:
                        st.caption("No hay proyectos en base de datos")

        # Cargar y desplegar lista nativa de proyectos en Pipeline
        conn = get_db_connection()
        proyectos = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        if not proyectos:
            st.warning("No hay proyectos registrados en este momento.")
        else:
            df_projs = pd.DataFrame([dict(p) for p in proyectos])
            # Ensure all expected columns are present in df_projs
            expected_db_cols = ['id', 'name', 'client', 'total_amount', 'final_amount', 'state', 'zone', 'assigned_lider', 'assigned_costos', 'assigned_ventas', 'status', 'current_stage']
            for col in expected_db_cols:
                if col not in df_projs.columns:
                    df_projs[col] = 0.0 if col in ['total_amount', 'final_amount'] else None
            df_display = df_projs.rename(columns={
                'id': 'ID Proyecto',
                'name': 'Obra / Proyecto',
                'client': 'Cliente',
                'total_amount': 'Monto Inicial ($)',
                'final_amount': 'Monto Final ($)',
                'state': 'Estado',
                'zone': 'Zona',
                'assigned_lider': 'Líder Regional',
                'assigned_costos': 'Analista de Costos',
                'assigned_ventas': 'Agente de Ventas',
                'status': 'Estatus Comercial',
                'current_stage': 'Paso Actual'
            })
            
            # Map paso actual to descriptive text
            steps_desc = {
                1: "1. Levantamiento (Ventas)",
                2: "2. Minuta (Ventas & Líder)",
                3: "3. Catálogo Conceptos (Líder)",
                4: "4. Cotización (Costos)",
                5: "5. Revisión y Aprobación (Dirección)",
                6: "6. Entrega al Cliente (Ventas)",
                7: "7. Cierre Comercial (Dirección)"
            }
            df_display['Paso Actual'] = df_display['Paso Actual'].map(steps_desc)
            
            cols_order_display = ['ID Proyecto', 'Obra / Proyecto', 'Cliente', 'Monto Inicial ($)', 'Monto Final ($)', 'Estado', 'Zona', 'Agente de Ventas', 'Líder Regional', 'Analista de Costos', 'Paso Actual', 'Estatus Comercial']
            st.dataframe(
                df_display[cols_order_display],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Monto Inicial ($)": st.column_config.NumberColumn(format="$%,.2f"),
                    "Monto Final ($)": st.column_config.NumberColumn(format="$%,.2f"),
                }
            )

# ==========================================
# MÓDULO 3: COMPUERTAS TÉCNICAS (FLUJO SECUENCIAL)
# ==========================================
if "✔️ Compuertas Técnicas" in tab_dict:
    with tab_dict["✔️ Compuertas Técnicas"]:
        st.subheader("✔️ Seguimiento de Pasos de Cotización")
        st.write("Estructura secuencial obligatoria para cada proyecto. Complete cada tarea para desbloquear el paso siguiente:")
        
        conn = get_db_connection()
        projs = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        if not projs:
            st.info("No hay proyectos registrados para procesar.")
        else:
            # Selector de proyectos
            proj_dict = {f"{p['id']} - {p['name']}": p for p in projs}
            sel_proj_label = st.selectbox("📂 Seleccione la Obra / Proyecto", list(proj_dict.keys()), key="seq_proj_select")
            p = proj_dict[sel_proj_label]
            
            # Tarjetas informativas superiores
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            with col_met1:
                st.metric("Agente de Ventas", p['assigned_ventas'])
            with col_met2:
                st.metric("Líder Regional", p['assigned_lider'])
            with col_met3:
                st.metric("Analista de Costos", p['assigned_costos'])
            with col_met4:
                st.metric("Estatus Licitación", p['status'])
                
            st.markdown("---")
            
            # Renderizado de pestañas de flujo paso a paso
            step_tabs = st.tabs([
                "Paso 1: Levantamiento 📋",
                "Paso 2: Minuta Trabajo 🤝",
                "Paso 3: Catálogo Conceptos ⚙️",
                "Paso 4: Cotización 📊",
                "Paso 5: Revisión Dirección 🔑",
                "Paso 6: Entrega Cliente 🚚",
                "Paso 7: Cierre Comercial 🏁"
            ])
            
            # Helper: Consultar archivos adjuntos para un paso específico
            def get_step_files(proj_id, step_name):
                conn = get_db_connection()
                files = conn.execute("SELECT * FROM uploads WHERE project_id = ? AND step_name = ?", (proj_id, step_name)).fetchall()
                conn.close()
                return files
            
            # Helper: Desplegar interfaz de archivos con permisos de eliminación nativos
            def display_files_interface(proj_id, step_name, active_user, is_readonly=False):
                st.markdown("**📂 Documentación y Archivos Adjuntos**")
                files = get_step_files(proj_id, step_name)
                if not files:
                    st.caption("No se han cargado documentos en este paso.")
                else:
                    for f in files:
                        col_file_name, col_file_dl, col_file_del = st.columns([3, 1, 1])
                        with col_file_name:
                            st.write(f"📄 {f['filename']} (Subido por: {f['uploaded_by']})")
                        with col_file_dl:
                            # Descargar archivo
                            try:
                                with open(f['file_path'], "rb") as file_bytes:
                                    st.download_button(
                                        label="Descargar 📥",
                                        data=file_bytes.read(),
                                        file_name=f['filename'],
                                        key=f"dl_{f['id']}"
                                    )
                            except:
                                st.error("Archivo no encontrado")
                        with col_file_del:
                            # Eliminar archivo (Solo si es quien lo cargó o Admin, y no es visualizador)
                            if not is_readonly and (active_user == f['uploaded_by'] or role == "Admin/Director"):
                                if st.button("Quitar 🗑️", key=f"del_{f['id']}"):
                                    conn = get_db_connection()
                                    conn.execute("DELETE FROM uploads WHERE id = ?", (f['id'],))
                                    conn.commit()
                                    conn.close()
                                    if os.path.exists(f['file_path']):
                                        try:
                                            os.remove(f['file_path'])
                                        except:
                                            pass
                                    log_audit(proj_id, st.session_state.full_name, role, f"Eliminó archivo {f['filename']} del paso {step_name}")
                                    st.success("Archivo eliminado.")
                                    st.rerun()
                                    
            # Permiso lectura general
            is_readonly = (role == "Ingeniero")
            
            # ---------------------------------------------
            # PASO 1: LEVANTAMIENTO (Ventas)
            # ---------------------------------------------
            with step_tabs[0]:
                st.markdown("### Paso 1: Crear Levantamiento Técnico")
                st.write(f"**Asignado a:** Agente de Ventas - *{p['assigned_ventas']}*")
                
                # Desplegar Archivos
                display_files_interface(p['id'], "step1_levantamiento", st.session_state.user_name, is_readonly)
                
                # Cargar Archivo (Solo Ventas asignado o Admin)
                is_authorized_s1 = (st.session_state.full_name == p['assigned_ventas'] or role == "Admin/Director") and not is_readonly
                
                if p['step1_completed'] == 0:
                    st.info("Estatus: Esperando carga de levantamiento técnico por el agente de ventas.")
                    if is_authorized_s1:
                        uploaded_file_s1 = st.file_uploader("Cargar evidencia de levantamiento (PDF, Imagen, Word, etc.)", key="uploader_s1")
                        if uploaded_file_s1:
                            if st.button("Guardar Evidencia y Validar Paso ✔️", key="btn_s1"):
                                # Guardar en disco
                                file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s1_{uploaded_file_s1.name}")
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file_s1.getbuffer())
                                    
                                conn = get_db_connection()
                                conn.execute('''
                                    INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (p['id'], "step1_levantamiento", uploaded_file_s1.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                conn.execute("UPDATE projects SET step1_completed = 1, current_stage = 2 WHERE id = ?", (p['id'],))
                                conn.commit()
                                conn.close()
                                log_audit(p['id'], st.session_state.full_name, role, "Completó Paso 1: Carga de levantamiento")
                                st.success("Paso 1 completado con éxito. Paso 2 desbloqueado.")
                                st.rerun()
                else:
                    st.success("✔️ Paso 1 Completado: Evidencia de levantamiento cargada.")
                    if is_authorized_s1:
                        # Opción de re-subir archivos adicionales
                        uploaded_file_s1_extra = st.file_uploader("Cargar archivo adicional", key="uploader_s1_extra")
                        if uploaded_file_s1_extra:
                            if st.button("Subir archivo adicional", key="btn_s1_extra"):
                                file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s1_{datetime.now().strftime('%H%M%S')}_{uploaded_file_s1_extra.name}")
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file_s1_extra.getbuffer())
                                conn = get_db_connection()
                                conn.execute('''
                                    INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (p['id'], "step1_levantamiento", uploaded_file_s1_extra.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                conn.commit()
                                conn.close()
                                st.success("Archivo subido con éxito.")
                                st.rerun()

            # ---------------------------------------------
            # PASO 2: MINUTA TRABAJO (Ventas & Líder)
            # ---------------------------------------------
            with step_tabs[1]:
                st.markdown("### Paso 2: Reunión de Seguimiento y Minuta de Trabajo")
                st.write(f"**Ventas Responsable:** {p['assigned_ventas']}")
                st.write(f"**Líder Regional Responsable:** {p['assigned_lider']}")
                
                display_files_interface(p['id'], "step2_minuta", st.session_state.user_name, is_readonly)
                
                # Validar si el paso previo está completado
                if p['step1_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 1 para poder acceder.")
                else:
                    is_ventas = (st.session_state.full_name == p['assigned_ventas'] or role == "Admin/Director") and not is_readonly
                    is_lider = (st.session_state.full_name == p['assigned_lider'] or st.session_state.user_role == p['assigned_lider'] or role == "Admin/Director") and not is_readonly
                    
                    st.markdown("##### ☑️ Confirmación de Reunión Realizada (Doble Check Obligatorio)")
                    col_chk1, col_col2 = st.columns(2)
                    with col_chk1:
                        # Check de ventas
                        chk_v = st.checkbox("Ventas: Reunión hecha", value=(p['step2_ventas_done'] == 1), disabled=not is_ventas, key="chk_v_s2")
                        if chk_v != (p['step2_ventas_done'] == 1):
                            conn = get_db_connection()
                            conn.execute("UPDATE projects SET step2_ventas_done = ? WHERE id = ?", (1 if chk_v else 0, p['id']))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with col_col2:
                        # Check de líder
                        chk_l = st.checkbox("Líder Regional: Reunión hecha", value=(p['step2_lider_done'] == 1), disabled=not is_lider, key="chk_l_s2")
                        if chk_l != (p['step2_lider_done'] == 1):
                            conn = get_db_connection()
                            conn.execute("UPDATE projects SET step2_lider_done = ? WHERE id = ?", (1 if chk_l else 0, p['id']))
                            conn.commit()
                            conn.close()
                            st.rerun()
                            
                    # Carga de minuta
                    if p['step2_completed'] == 0:
                        if p['step2_ventas_done'] == 1 and p['step2_lider_done'] == 1:
                            st.info("Ambas partes han confirmado la reunión. Proceda a cargar la minuta de trabajo firmada para validar la compuerta:")
                            if is_ventas or is_lider:
                                uploaded_file_s2 = st.file_uploader("Cargar archivo de minuta de trabajo", key="uploader_s2")
                                if uploaded_file_s2:
                                    if st.button("Guardar Minuta y Validar Paso ✔️", key="btn_s2"):
                                        file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s2_{uploaded_file_s2.name}")
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file_s2.getbuffer())
                                            
                                        conn = get_db_connection()
                                        conn.execute('''
                                            INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        ''', (p['id'], "step2_minuta", uploaded_file_s2.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                        conn.execute("UPDATE projects SET step2_completed = 1, current_stage = 3 WHERE id = ?", (p['id'],))
                                        conn.commit()
                                        conn.close()
                                        log_audit(p['id'], st.session_state.full_name, role, "Completó Paso 2: Carga de minuta de trabajo")
                                        st.success("Paso 2 completado. Paso 3 desbloqueado.")
                                        st.rerun()
                        else:
                            st.warning("Esperando confirmación doble de 'Reunión hecha' por parte del Agente de Ventas y el Líder Regional para habilitar la carga de documentos.")
                    else:
                        st.success("✔️ Paso 2 Completado: Minuta cargada y validada por ambas partes.")
                        if is_ventas or is_lider:
                            uploaded_file_s2_extra = st.file_uploader("Cargar archivo de minuta adicional", key="uploader_s2_extra")
                            if uploaded_file_s2_extra:
                                if st.button("Subir minuta adicional", key="btn_s2_extra"):
                                    file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s2_{datetime.now().strftime('%H%M%S')}_{uploaded_file_s2_extra.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file_s2_extra.getbuffer())
                                    conn = get_db_connection()
                                    conn.execute('''
                                        INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (p['id'], "step2_minuta", uploaded_file_s2_extra.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                    conn.commit()
                                    conn.close()
                                    st.success("Archivo subido con éxito.")
                                    st.rerun()

            # ---------------------------------------------
            # PASO 3: CATÁLOGO CONCEPTOS (Líder)
            # ---------------------------------------------
            with step_tabs[2]:
                st.markdown("### Paso 3: Catálogo de Conceptos Técnico")
                st.write(f"**Asignado a:** Líder Regional - *{p['assigned_lider']}*")
                
                display_files_interface(p['id'], "step3_catalogo", st.session_state.user_name, is_readonly)
                
                if p['step2_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 2 para poder acceder.")
                else:
                    is_authorized_s3 = (st.session_state.full_name == p['assigned_lider'] or st.session_state.user_role == p['assigned_lider'] or role == "Admin/Director") and not is_readonly
                    
                    if p['step3_completed'] == 0:
                        st.info("Estatus: Esperando catálogo de conceptos técnico por el Líder Regional.")
                        if is_authorized_s3:
                            uploaded_file_s3 = st.file_uploader("Cargar Catálogo de Conceptos (Excel, PDF)", key="uploader_s3")
                            if uploaded_file_s3:
                                if st.button("Guardar Catálogo y Validar Paso ✔️", key="btn_s3"):
                                    file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s3_{uploaded_file_s3.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file_s3.getbuffer())
                                        
                                    conn = get_db_connection()
                                    conn.execute('''
                                        INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (p['id'], "step3_catalogo", uploaded_file_s3.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                    conn.execute("UPDATE projects SET step3_completed = 1, current_stage = 4 WHERE id = ?", (p['id'],))
                                    conn.commit()
                                    conn.close()
                                    log_audit(p['id'], st.session_state.full_name, role, "Completó Paso 3: Carga de catálogo de conceptos")
                                    st.success("Paso 3 completado. Paso 4 desbloqueado.")
                                    st.rerun()
                    else:
                        st.success("✔️ Paso 3 Completado: Catálogo de conceptos técnico cargado.")
                        if is_authorized_s3:
                            uploaded_file_s3_extra = st.file_uploader("Cargar archivo técnico adicional", key="uploader_s3_extra")
                            if uploaded_file_s3_extra:
                                if st.button("Subir archivo adicional", key="btn_s3_extra"):
                                    file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s3_{datetime.now().strftime('%H%M%S')}_{uploaded_file_s3_extra.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file_s3_extra.getbuffer())
                                    conn = get_db_connection()
                                    conn.execute('''
                                        INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (p['id'], "step3_catalogo", uploaded_file_s3_extra.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                    conn.commit()
                                    conn.close()
                                    st.success("Archivo subido con éxito.")
                                    st.rerun()

            # ---------------------------------------------
            # PASO 4: COTIZACIÓN (Costos)
            # ---------------------------------------------
            with step_tabs[3]:
                st.markdown("### Paso 4: Elaboración de Cotización de Precios")
                st.write(f"**Asignado a:** Analista de Costos - *{p['assigned_costos']}*")
                
                display_files_interface(p['id'], "step4_cotizacion", st.session_state.user_name, is_readonly)
                
                if p['step3_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 3 para poder acceder.")
                else:
                    is_authorized_s4 = (st.session_state.full_name == p['assigned_costos'] or st.session_state.user_role == p['assigned_costos'] or role == "Admin/Director") and not is_readonly
                    
                    # El analista de costos ve el catálogo y puede validarlo con checks interactivos nativos
                    st.markdown("##### 📝 Verificación de Conceptos Técnicos")
                    chk_c1 = st.checkbox("Conceptos alineados con catálogo", key="chk_c1", disabled=not is_authorized_s4)
                    chk_c2 = st.checkbox("Análisis de precios unitarios formulado", key="chk_c2", disabled=not is_authorized_s4)
                    chk_c3 = st.checkbox("Márgenes comerciales integrados", key="chk_c3", disabled=not is_authorized_s4)
                    
                    if p['step4_completed'] == 0:
                        if is_authorized_s4:
                            st.markdown("##### 📤 Cargar Cotización de Precios")
                            uploaded_file_s4 = st.file_uploader("Cargar cotización final de precios", key="uploader_s4")
                            
                            # Validar que los checks se marquen antes de completar
                            if uploaded_file_s4:
                                if chk_c1 and chk_c2 and chk_c3:
                                    if st.button("Cargar Cotización y Validar Paso ✔️", key="btn_s4"):
                                        file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s4_{uploaded_file_s4.name}")
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file_s4.getbuffer())
                                            
                                        conn = get_db_connection()
                                        conn.execute('''
                                            INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        ''', (p['id'], "step4_cotizacion", uploaded_file_s4.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                        conn.execute("UPDATE projects SET step4_completed = 1, current_stage = 5 WHERE id = ?", (p['id'],))
                                        conn.commit()
                                        conn.close()
                                        log_audit(p['id'], st.session_state.full_name, role, "Completó Paso 4: Elaboró y cargó cotización")
                                        st.success("Paso 4 completado con éxito. Paso 5 desbloqueado para revisión de dirección.")
                                        st.rerun()
                                else:
                                    st.warning("Debe marcar las 3 casillas de verificación técnica para poder validar y guardar la cotización.")
                    else:
                        st.success("✔️ Paso 4 Completado: Cotización final cargada y verificada.")
                        if is_authorized_s4:
                            uploaded_file_s4_extra = st.file_uploader("Cargar archivo de cotización adicional", key="uploader_s4_extra")
                            if uploaded_file_s4_extra:
                                if st.button("Subir cotización adicional", key="btn_s4_extra"):
                                    file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s4_{datetime.now().strftime('%H%M%S')}_{uploaded_file_s4_extra.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file_s4_extra.getbuffer())
                                    conn = get_db_connection()
                                    conn.execute('''
                                        INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (p['id'], "step4_cotizacion", uploaded_file_s4_extra.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                    conn.commit()
                                    conn.close()
                                    st.success("Archivo subido con éxito.")
                                    st.rerun()

            # ---------------------------------------------
            # PASO 5: REVISIÓN DIRECCIÓN (Admin / Director)
            # ---------------------------------------------
            with step_tabs[4]:
                st.markdown("### Paso 5: Revisión de Cotización y Aprobación de Costos")
                st.write("**Asignado a:** Dirección General / Administrador")
                
                if p['step4_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 4 para poder acceder.")
                else:
                    is_authorized_s5 = (role == "Admin/Director") and not is_readonly
                    
                    # Director puede ver y descargar los archivos cargados por el analista
                    st.markdown("##### 📥 Descargar Licitación Propuesta")
                    files_proposal = get_step_files(p['id'], "step4_cotizacion")
                    if not files_proposal:
                        st.caption("No hay propuesta cargada.")
                    else:
                        for f in files_proposal:
                            try:
                                with open(f['file_path'], "rb") as file_bytes:
                                    st.download_button(
                                        label=f"Descargar Propuesta: {f['filename']} 📥",
                                        data=file_bytes.read(),
                                        file_name=f['filename'],
                                        key=f"proposal_dl_{f['id']}"
                                    )
                            except:
                                pass
                                
                    st.markdown("---")
                    
                    if p['step5_completed'] == 0:
                        if is_authorized_s5:
                            st.write("Revise a detalle la cotización propuesta en costo, alcance y margen. Si es correcta, confirme y firme electrónicamente:")
                            chk_rev1 = st.checkbox("Cotización revisada en costo y alcance", key="chk_rev1")
                            chk_rev2 = st.checkbox("Márgenes comerciales validados", key="chk_rev2")
                            
                            if chk_rev1 and chk_rev2:
                                if st.button("Aprobar Cotización ✔️", key="btn_s5", type="primary"):
                                    conn = get_db_connection()
                                    conn.execute("UPDATE projects SET step5_completed = 1, current_stage = 6 WHERE id = ?", (p['id'],))
                                    conn.commit()
                                    conn.close()
                                    log_audit(p['id'], st.session_state.full_name, role, "Aprobó y autorizó cotización")
                                    st.success("Cotización aprobada por Dirección con éxito. Paso 6 asignado para entrega comercial.")
                                    st.rerun()
                            else:
                                st.warning("Marque las casillas de verificación de costos para habilitar el botón de aprobación oficial.")
                        else:
                            st.info("Estatus: Esperando revisión y firma del Director General.")
                    else:
                        st.success("✔️ Paso 5 Completado: Cotización aprobada oficialmente por Dirección.")

            # ---------------------------------------------
            # PASO 6: ENTREGA CLIENTE (Ventas)
            # ---------------------------------------------
            with step_tabs[5]:
                st.markdown("### Paso 6: Entrega de Cotización al Cliente")
                st.write(f"**Asignado a:** Agente de Ventas - *{p['assigned_ventas']}*")
                
                display_files_interface(p['id'], "step6_entrega", st.session_state.user_name, is_readonly)
                
                if p['step5_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 5 para poder acceder.")
                else:
                    is_authorized_s6 = (st.session_state.full_name == p['assigned_ventas'] or st.session_state.user_role == p['assigned_ventas'] or role == "Admin/Director") and not is_readonly
                    
                    if p['step6_completed'] == 0:
                        st.info("Estatus: Esperando entrega formal al cliente y registro de comentarios finales.")
                        if is_authorized_s6:
                            with st.form("Entrega Cliente Form"):
                                final_val = st.number_input("Monto final en el que se entregó la cotización ($)", min_value=0.0, value=p['total_amount'], step=1000.0)
                                comments_s6 = st.text_area("Comentarios de entrega y observaciones del cliente")
                                chk_delivered = st.checkbox("Confirmo que la cotización ha sido entregada de forma oficial al cliente.")
                                
                                uploaded_evidence_s6 = st.file_uploader("Cargar acuse o evidencia de entrega (Opcional)", key="uploader_s6")
                                
                                btn_s6 = st.form_submit_button("Guardar Datos de Entrega ✔️")
                                if btn_s6:
                                    if not chk_delivered:
                                        st.error("Debe marcar la casilla de confirmación de entrega.")
                                    else:
                                        # Guardar evidencia si existe
                                        file_path = ""
                                        if uploaded_evidence_s6:
                                            file_path = os.path.join(UPLOAD_DIR, f"{p['id']}_s6_{uploaded_evidence_s6.name}")
                                            with open(file_path, "wb") as f:
                                                f.write(uploaded_evidence_s6.getbuffer())
                                                
                                        conn = get_db_connection()
                                        if file_path:
                                            conn.execute('''
                                                INSERT INTO uploads (project_id, step_name, filename, file_path, uploaded_by, uploaded_at)
                                                VALUES (?, ?, ?, ?, ?, ?)
                                            ''', (p['id'], "step6_entrega", uploaded_evidence_s6.name, file_path, st.session_state.user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                            
                                        conn.execute('''
                                            UPDATE projects 
                                            SET final_amount = ?, step6_completed = 1, current_stage = 7, lose_reason = ?
                                            WHERE id = ?
                                        ''', (final_val, comments_s6, p['id']))
                                        conn.commit()
                                        conn.close()
                                        log_audit(p['id'], st.session_state.full_name, role, f"Completó entrega de cotización por monto final ${final_val:,.2f}")
                                        st.success("Datos de entrega guardados. Paso 7 habilitado para cierre de proyecto.")
                                        st.rerun()
                    else:
                        st.success("✔️ Paso 6 Completado: Cotización entregada al cliente.")
                        st.write(f"**Monto final de entrega:** ${p['final_amount']:,.2f}")
                        st.write(f"**Observaciones:** {p['lose_reason'] or 'Sin comentarios registrados'}")

            # ---------------------------------------------
            # PASO 7: CIERRE COMERCIAL (Admin / Director)
            # ---------------------------------------------
            with step_tabs[6]:
                st.markdown("### Paso 7: Cierre Comercial de Licitación")
                st.write("**Asignado a:** Dirección General / Administrador")
                
                if p['step6_completed'] == 0:
                    st.warning("🔒 Este paso se encuentra bloqueado. Complete el Paso 6 para poder acceder.")
                else:
                    is_authorized_s7 = (role == "Admin/Director") and not is_readonly
                    
                    if p['status'] == "En Proceso":
                        if is_authorized_s7:
                            st.write("Especifique el resultado de la licitación comercial:")
                            with st.form("Cierre Licitación Form"):
                                final_res = st.selectbox("Estatus Final", ["Ganado", "Perdido", "Cancelado"])
                                gap_p = st.number_input("Porcentaje de Desfase de Precio / Margen (%)", min_value=0.0, step=1.0)
                                reason_close = st.text_area("Razón o motivo del resultado (¿Por qué se ganó o perdió?)")
                                
                                btn_s7 = st.form_submit_button("Proceder con el Cierre Oficial 🏁")
                                if btn_s7:
                                    conn = get_db_connection()
                                    conn.execute('''
                                        UPDATE projects 
                                        SET status = ?, lose_percentage_gap = ?, lose_reason = ?
                                        WHERE id = ?
                                    ''', (final_res, gap_p, reason_close, p['id']))
                                    conn.commit()
                                    conn.close()
                                    log_audit(p['id'], st.session_state.full_name, role, f"Cerró licitación comercial como '{final_res}'")
                                    st.success(f"Licitación cerrada oficialmente como '{final_res}'.")
                                    st.rerun()
                        else:
                            st.info("Estatus: Esperando cierre comercial definitivo por el Director General.")
                    else:
                        st.success(f"🏁 Licitación Cerrada: **{p['status'].upper()}**")
                        st.write(f"**Motivos:** {p['lose_reason'] or 'No especificado'}")
                        st.write(f"**Desfase de Costo:** {p['lose_percentage_gap']}%")

# ==========================================
# MÓDULO 4: KANBAN VISUAL
# ==========================================
if "🗺️ Kanban Visual" in tab_dict:
    with tab_dict["🗺️ Kanban Visual"]:
        st.subheader("🗺️ Tablero Comercial de Cotizaciones")
        
        conn = get_db_connection()
        projects_k = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        col_kp, col_kg, col_kd = st.columns(3)
        
        # Helper: Renderizar tarjetas Kanban con archivos descargables integrados
        def render_kanban_card(p):
            with st.container(border=True):
                st.markdown(f"**{p['id']} - {p['name']}**")
                st.write(f"💼 **Cliente:** {p['client']}")
                st.write(f"💰 **Monto Cotizado:** ${p['total_amount']:,.2f}")
                
                # Paso actual descriptivo
                steps_desc = {
                    1: "Paso 1: Levantamiento (Ventas)",
                    2: "Paso 2: Minuta Trabajo (Ventas & Líder)",
                    3: "Paso 3: Catálogo Conceptos (Líder)",
                    4: "Paso 4: Cotización (Costos)",
                    5: "Paso 5: Revisión Dirección (Admin/Director)",
                    6: "Paso 6: Entrega Cliente (Ventas)",
                    7: "Paso 7: Cierre Comercial (Admin/Director)"
                }
                current_step_name = steps_desc.get(p['current_stage'], "Completado")
                st.write(f"📋 **Estatus Actual:** {current_step_name}")
                
                # Barra de avance según el paso actual
                progress_val = p['current_stage'] / 7.0
                st.progress(progress_val)
                st.caption(f"Avance: Paso {p['current_stage']} de 7")
                
                # Archivos para este proyecto
                conn = get_db_connection()
                files_proj = conn.execute("SELECT * FROM uploads WHERE project_id = ?", (p['id'],)).fetchall()
                conn.close()
                
                if files_proj:
                    st.markdown("**📂 Documentos Disponibles:**")
                    for f in files_proj:
                        try:
                            with open(f['file_path'], "rb") as file_bytes:
                                st.download_button(
                                    label=f"📥 {f['filename']}",
                                    data=file_bytes.read(),
                                    file_name=f['filename'],
                                    key=f"kanban_dl_{p['id']}_{f['id']}"
                                )
                        except:
                            st.caption(f"⚠️ {f['filename']} (Error)")
                else:
                    st.caption("Sin documentos cargados.")
        
        with col_kp:
            st.info("⏳ EN PROCESO")
            for p in projects_k:
                if p['status'] == "En Proceso":
                    render_kanban_card(p)
                        
        with col_kg:
            st.success("✔️ GANADOS")
            for p in projects_k:
                if p['status'] == "Ganado":
                    render_kanban_card(p)
                        
        with col_kd:
            st.error("🚨 PERDIDOS / CANCELADOS")
            for p in projects_k:
                if p['status'] in ["Perdido", "Cancelado"]:
                    render_kanban_card(p)

# ==========================================
# MÓDULO 5: USUARIOS Y SEGURIDAD (Exclusivo Admin)
# ==========================================
if "👥 Usuarios y Seguridad" in tab_dict:
    with tab_dict["👥 Usuarios y Seguridad"]:
        st.subheader("👥 Configuración de Usuarios e Involucrados")
        
        # --- SECCIÓN EDITAR MI PERFIL (PROGRESIVO CON CLAVE 1604) ---
        st.markdown("##### 📝 Mis Datos de Perfil")
        conn_p = get_db_connection()
        curr_user = conn_p.execute("SELECT * FROM users WHERE username = ?", (st.session_state.user_name,)).fetchone()
        conn_p.close()
        
        if curr_user:
            with st.expander("📝 Editar mi información (Nombre, Correo, Contraseña de Acceso)", expanded=False):
                with st.form("Edit My Profile Form"):
                    new_full_name = st.text_input("Mi Nombre Completo", value=curr_user['full_name'])
                    new_email = st.text_input("Mi Correo de Notificaciones", value=curr_user['email'] or "")
                    new_pass_val = st.text_input("Nueva Contraseña de Acceso (Opcional, dejar en blanco para no cambiar)", type="password")
                    
                    st.markdown("🔒 **Para autorizar y guardar estos cambios, ingresa la clave de seguridad:**")
                    security_key = st.text_input("Clave de Seguridad", type="password", key="sec_key_prof")
                    
                    btn_save_p = st.form_submit_button("Guardar Cambios 💾")
                    if btn_save_p:
                        if security_key != "1604":
                            st.error("❌ Clave de seguridad incorrecta. No se guardaron los cambios.")
                        elif not new_full_name or not new_email:
                            st.error("❌ El nombre y el correo electrónico son obligatorios.")
                        else:
                            conn_up_p = get_db_connection()
                            if new_pass_val.strip():
                                conn_up_p.execute("""
                                    UPDATE users 
                                    SET full_name = ?, email = ?, password = ? 
                                    WHERE username = ?
                                """, (new_full_name, new_email, new_pass_val.strip(), st.session_state.user_name))
                            else:
                                conn_up_p.execute("""
                                    UPDATE users 
                                    SET full_name = ?, email = ? 
                                    WHERE username = ?
                                """, (new_full_name, new_email, st.session_state.user_name))
                            conn_up_p.commit()
                            conn_up_p.close()
                            
                            st.session_state.full_name = new_full_name
                            # Indicar que se debe limpiar el pin en el siguiente rerun (antes de instanciar el widget)
                            st.session_state['clear_profile_pin'] = True
                            log_audit("SISTEMA", st.session_state.user_name, role, f"Actualizó datos de su perfil de usuario ({st.session_state.user_name})")
                            st.success("🎉 ¡Cambios guardados con éxito en tu perfil!")
                            st.rerun()
                            
        st.markdown("---")
        
        # Mostrar Directorio de Usuarios de forma ejecutiva como Tarjetas Nativas
        st.markdown("##### Directorio Oficial de DC Control")
        
        conn = get_db_connection()
        users_list = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        
        for u in users_list:
            # Crear contenedor limpio para cada usuario
            with st.container(border=True):
                col_u_info, col_u_action = st.columns([4, 1])
                with col_u_info:
                    st.markdown(f"#### {u['full_name']} (`{u['username']}`)")
                    st.write(f"💼 **Puesto:** {u['role']}")
                    st.write(f"📧 **Correo Electrónico:** {u['email'] or 'No registrado'}")
                with col_u_action:
                    # Botón de eliminar (Sólo Admin/Director puede usarlo, no se puede eliminar a sí mismo ni a admin principal)
                    if role == "Admin/Director" and u['username'] != st.session_state.user_name and u['username'] != 'noe.ortizadm':
                        if st.button("Quitar 🗑️", key=f"del_user_{u['username']}"):
                            conn = get_db_connection()
                            conn.execute("DELETE FROM users WHERE username = ?", (u['username'],))
                            conn.commit()
                            conn.close()
                            log_audit("SISTEMA", st.session_state.full_name, role, f"Eliminó cuenta de usuario: {u['username']}")
                            st.success(f"Usuario {u['username']} eliminado.")
                            st.rerun()
                            
        st.markdown("---")
        
        # Registrar nuevo usuario (Solo Admin)
        if role == "Admin/Director":
            with st.expander("➕ Registrar Nuevo Colaborador"):
                with st.form("Add User Form"):
                    nu_user = st.text_input("Usuario (Login)")
                    nu_pass = st.text_input("Contraseña", type="password")
                    nu_name = st.text_input("Nombre Completo")
                    nu_email = st.text_input("Correo Electrónico Individual")
                    nu_role = st.selectbox("Puesto / Rol", [
                        "Ventas",
                        "Líder Regional - Sur",
                        "Líder Regional - Norte",
                        "Analista de Costos Jefe",
                        "Analista de Costos Junior 1",
                        "Analista de Costos Junior 2",
                        "Ingeniero"
                    ])
                    
                    btn_nu = st.form_submit_button("Crear Cuenta")
                    if btn_nu:
                        if not nu_user or not nu_pass or not nu_name or not nu_email:
                            st.error("Todos los campos de registro son obligatorios.")
                        else:
                            conn = get_db_connection()
                            try:
                                conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (nu_user, nu_pass, nu_name, nu_role, nu_email))
                                conn.commit()
                                log_audit("SISTEMA", st.session_state.full_name, role, f"Creó nuevo usuario: {nu_user}")
                                st.success(f"Usuario {nu_user} creado con éxito.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("El nombre de usuario ingresado ya se encuentra registrado.")
                            finally:
                                conn.close()
                                
            # --- MANTENIMIENTO: RESTABLECIMIENTO TOTAL ---
            st.markdown("##### ⚙️ Mantenimiento de la Base de Datos")
            with st.expander("🚨 Restablecer Base de Datos a Cero"):
                st.warning("Esta acción borrará de manera definitiva todos los proyectos, archivos cargados en el disco, registros de auditoría y base de datos. Las cuentas de usuario y contraseñas permanecerán seguras.")
                confirm_reset = st.checkbox("Entiendo los efectos y confirmo que deseo limpiar a cero toda la base de datos.")
                
                if st.button("Restablecer Base de Datos ⚠️", type="primary", disabled=not confirm_reset):
                    try:
                        conn_res = get_db_connection()
                        cursor_res = conn_res.cursor()
                        cursor_res.execute("DROP TABLE IF EXISTS projects")
                        cursor_res.execute("DROP TABLE IF EXISTS tasks")
                        cursor_res.execute("DROP TABLE IF EXISTS audit_log")
                        cursor_res.execute("DROP TABLE IF EXISTS uploads")
                        conn_res.commit()
                        conn_res.close()
                        
                        # Limpiar archivos de uploads
                        if os.path.exists(UPLOAD_DIR):
                            shutil.rmtree(UPLOAD_DIR)
                            os.makedirs(UPLOAD_DIR)
                            
                        # Recrear estructura vacía
                        init_db(insert_demos=False)
                        
                        st.success("¡Base de datos restablecida a cero de manera exitosa!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al restablecer: {e}")

# ==========================================
# MÓDULO 6: BITÁCORA DE AUDITORÍA (Solo Admin)
# ==========================================
if "📜 Bitácora Auditoría" in tab_dict:
    with tab_dict["📜 Bitácora Auditoría"]:
        st.subheader("📜 Bitácora de Trazabilidad")
        st.write("Registro histórico de acciones realizadas en la base de datos:")
        
        conn = get_db_connection()
        logs = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
        conn.close()
        
        if not logs:
            st.info("No se han registrado acciones comerciales ni técnicas de momento.")
        else:
            df_logs = pd.DataFrame([dict(l) for l in logs])
            df_logs_display = df_logs.rename(columns={
                'project_id': 'ID Proyecto',
                'user_name': 'Usuario Responsable',
                'role': 'Puesto / Rol',
                'action': 'Acción Realizada',
                'timestamp': 'Fecha y Hora'
            })[['ID Proyecto', 'Usuario Responsable', 'Puesto / Rol', 'Acción Realizada', 'Fecha y Hora']]
            
            st.dataframe(df_logs_display, use_container_width=True, hide_index=True)

# Footer Corporativo
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #9ca3af; font-size: 11px;'> "
    "DC Control S.A. de C.V. • Control de Cotizaciones"
    "</p>", 
    unsafe_allow_html=True
)
