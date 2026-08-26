import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración de la página
st.set_page_config(
    page_title="DC Control - Sistema de Trazabilidad Súper-Gobernado v17",
    layout="wide",
    page_icon="🏗️"
)

DB_FILE = "pipeline_cotizaciones.db"

# Diccionario de Mapeo de Estados de México a Líderes Regionales
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
    "Ingeniero": "ingenieria@dccontrol.com"
}

def escape_xml_chars(text):
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def obtener_nombre_asignado(role_name):
    # Retorna el nombre del responsable asociado al rol
    conn = get_db_connection()
    user = conn.execute("SELECT full_name FROM users WHERE role = ?", (role_name,)).fetchone()
    conn.close()
    if user:
        return user['full_name']
    return "Sin Asignar"

# ==========================================
# GENERADOR DE REPORTE EJECUTIVO PDF
# ==========================================
def generar_pdf_reporte_ejecutivo(db_path, output_pdf_path=None):
    import io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, NextPageTemplate, PageBreak, Image, Flowable
    )
    
    # 1. Query Database to get projects and tasks
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects")
    projs = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT t.*, p.name as project_name FROM tasks t LEFT JOIN projects p ON t.project_id = p.id")
    tasks = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    pdf_buffer = io.BytesIO()
    doc = BaseDocTemplate(
        output_pdf_path if output_pdf_path else pdf_buffer,
        pagesize=LETTER,
        leftMargin=54, rightMargin=54,
        topMargin=54 + 14, bottomMargin=54,
    )
    
    content_frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        612 - 2*54, 792 - doc.topMargin - doc.bottomMargin,
        id='main'
    )
    
    COLS = {
        'heading':    HexColor('#1e3a8a'), # Dark Navy
        'body':       HexColor('#2c3e50'), # Charcoal
        'accent':     HexColor('#f39c12'), # Amber/Orange
        'muted':      HexColor('#7f8c8d'), # Muted Gray
        'bg_alt':     HexColor('#fafbfc'), # Very light tint
        'bg_header':  HexColor('#1e3a8a'), # Dark Navy
        'white':      HexColor('#ffffff'),
    }
    
    class SectionDivider(Flowable):
        def __init__(self, width, colors):
            Flowable.__init__(self)
            self._width = width
            self.colors = colors
            self._height = 20

        def wrap(self, availWidth, availHeight):
            return self._width, self._height

        def draw(self):
            y = self._height / 2
            self.canv.setStrokeColor(self.colors['accent'])
            self.canv.setLineWidth(1.5)
            self.canv.line(0, y, self._width * 0.3, y)
            
    def page_title_cb(canvas, doc_obj):
        canvas.saveState()
        canvas.setFillColor(COLS['heading'])
        canvas.rect(0, 792 - 180, 612, 180, fill=1, stroke=0)

        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(COLS['accent'])
        label = "   ".join("REPORTE EJECUTIVO DE CONTROL Y TRAZABILIDAD".upper())
        canvas.drawCentredString(612 / 2, 792 - 60, label)

        canvas.setFont('Helvetica-Bold', 22)
        canvas.setFillColor(COLS['white'])
        canvas.drawCentredString(612 / 2, 792 - 110, "DC CONTROL - INFORME GLOBAL")

        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(COLS['white'])
        canvas.drawCentredString(612 / 2, 792 - 145, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.restoreState()
        
    def page_later_cb(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(COLS['accent'])
        canvas.setLineWidth(1)
        canvas.line(54, 792 - 54 + 6, 612 - 54, 792 - 54 + 6)

        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(COLS['muted'])
        canvas.drawString(54, 792 - 54 + 10, "DC CONTROL - REPORTE EJECUTIVO GLOBAL")
        canvas.drawRightString(612 - 54, 792 - 54 + 10, datetime.now().strftime("%Y-%m-%d"))

        # Footer
        canvas.setStrokeColor(COLS['bg_alt'])
        canvas.setLineWidth(0.5)
        canvas.line(54, 54 - 10, 612 - 54, 54 - 10)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(COLS['muted'])
        canvas.drawCentredString(612 / 2, 54 - 24, f"Página {doc_obj.page}")
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id='title_page', frames=content_frame, onPage=page_title_cb),
        PageTemplate(id='content', frames=content_frame, onPage=page_later_cb),
    ])
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'H1_Custom', fontName='Helvetica-Bold', fontSize=14,
        textColor=COLS['heading'], leading=18,
        spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'H2_Custom', fontName='Helvetica-Bold', fontSize=11,
        textColor=COLS['heading'], leading=14,
        spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'Body_Custom', fontName='Helvetica', fontSize=9.5,
        textColor=COLS['body'], leading=13.5,
        spaceAfter=6, alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        'TableHead', fontName='Helvetica-Bold', fontSize=8,
        textColor=COLS['white'], leading=10,
    ))
    styles.add(ParagraphStyle(
        'TableBody', fontName='Helvetica', fontSize=8,
        textColor=COLS['body'], leading=10,
    ))
    styles.add(ParagraphStyle(
        'Caption_Custom', fontName='Helvetica', fontSize=8,
        textColor=COLS['muted'], leading=10,
        alignment=TA_CENTER,
    ))
    
    story = []
    
    # ── Page 1: Resumen Ejecutivo ─────────────────────────────────
    story.append(Spacer(1, 150))
    story.append(Paragraph("1. RESUMEN EJECUTIVO Y ANÁLISIS DE EFECTIVIDAD", styles['H1_Custom']))
    story.append(SectionDivider(612 - 2*54, COLS))
    story.append(Spacer(1, 8))
    
    df_proj = pd.DataFrame(projs) if projs else pd.DataFrame()
    if not df_proj.empty:
        total_monto = df_proj['total_amount'].sum()
        ganados = df_proj[df_proj['status'] == 'Ganado']
        perdidos = df_proj[df_proj['status'] == 'Perdido']
        activos = df_proj[df_proj['status'] == 'Activo']
        
        monto_ganado = ganados['total_amount'].sum()
        monto_perdido = perdidos['total_amount'].sum()
        monto_activo = activos['total_amount'].sum()
        
        rate = (len(ganados) / (len(ganados) + len(perdidos)) * 100) if (len(ganados) + len(perdidos)) > 0 else 0
        
        # Calcular porcentaje de desfase promedio
        perdidos_con_desfase = perdidos[perdidos['lose_percentage_gap'] > 0]
        avg_desfase = perdidos_con_desfase['lose_percentage_gap'].mean() if not perdidos_con_desfase.empty else 0
        
        summary_text = (
            f"El presente reporte ejecutivo consolida la información comercial y de trazabilidad "
            f"operativa de <b>DC CONTROL</b> al día de hoy. Actualmente, el portafolio cuenta con un "
            f"monto total cotizado de <b>${total_monto:,.2f}</b>, distribuidos en <b>{len(df_proj)}</b> proyectos históricos. "
            f"La tasa de efectividad comercial de la empresa se sitúa en un <b>{rate:.1f}%</b>, con un total de "
            f"<b>{len(ganados)}</b> obras ganadas (cartera de <b>${monto_ganado:,.2f}</b>) y <b>{len(perdidos)}</b> obras "
            f"perdidas (monto de <b>${monto_perdido:,.2f}</b>). En promedio, las licitaciones o cotizaciones perdidas presentan "
            f"un <b>desfase de precio del {avg_desfase:.1f}%</b> con respecto a la competencia ganadora. "
            f"Adicionalmente, se mantienen <b>{len(activos)}</b> obras activas en el pipeline operativo con un valor en curso de <b>${monto_activo:,.2f}</b>."
        )
    else:
        total_monto = 0
        monto_ganado = 0
        monto_perdido = 0
        monto_activo = 0
        rate = 0
        avg_desfase = 0
        summary_text = "No se registran obras o cotizaciones en el sistema en este momento. El pipeline comercial se encuentra en cero absoluto ($0.00)."

    story.append(Paragraph(summary_text, styles['Body_Custom']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>MÉTRICAS CLAVE DEL SISTEMA DE COTIZACIONES:</b>", styles['H2_Custom']))
    grid_headers = ["Indicador Clave", "Monto Económico ($)", "Detalle / Volumen"]
    grid_rows = [
        ["Monto Total Cotizado", f"${total_monto:,.2f}", f"{len(df_proj)} obras totales"],
        ["Proyectos Ganados (Cartera)", f"${monto_ganado:,.2f}", f"{len(ganados) if 'ganados' in locals() else 0} obras"],
        ["Proyectos Perdidos", f"${monto_perdido:,.2f}", f"{len(perdidos) if 'perdidos' in locals() else 0} obras"],
        ["Porcentaje Desfase Promedio", f"{avg_desfase:.1f}%", "En propuestas perdidas"],
        ["Proyectos Activos (Pipeline)", f"${monto_activo:,.2f}", f"{len(activos) if 'activos' in locals() else 0} obras activas"],
        ["Efectividad Comercial (Éxito)", f"{rate:.1f}%", "Proporción Ganados/Cerrados"]
    ]
    
    header_row = [Paragraph(str(h), styles['TableHead']) for h in grid_headers]
    data_rows = [[Paragraph(str(cell), styles['TableBody']) for cell in row] for row in grid_rows]
    t_metrics = Table([header_row] + data_rows, colWidths=[160, 140, 204])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLS['bg_header']),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLS['white'], COLS['bg_alt']]),
        ('GRID', (0, 0), (-1, -1), 0.5, COLS['muted']),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_metrics)
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("<i>Nota: Toda la información reportada es obtenida en tiempo real de la base de datos de control interno, garantizando la inmutabilidad y la trazabilidad de cada paso del flujo.</i>", styles['Body_Custom']))
    
    story.append(NextPageTemplate('content'))
    story.append(PageBreak())
    
    # ── Page 2: Charts ──────────────────────────────────────────────────────
    story.append(Paragraph("2. ANÁLISIS COMERCIAL, DESFASE Y GEOGRÁFICO", styles['H1_Custom']))
    story.append(SectionDivider(612 - 2*54, COLS))
    story.append(Spacer(1, 10))
    
    fig_w, fig_h = 5.5, 2.2
    if not df_proj.empty:
        fig1, ax1 = plt.subplots(figsize=(fig_w, fig_h))
        sizes = [monto_ganado, monto_perdido, monto_activo]
        labels_pie = ["Ganado", "Perdido", "En Proceso"]
        labels_filtered = [labels_pie[i] for i in range(3) if sizes[i] > 0]
        sizes_filtered = [sizes[i] for i in range(3) if sizes[i] > 0]
        
        if sum(sizes_filtered) > 0:
            ax1.pie(sizes_filtered, labels=labels_filtered, colors=["#2ecc71", "#e74c3c", "#3498db"][:len(sizes_filtered)], autopct='%1.1f%%', startangle=90)
            ax1.axis('equal')
        else:
            ax1.text(0.5, 0.5, "Sin Montos Registrados", ha='center', va='center')
        
        plt.tight_layout()
        import tempfile
        temp_dir = tempfile.gettempdir()
        chart_p1 = os.path.join(temp_dir, "pdf_chart1.png")
        plt.savefig(chart_p1, dpi=200, bbox_inches='tight')
        plt.close()
        
        story.append(Image(chart_p1, width=320, height=130))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Figura 1: Distribución Porcentual del Pipeline Financiero", styles['Caption_Custom']))
        story.append(Spacer(1, 10))
        
        # Desfase de Precios Chart
        fig2, ax2 = plt.subplots(figsize=(fig_w, fig_h))
        df_lost = df_proj[(df_proj['status'] == 'Perdido') & (df_proj['lose_percentage_gap'] > 0)].copy()
        if not df_lost.empty:
            bars = ax2.bar(df_lost['name'], df_lost['lose_percentage_gap'], color='#e74c3c')
            ax2.set_ylabel('% Desfase de Precio')
            ax2.set_ylim(0, max(df_lost['lose_percentage_gap'].max() * 1.2, 10))
            ax2.set_xticklabels(df_lost['name'], rotation=15, ha='right', fontsize=6)
            for bar in bars:
                height = bar.get_height()
                ax2.annotate(f'{height:.1f}%',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 2),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=7)
        else:
            ax2.text(0.5, 0.5, "No se registran desfases comerciales", ha='center', va='center')
            
        plt.tight_layout()
        import tempfile
        temp_dir = tempfile.gettempdir()
        chart_p2 = os.path.join(temp_dir, "pdf_chart2.png")
        plt.savefig(chart_p2, dpi=200, bbox_inches='tight')
        plt.close()
        
        story.append(Image(chart_p2, width=320, height=130))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Figura 2: Porcentaje de Desfase de Precio en Proyectos Perdidos", styles['Caption_Custom']))
        
    story.append(PageBreak())
    
    # ── Page 3: Trazabilidad y Tiempos de Respuesta SLA ─────────────────────
    story.append(Paragraph("3. TRAZABILIDAD DE TIEMPOS DE RESPUESTA (SLA)", styles['H1_Custom']))
    story.append(SectionDivider(612 - 2*54, COLS))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "A continuación se presenta el desglose de los tiempos de respuesta (SLA) para cada una de las "
        "tareas completadas en el flujo. La trazabilidad mide los días transcurridos desde que "
        "se generó el pendiente hasta su confirmación y firma en el sistema, lo cual permite auditar "
        "el desempeño técnico y comercial de cada departamento.", styles['Body_Custom']
    ))
    story.append(Spacer(1, 10))
    
    def calc_sla_days(created_str, completed_str):
        if not created_str or not completed_str:
            return "N/A"
        try:
            c_date = datetime.strptime(created_str.split(" ")[0], "%Y-%m-%d").date()
            f_date = datetime.strptime(completed_str.split(" ")[0], "%Y-%m-%d").date()
            diff = (f_date - c_date).days
            return f"{diff} días" if diff > 0 else "Mismo día"
        except Exception:
            return "N/A"

    completed_tasks = [t for t in tasks if t['is_completed'] == 1]
    
    if completed_tasks:
        sla_headers = ["Proyecto / Obra", "Acción de Compuerta", "Responsable", "SLA (Tiempo)"]
        sla_rows = []
        for t in completed_tasks[:12]: # Limit to top 12 for page space
            role_assigned = t['assigned_role']
            sla_time = calc_sla_days(t['created_at'], t['completed_at'])
            sla_rows.append([
                t['project_name'] if t['project_name'] else "Sin Nombre",
                t['title'][:40] + "..." if len(t['title']) > 40 else t['title'],
                role_assigned,
                sla_time
            ])
            
        header_row_s = [Paragraph(str(h), styles['TableHead']) for h in sla_headers]
        data_rows_s = [[Paragraph(str(cell), styles['TableBody']) for cell in row] for row in sla_rows]
        t_sla = Table([header_row_s] + data_rows_s, colWidths=[130, 180, 114, 80])
        t_sla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLS['bg_header']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLS['white'], COLS['bg_alt']]),
            ('GRID', (0, 0), (-1, -1), 0.5, COLS['muted']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_sla)
    else:
        story.append(Paragraph("<i>No se registran tareas cerradas o concluidas en el sistema para auditar el SLA de respuesta.</i>", styles['Body_Custom']))
        
    # Detector de Cuello de Botella
    story.append(Spacer(1, 15))
    df_activos = df_proj[df_proj['status'] == 'Activo'] if not df_proj.empty else pd.DataFrame()
    if not df_activos.empty:
        df_act_stages = df_activos.groupby('current_stage').size().reset_index(name='count')
        max_stage_row = df_act_stages.loc[df_act_stages['count'].idxmax()]
        etapas_map_pdf = {
            1: "Levantamiento Técnico (Ventas)",
            2: "Reunión de Alineación & Minuta (Ventas / Ingeniería)",
            3: "Elaboración de Catálogo (Ingeniería)",
            4: "Presupuestación y Cotización (Costos)",
            5: "Cierre Comercial (Ventas)"
        }
        etapa_critica_pdf = etapas_map_pdf.get(max_stage_row['current_stage'], "Desconocida")
        
        story.append(Paragraph(
            f"⚠️ <b>ALERTA DE RETRASO COMERCIAL (AUDIT ROAD):</b> Actualmente se detecta una retención "
            f"de proyectos en la etapa de <b>{etapa_critica_pdf}</b> con un total de <b>{max_stage_row['count']} obras activas</b> en espera. "
            f"Se recomienda agilizar las firmas de entrega técnica para mantener los compromisos de entrega con el cliente.",
            styles['Body_Custom']
        ))
    else:
        story.append(Paragraph("🟢 <b>AUDIT REPORT:</b> No se registran cuellos de botella. El flujo operativo de DC Control se encuentra optimizado.", styles['Body_Custom']))
        
    doc.build(story)
    return pdf_buffer.getvalue()

# ==========================================
# FUNCIONES AUXILIARES DE BASE DE DATOS
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de Configuración del Sistema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL
        )
    ''')
    
    # Tabla de Proyectos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client TEXT NOT NULL,
            total_amount REAL DEFAULT 0,
            current_stage INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Activo',
            lose_reason TEXT,
            created_at TEXT,
            target_date TEXT,
            zone TEXT DEFAULT 'Sin Especificar',
            assigned_lider TEXT DEFAULT 'Líder Regional - Sur',
            assigned_costos TEXT DEFAULT 'Analista de Costos Jefe',
            observations TEXT,
            meeting_minutes_date TEXT,
            meeting_minutes_attendance TEXT,
            meeting_minutes_decisions TEXT,
            lose_percentage_gap REAL DEFAULT 0,
            director_review_required INTEGER DEFAULT 0
        )
    ''')
    
    # Tabla de Tareas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT,
            assigned_role TEXT,
            is_completed INTEGER DEFAULT 0,
            completed_at TEXT,
            completed_by TEXT,
            created_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')
    
    # Tabla de Historial (Auditoría)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_name TEXT,
            role TEXT,
            action TEXT,
            timestamp TEXT
        )
    ''')
    
    # Tabla de Documentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            filename TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT,
            stage INTEGER DEFAULT 1,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')
    
    # Migraciones
    cursor.execute("PRAGMA table_info(projects)")
    columns = [col[1] for col in cursor.fetchall()]
    if "zone" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN zone TEXT DEFAULT 'Sin Especificar'")
    if "assigned_lider" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN assigned_lider TEXT DEFAULT 'Líder Regional - Sur'")
    if "assigned_costos" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN assigned_costos TEXT DEFAULT 'Analista de Costos Jefe'")
    if "observations" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN observations TEXT")
    if "meeting_minutes_date" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN meeting_minutes_date TEXT")
    if "meeting_minutes_attendance" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN meeting_minutes_attendance TEXT")
    if "meeting_minutes_decisions" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN meeting_minutes_decisions TEXT")
    if "lose_percentage_gap" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN lose_percentage_gap REAL DEFAULT 0")
    if "director_review_required" not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN director_review_required INTEGER DEFAULT 0")
        
    cursor.execute("PRAGMA table_info(documents)")
    doc_cols = [col[1] for col in cursor.fetchall()]
    if "stage" not in doc_cols:
        cursor.execute("ALTER TABLE documents ADD COLUMN stage INTEGER DEFAULT 1")
    
    # Cuentas de usuarios por defecto
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin/Director', 'Director General')")
        cursor.execute("INSERT INTO users VALUES ('ventas1', 'ventas123', 'Ventas', 'Ing. Carlos (Ventas)')")
        cursor.execute("INSERT INTO users VALUES ('lider_sur', 'lider123', 'Líder Regional - Sur', 'Ing. Sofía (Líder Regional Sur)')")
        cursor.execute("INSERT INTO users VALUES ('lider_norte', 'lider123', 'Líder Regional - Norte', 'Ing. Alejandro (Líder Regional Norte)')")
        cursor.execute("INSERT INTO users VALUES ('costos_jefe', 'costos123', 'Analista de Costos Jefe', 'Lic. Roberto (Director de Costos)')")
        cursor.execute("INSERT INTO users VALUES ('costos_jr1', 'costos123', 'Analista de Costos Junior 1', 'Ing. Manuel (Analista Jr 1)')")
        cursor.execute("INSERT INTO users VALUES ('costos_jr2', 'costos123', 'Analista de Costos Junior 2', 'Ing. Gabriel (Analista Jr 2)')")
    
    # Muestra opcional de demos
    cursor.execute("SELECT value FROM system_settings WHERE key = 'mock_initialized'")
    setting = cursor.fetchone()
    
    if setting is None:
        mock_projects = [
            ("Torre Reforma Nubes", "Grupo Inmobiliario CDMX", 4500000.0, 5, "Ganado", None, (date.today() - timedelta(days=20)).isoformat(), (date.today() - timedelta(days=5)).isoformat(), "CDMX", "Líder Regional - Sur", "Analista de Costos Jefe", 12.0),
            ("Planta Industrial Querétaro", "Aceros del Bajío", 8200000.0, 5, "Perdido", "Fuera de precio (alto)", (date.today() - timedelta(days=25)).isoformat(), (date.today() - timedelta(days=10)).isoformat(), "Querétaro", "Líder Regional - Sur", "Analista de Costos Junior 1", 15.5),
            ("Hospital del Norte", "SS Federal", 12500000.0, 3, "Activo", None, (date.today() - timedelta(days=15)).isoformat(), (date.today() - timedelta(days=2)).isoformat(), "Nuevo León", "Líder Regional - Norte", "Analista de Costos Junior 2", 0.0),
            ("Centro Comercial Altaria", "Fibra Plus", 0, 1, "Activo", None, date.today().isoformat(), (date.today() + timedelta(days=10)).isoformat(), "Aguascalientes", "Líder Regional - Norte", "Analista de Costos Jefe", 0.0),
            ("Complejo Residencial Mitikah", "Desarrollos GAP", 3100000.0, 4, "Activo", None, (date.today() - timedelta(days=5)).isoformat(), (date.today() + timedelta(days=5)).isoformat(), "CDMX", "Líder Regional - Sur", "Analista de Costos Junior 1", 0.0)
        ]
        
        for name, client, amount, stage, status, reason, created, target, zone, lider, costos, p_gap in mock_projects:
            cursor.execute('''
                INSERT INTO projects (name, client, total_amount, current_stage, status, lose_reason, created_at, target_date, zone, assigned_lider, assigned_costos, lose_percentage_gap, director_review_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (name, client, amount, stage, status, reason, created, target, zone, lider, costos, p_gap))
            proj_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO audit_log (project_id, user_name, role, action, timestamp)
                VALUES (?, 'Sistema', 'Admin', 'Proyecto creado e ingresado a Etapa 1', ?)
            ''', (proj_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Tareas Muestra
            if stage >= 1:
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Confirmar levantamiento técnico completo (Ventas)', 'Ventas', ?, ?)", (proj_id, 1 if stage > 1 else 0, created))
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Confirmar recepción y validación técnica del levantamiento (Líder Regional)', ?, ?, ?)", (proj_id, lider, 1 if stage > 1 else 0, created))
            if stage >= 2:
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Confirmar realización de reunión de alineación (Ventas)', 'Ventas', ?, ?)", (proj_id, 1 if stage > 2 else 0, created))
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Confirmar realización de reunión de alineación (Líder Regional)', ?, ?, ?)", (proj_id, lider, 1 if stage > 2 else 0, created))
            if stage >= 3:
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Subir catálogo de conceptos y marcar completo (Líder Regional)', ?, ?, ?)", (proj_id, lider, 1 if stage > 3 else 0, created))
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Validar catálogo y confirmar información completa (Analista de Costos)', ?, ?, ?)", (proj_id, costos, 1 if stage > 3 else 0, created))
            if stage >= 4:
                cursor.execute("INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at) VALUES (?, 'Vaciar catálogo de conceptos en bases de datos y armar propuesta de Costos final', ?, ?, ?)", (proj_id, costos, 1 if stage > 4 else 0, created))
        
        cursor.execute("INSERT INTO system_settings (key, value) VALUES ('mock_initialized', '1')")
        conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), is_select=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    if is_select:
        result = cursor.fetchall()
        conn.close()
        return result
    else:
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

def log_audit(project_id, user_name, role, action):
    run_query('''
        INSERT INTO audit_log (project_id, user_name, role, action, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, user_name, role, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), is_select=False)

def eliminar_proyecto(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM audit_log WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

def restabelecer_base_de_datos(incluir_demos=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS system_settings")
    cursor.execute("DROP TABLE IF EXISTS projects")
    cursor.execute("DROP TABLE IF EXISTS tasks")
    cursor.execute("DROP TABLE IF EXISTS audit_log")
    cursor.execute("DROP TABLE IF EXISTS documents")
    conn.commit()
    conn.close()
    
    # Re-crear tablas e inicializar
    if not incluir_demos:
        # Guardamos bandera para que no cargue demos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute("INSERT INTO system_settings (key, value) VALUES ('mock_initialized', '1')")
        conn.commit()
        conn.close()
        
    init_db()

def enviar_correo_alerta(destinatario, rol_dest, asunto, proyecto_nombre, tarea_desc):
    if 'smtp_enabled' in st.session_state and st.session_state.smtp_enabled:
        try:
            msg = MIMEMultipart()
            msg['From'] = st.session_state.smtp_user
            msg['To'] = destinatario
            msg['Subject'] = f"DC Control: {asunto}"
            
            cuerpo_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <div style="background-color: #1e3a8a; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
                        <h2>DC CONTROL - Alerta de Flujo de Trabajo</h2>
                    </div>
                    <div style="padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
                        <p>Estimado miembro del equipo de <strong>{rol_dest}</strong>,</p>
                        <p>Se te ha asignado una acción/tarea dentro de la plataforma de control:</p>
                        <blockquote style="background-color: #f4f6f9; padding: 15px; border-left: 5px solid #1e3a8a; margin: 15px 0;">
                            <strong>Proyecto:</strong> {proyecto_nombre}<br/>
                            <strong>Tarea asignada:</strong> {tarea_desc}
                        </blockquote>
                        <p>Por favor ingresa a la plataforma para darle seguimiento.</p>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>
                        <small style="color: #777;">Este es un correo automático generado por el sistema de trazabilidad de DC Control.</small>
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(cuerpo_html, 'html'))
            
            server = smtplib.SMTP(st.session_state.smtp_server, st.session_state.smtp_port)
            server.starttls()
            server.login(st.session_state.smtp_user, st.session_state.smtp_password)
            server.sendmail(st.session_state.smtp_user, destinatario, msg.as_string())
            server.quit()
            st.toast(f"📧 Correo REAL enviado a {destinatario} ({rol_dest})", icon="✅")
        except Exception as e:
            st.error(f"Error al enviar correo real: {e}")
    else:
        st.toast(f"✉️ [Simulado] Alerta para {rol_dest} ({destinatario}) | Tarea: {tarea_desc}", icon="📩")

def generar_reporte_proyecto(p):
    proj_id = p['id']
    audit = run_query("SELECT * FROM audit_log WHERE project_id = ? ORDER BY timestamp ASC", (proj_id,))
    tasks = run_query("SELECT * FROM tasks WHERE project_id = ?", (proj_id,))
    docs = run_query("SELECT * FROM documents WHERE project_id = ?", (proj_id,))
    
    reporte = f"""================================================================================
DC CONTROL - REPORTE DE TRAZABILIDAD TOTAL Y DOSSIER DE OBRA
================================================================================

FICHA TÉCNICA DEL PROYECTO:
---------------------------
Nombre de la Obra: {p['name']}
Cliente:           {p['client']}
Monto Cotizado:    ${p['total_amount']:,.2f}
Zona / Región:     {p['zone']}
Líder Regional:    {p['assigned_lider']}
Analista de Costos:{p['assigned_costos']}
Estado Comercial:  {p['status']}
Fecha de Creación: {p['created_at']}
Fecha Compromiso:  {p['target_date']}
Etapa Actual:      {p['current_stage']} (de 5)
Desfase Comercial: {p['lose_percentage_gap'] if p['status'] == 'Perdido' else 0.0}%
Revisión Dirección:{'Requerida y Validada' if p['director_review_required'] == 1 else 'No requerida'}

================================================================================
MINUTA DE REUNIÓN DE ALINEACIÓN (ETAPA 2):
------------------------------------------
Fecha de Reunión: {p['meeting_minutes_date'] or 'Sin registrar'}
Asistentes:  
{p['meeting_minutes_attendance'] or 'Sin registrar'}

Decisiones y Acuerdos Clave:
{p['meeting_minutes_decisions'] or 'Sin registrar'}

================================================================================
ESTADO DE LAS TAREAS DEL FLUJO DE TRABAJO (COMPUERTAS DE CONTROL):
------------------------------------------------------------------
"""
    for t in tasks:
        t = dict(t)
        status = "✔️ COMPLETADA" if t['is_completed'] == 1 else "⏳ PENDIENTE"
        comp_by = f" por {t['completed_by']} el {t['completed_at']}" if t['is_completed'] == 1 else ""
        reporte += f"- [{t['assigned_role']}] {t['title']} -> {status}{comp_by}\n"
        
    reporte += """
================================================================================
ENTREGABLES Y DOCUMENTOS CARGADOS:
----------------------------------
"""
    if docs:
        for d in docs:
            d = dict(d)
            reporte += f"- Archivo: {d['filename']} (Cargado en Etapa {d['stage']} por {d['uploaded_by']} el {d['uploaded_at']})\n"
    else:
        reporte += "Sin documentos cargados aún.\n"
        
    reporte += """
================================================================================
BITÁCORA HISTÓRICA DE AUDITORÍA (AUDIT TRAIL):
----------------------------------------------
"""
    for a in audit:
        a = dict(a)
        reporte += f"[{a['timestamp']}] ({a['role']}) {a['user_name']}: {a['action']}\n"
        
    reporte += f"""
================================================================================
Reporte generado automáticamente el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Comercializadora Industrial DC Control S.A. de C.V.
================================================================================
"""
    return reporte

# ==========================================
# 3. CONTROL DE SESIÓN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.full_name = ""
if 'uploader_key_suffix' not in st.session_state:
    st.session_state.uploader_key_suffix = 1

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
        <div style='background-color:#1e3a8a; padding:25px; border-radius:15px; text-align:center; margin-bottom:20px; border-left: 8px solid #f39c12; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h1 style='color:white; margin:0; font-family:sans-serif; letter-spacing: 3px; font-size: 28px;'>DC CONTROL</h1>
            <p style='color:#93c5fd; font-family:sans-serif; font-weight: bold; margin: 5px 0 0 0;'>Sistema Interno de Control y Trazabilidad</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.write("### 🔑 Iniciar Sesión")
            username_input = st.text_input("Usuario / Username:", placeholder="Escribe tu usuario")
            password_input = st.text_input("Contraseña / Password:", type="password", placeholder="Escribe tu contraseña")
            
            login_btn = st.button("Ingresar al Portal", use_container_width=True, type="primary")
            
            if login_btn:
                user_res = run_query("SELECT * FROM users WHERE username = ? AND password = ?", (username_input, password_input))
                if user_res:
                    user_data = dict(user_res[0])
                    st.session_state.logged_in = True
                    st.session_state.user_name = user_data['username']
                    st.session_state.user_role = user_data['role']
                    st.session_state.full_name = user_data['full_name']
                    st.success(f"¡Bienvenido, {user_data['full_name']}!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Por favor verifica tus datos.")
    st.stop()

# ==========================================
# 4. INTERFAZ UNA VEZ LOGUEADO
# ==========================================
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
    st.sidebar.markdown("""
    <div style='background-color:#1e3a8a; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px; border-left: 5px solid #f39c12;'>
        <h3 style='color:white; margin:0; font-family:sans-serif; letter-spacing: 1px;'>DC CONTROL</h3>
        <small style='color:#93c5fd;'>Control de Obras & Licitaciones</small>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown(f"👤 **Sesión Activa:**\n* **Nombre:** {st.session_state.full_name}\n* **Puesto:** `{st.session_state.user_role}`")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout()

st.sidebar.markdown("---")

role = st.session_state.user_role

if role == "Admin/Director":
    with st.sidebar.expander("📧 Configurar Correos (SMTP)"):
        st.write("Configuración del servidor:")
        smtp_server = st.text_input("Servidor SMTP:", value="smtp.gmail.com", key="smtp_server")
        smtp_port = st.number_input("Puerto (TLS):", value=587, key="smtp_port")
        smtp_user = st.text_input("Correo Emisor:", key="smtp_user")
        smtp_password = st.text_input("Contraseña de Aplicación:", type="password", key="smtp_password")
        smtp_enabled = st.checkbox("Habilitar envío de correos", value=False, key="smtp_enabled")
        
        st.markdown("**Destinatarios Configurados:**")
        email_ventas = st.text_input("Ventas:", value=EMAIL_MAP["Ventas"], key="em_ventas")
        email_ingeniero = st.text_input("Ingeniería:", value=EMAIL_MAP["Ingeniero"], key="em_ing")
        email_lider_sur = st.text_input("Líder Reg. Sur:", value=EMAIL_MAP["Líder Regional - Sur"], key="em_lider_sur")
        email_lider_norte = st.text_input("Líder Reg. Norte:", value=EMAIL_MAP["Líder Regional - Norte"], key="em_lider_norte")
        email_costos_jefe = st.text_input("Costos Jefe:", value=EMAIL_MAP["Analista de Costos Jefe"], key="em_costos_jefe")
else:
    email_ventas = EMAIL_MAP["Ventas"]
    email_ingeniero = EMAIL_MAP["Ingeniero"]
    email_lider_sur = EMAIL_MAP["Líder Regional - Sur"]
    email_lider_norte = EMAIL_MAP["Líder Regional - Norte"]
    email_costos_jefe = EMAIL_MAP["Analista de Costos Jefe"]

st.sidebar.caption("SLA, Compuertas Técnicas y Validación de Documentos activos en el sistema.")

# ==========================================
# 5. ESTRUCTURA DE PESTAÑAS SEGÚN ROL
# ==========================================
tabs_definidos = []
if role == "Admin/Director":
    tabs_definidos = ["📊 Reportes Globales", "📋 Control Operativo (Todo)", "📅 Agenda de Trabajos", "🗺️ Kanban Visual", "🔍 Consulta Histórica de Tareas", "👥 Gestión de Usuarios", "📜 Auditoría Completa"]
elif role == "Ventas":
    tabs_definidos = ["📋 Mis Proyectos Activos (Ventas)", "📅 Agenda de Trabajos", "🗺️ Kanban Visual", "🔍 Consulta Histórica de Tareas"]
elif "Líder Regional" in role or role == "Ingeniero":
    tabs_definidos = ["📋 Mis Catálogos de Conceptos", "📅 Agenda de Trabajos", "🗺️ Kanban Visual", "🔍 Consulta Histórica de Tareas"]
elif "Analista de Costos" in role:
    tabs_definidos = ["📋 Presupuestos por Cotizar", "📅 Agenda de Trabajos", "🗺️ Kanban Visual", "🔍 Consulta Histórica de Tareas"]

tabs = st.tabs(tabs_definidos)
tab_index = {t_name: t_obj for t_name, t_obj in zip(tabs_definidos, tabs)}

# ==========================================
# MODULO: REPORTES GLOBALES (Solo Admin)
# ==========================================
if "📊 Reportes Globales" in tab_index:
    with tab_index["📊 Reportes Globales"]:
        st.subheader("Indicadores de Desempeño Financiero, Zonas, Desfase y Efectividad")
        
        projs = run_query("SELECT * FROM projects")
        df_proj = pd.DataFrame([dict(p) for p in projs]) if projs else pd.DataFrame()
        
        if not df_proj.empty:
            ganados = df_proj[df_proj['status'] == 'Ganado']
            perdidos = df_proj[df_proj['status'] == 'Perdido']
            activos = df_proj[df_proj['status'] == 'Activo']
            
            monto_ganado = ganados['total_amount'].sum()
            monto_perdido = perdidos['total_amount'].sum()
            monto_total = df_proj['total_amount'].sum()
            conversion_rate = (len(ganados) / (len(ganados) + len(perdidos)) * 100) if (len(ganados) + len(perdidos)) > 0 else 0
            
            # Porcentaje de desfase promedio
            perdidos_con_desfase = perdidos[perdidos['lose_percentage_gap'] > 0]
            avg_desfase_kpi = perdidos_con_desfase['lose_percentage_gap'].mean() if not perdidos_con_desfase.empty else 0.0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Monto Total Cotizado", f"${monto_total:,.2f}")
            col2.metric("Monto Ganado (Cartera)", f"${monto_ganado:,.2f}", delta=f"+{len(ganados)} obras")
            col3.metric("Monto Perdido", f"${monto_perdido:,.2f}", delta=f"-{len(perdidos)} obras", delta_color="inverse")
            col4.metric("Desfase de Precio Promedio", f"{avg_desfase_kpi:.1f}%")
            
            st.markdown("---")
            col_rep1, col_rep2, col_rep3 = st.columns(3)
            with col_rep1:
                csv_projects = df_proj.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Obras (CSV)",
                    data=csv_projects,
                    file_name="Reporte_General_Obras_DC_Control.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_rep2:
                tasks_raw = run_query("""
                    SELECT t.*, p.name as project_name, p.client as project_client, p.zone as project_zone
                    FROM tasks t
                    LEFT JOIN projects p ON t.project_id = p.id
                """)
                if tasks_raw:
                    df_tasks_raw = pd.DataFrame([dict(x) for x in tasks_raw])
                    csv_tasks = df_tasks_raw.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Tareas (CSV)",
                        data=csv_tasks,
                        file_name="Reporte_Tareas_Etapas_DC_Control.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            with col_rep3:
                try:
                    pdf_bytes = generar_pdf_reporte_ejecutivo(DB_FILE)
                    if os.path.exists("/workspace/out"):
                        try:
                            with open("/workspace/out/reporte_ejecutivo_dc_control.pdf", "wb") as f_pdf:
                                f_pdf.write(pdf_bytes)
                        except Exception:
                            pass
                    st.download_button(
                        label="📄 Descargar Reporte PDF Ejecutivo",
                        data=pdf_bytes,
                        file_name="Reporte_Ejecutivo_DC_Control.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as pdf_error:
                    st.error(f"Error PDF: {pdf_error}")
            
            st.markdown("---")
            
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("#### Balance de Pipeline: Ganado vs Perdido ($)")
                fig = px.pie(
                    names=["Ganado", "Perdido", "En Proceso"],
                    values=[monto_ganado, monto_perdido, activos['total_amount'].sum()],
                    color=["Ganado", "Perdido", "En Proceso"],
                    color_discrete_map={"Ganado": "#2ecc71", "Perdido": "#e74c3c", "En Proceso": "#3498db"},
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.markdown("#### Análisis de Motivos de Pérdida")
                df_reasons = df_proj[df_proj['status'] == 'Perdido'].groupby('lose_reason').size().reset_index(name='Casos')
                if not df_reasons.empty:
                    fig_r = px.bar(df_reasons, x='lose_reason', y='Casos', color='lose_reason', color_discrete_sequence=px.colors.qualitative.Safe)
                    st.plotly_chart(fig_r, use_container_width=True)
                else:
                    st.info("No hay descartes registrados todavía.")
            
            # Dashboard de Porcentajes de Desfase
            st.markdown("---")
            st.markdown("### 📉 Análisis de Desfase de Precios en Licitaciones Perdidas")
            df_lost = df_proj[(df_proj['status'] == 'Perdido') & (df_proj['lose_percentage_gap'] > 0)].copy()
            if not df_lost.empty:
                fig_gap = px.bar(
                    df_lost, 
                    x='name', 
                    y='lose_percentage_gap', 
                    color='zone', 
                    labels={'name': 'Proyecto', 'lose_percentage_gap': '% Desfase vs Competencia', 'zone': 'Estado'},
                    text='lose_percentage_gap',
                    hover_data=['client', 'total_amount']
                )
                fig_gap.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig_gap, use_container_width=True)
            else:
                st.info("No se registran descartes con porcentajes de desfase asignados aún.")

            st.markdown("---")
            st.markdown("### 🗺️ Rendimiento y Éxito por Zona Geográfica")
            col_z1, col_z2 = st.columns(2)
            
            with col_z1:
                st.markdown("#### Efectividad de Éxito por Zona (% de Éxito)")
                df_zones = df_proj[df_proj['status'].isin(['Ganado', 'Perdido'])].copy()
                if not df_zones.empty:
                    df_z_stats = df_zones.groupby(['zone', 'status']).size().unstack(fill_value=0).reset_index()
                    if 'Ganado' not in df_z_stats.columns: df_z_stats['Ganado'] = 0
                    if 'Perdido' not in df_z_stats.columns: df_z_stats['Perdido'] = 0
                    df_z_stats['Tasa_Exito'] = (df_z_stats['Ganado'] / (df_z_stats['Ganado'] + df_z_stats['Perdido'])) * 100
                    
                    fig_z1 = px.bar(df_z_stats, x='zone', y='Tasa_Exito', labels={'zone': 'Zona', 'Tasa_Exito': '% Éxito Comercial'}, color='zone', text_auto='.1f')
                    st.plotly_chart(fig_z1, use_container_width=True)
                else:
                    st.caption("No hay suficientes obras finalizadas para calcular el éxito por zonas.")
            
            with col_z2:
                st.markdown("#### Montos Totales Cotizados por Zona Geográfica ($)")
                df_zone_money = df_proj.groupby('zone')['total_amount'].sum().reset_index()
                fig_z2 = px.pie(df_zone_money, names='zone', values='total_amount', color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig_z2, use_container_width=True)
                
            # DETECTOR INTELIGENTE DE CUELLOS DE BOTELLA
            st.markdown("---")
            st.markdown("### ⏱️ Auditoría de Cuello de Botella Operativo")
            
            if not activos.empty:
                df_act_stages = activos.groupby('current_stage').size().reset_index(name='count')
                max_stage_row = df_act_stages.loc[df_act_stages['count'].idxmax()]
                
                etapas_map = {
                    1: ("Ventas", "Levantamiento Técnico (Fase 1)"),
                    2: ("Ventas / Líderes Regionales", "Reunión de Alineación & Minuta (Fase 2)"),
                    3: ("Ingeniería / Líderes Regionales", "Elaboración y Validación de Catálogo (Fase 3)"),
                    4: ("Analista de Costos Asignado", "Presupuestación/Cotización (Fase 4)"),
                    5: ("Ventas", "Cierre Comercial (Fase 5)")
                }
                
                puesto_critico, etapa_critica = etapas_map[max_stage_row['current_stage']]
                st.error(f"🚨 **ALERTA DE RETRASO:** El departamento con mayor acumulación de trabajo actualmente es **{puesto_critico}** con **{max_stage_row['count']} obras activas** retenidas en la etapa de **{etapa_critica}**.")
            else:
                st.success("🟢 **OPERACIÓN OPTIMIZADA:** No hay obras activas retenidas en el pipeline actual.")
                
        else:
            st.info("No hay información registrada para generar reportes comerciales.")

# ==========================================
# MODULO: CONTROL OPERATIVO FILTRADO POR ROL
# ==========================================
operativo_tab_key = [k for k in tabs_definidos if "📋" in k][0]

with tab_index[operativo_tab_key]:
    st.subheader("Bandeja de Proyectos y Tareas Asignadas")
    
    if role == "Admin/Director":
        st.markdown("#### 🔍 Filtrar visualización de obras:")
        filtro_vista = st.radio("Mostrar proyectos:", ["Solo Activos", "Archivados (Ganados / Perdidos)", "Todos"], horizontal=True)
        
        if filtro_vista == "Solo Activos":
            query_obras = "SELECT * FROM projects WHERE status = 'Activo'"
            params_obras = ()
        elif filtro_vista == "Archivados (Ganados / Perdidos)":
            query_obras = "SELECT * FROM projects WHERE status IN ('Ganado', 'Perdido')"
            params_obras = ()
        else:
            query_obras = "SELECT * FROM projects"
            params_obras = ()
    elif role == "Ventas":
        query_obras = "SELECT * FROM projects WHERE status = 'Activo' AND current_stage IN (1, 2, 5)"
        params_obras = ()
        st.info("ℹ️ Vista de Ventas: Mostrando proyectos en **Levantamiento (1)**, **Reunión de Alineación & Minuta (2)** o **Cierre Comercial (5)**.")
    elif "Líder Regional" in role:
        query_obras = "SELECT * FROM projects WHERE status = 'Activo' AND current_stage IN (2, 3) AND assigned_lider = ?"
        params_obras = (role,)
        st.info(f"ℹ️ Vista de {role}: Mostrando proyectos asignados en **Reunión de Alineación (2)** o **Catálogo de Conceptos (3)**.")
    elif "Analista de Costos" in role:
        query_obras = "SELECT * FROM projects WHERE status = 'Activo' AND current_stage IN (3, 4) AND assigned_costos = ?"
        params_obras = (role,)
        st.info(f"ℹ️ Vista de {role}: Mostrando proyectos asignados en **Validación de Catálogo (3)** o **Presupuestación (4)**.")
    elif role == "Ingeniero":
        query_obras = "SELECT * FROM projects WHERE status = 'Activo' AND current_stage IN (2, 3)"
        params_obras = ()

    obras_visibles = run_query(query_obras, params_obras)
    
    # SOLO EL ADMIN/DIRECTOR CREA LOS PROYECTOS (Monto inicial removido, se define en Cotización)
    if role == "Admin/Director":
        with st.expander("➕ Iniciar Nuevo Proyecto / Obra (Exclusivo Administrador)"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Nombre de la Obra/Proyecto:")
            p_client = c1.text_input("Cliente:")
            p_sla = c2.date_input("Compromiso de Entrega al Cliente:", value=date.today() + timedelta(days=15))
            
            p_state = c1.selectbox("Estado de la Obra (Ubicación Geográfica):", list(ESTADOS_MEXICO.keys()))
            mapped_lider = ESTADOS_MEXICO[p_state]
            c1.info(f"📍 Región asignada automáticamente: **{mapped_lider}**")
            
            p_analista = c2.selectbox("Asignar Analista de Costos:", [
                "Analista de Costos Jefe",
                "Analista de Costos Junior 1",
                "Analista de Costos Junior 2"
            ])
            
            # Punto 5: Configuración de la revisión con Dirección Comercial al crear el proyecto
            p_review = c2.checkbox("¿Requiere Aprobación Obligatoria de Dirección Comercial en la Etapa 4?", value=False)
            
            submit_proj = st.button("Lanzar Flujo Automatizado con Doble Checks", use_container_width=True, type="primary")
            if submit_proj and p_name and p_client:
                # El total_amount se guarda inicialmente en 0
                new_id = run_query('''
                    INSERT INTO projects (name, client, total_amount, current_stage, status, created_at, target_date, zone, assigned_lider, assigned_costos, lose_percentage_gap, director_review_required)
                    VALUES (?, ?, 0, 1, 'Activo', ?, ?, ?, ?, ?, 0, ?)
                ''', (p_name, p_client, date.today().isoformat(), p_sla.isoformat(), p_state, mapped_lider, p_analista, 1 if p_review else 0), is_select=False)
                
                # Insertar la tarea inicial de doble check para Etapa 1
                run_query('''
                    INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                    VALUES (?, 'Confirmar levantamiento técnico completo (Ventas)', 'Ventas', 0, ?)
                ''', (new_id, date.today().isoformat()), is_select=False)
                run_query('''
                    INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                    VALUES (?, 'Confirmar recepción y validación técnica del levantamiento (Líder Regional)', 'Líder Regional', 0, ?)
                ''', (new_id, date.today().isoformat()), is_select=False)
                
                log_audit(new_id, st.session_state.full_name, role, f"Inició el proyecto {p_name} en {p_state}. Asignado a {mapped_lider} y {p_analista}.")
                enviar_correo_alerta(email_ventas, "Ventas", f"Nuevo Levantamiento Técnico: {p_name}", p_name, "Subir archivos de levantamiento y firmar check")
                st.success("¡Proyecto creado con éxito y asignado según gobernanza!")
                st.rerun()

    if not obras_visibles:
        st.warning("No tienes obras o tareas pendientes asignadas a tu departamento en este momento.")
    else:
        # --- MEJORA DE NAVEGACIÓN Y REDUCCIÓN DE SCROLL ---
        st.markdown("### 📋 Resumen del Panel de Trabajo")
        st.write("A continuación se muestra un resumen ejecutivo de tus proyectos asignados:")
        
        # Crear un DataFrame resumen elegante
        resumen_data = []
        etapas_nombres = {
            1: "1. Levantamiento Técnico",
            2: "2. Reunión & Minuta",
            3: "3. Elaboración Catálogo",
            4: "4. Presupuestación",
            5: "5. Cierre Comercial"
        }
        for o in obras_visibles:
            o_dict = dict(o)
            target = datetime.strptime(o_dict['target_date'], "%Y-%m-%d").date()
            dias_restantes = (target - date.today()).days
            
            if o_dict['status'] == 'Ganado':
                sla_txt = "🏆 Ganado"
            elif o_dict['status'] == 'Perdido':
                sla_txt = f"❌ Perdido ({o_dict['lose_reason']})"
            else:
                if dias_restantes < 0:
                    sla_txt = f"🔴 Atrasado ({abs(dias_restantes)} d)"
                    sla_msg_color = "red"
                elif dias_restantes <= 3:
                    sla_txt = f"🟡 Crítico ({dias_restantes} d)"
                    sla_msg_color = "orange"
                else:
                    sla_txt = f"🟢 A tiempo ({dias_restantes} d)"
                    sla_msg_color = "blue"
            
            resumen_data.append({
                "ID": o_dict['id'],
                "Nombre del Proyecto": o_dict['name'],
                "Cliente": o_dict['client'],
                "Etapa Actual": etapas_nombres.get(o_dict['current_stage'], "Desconocida"),
                "Monto ($)": f"${o_dict['total_amount']:,.2f}",
                "Estatus": o_dict['status'],
                "Zona": o_dict['zone'],
                "SLA / Margen": sla_txt
            })
            
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🛠️ Espacio de Trabajo Enfocado")
        st.write("Selecciona una obra de la lista para ver su checklist, subir archivos, minutas de reunión o registrar cierres:")
        
        # Selector del proyecto enfocado
        opciones_proyectos = {f"🏗️ {o['name']} (Cliente: {o['client']}) - Etapa {o['current_stage']}": o['id'] for o in obras_visibles}
        proyecto_seleccionado_label = st.selectbox("🎯 Selecciona la Obra en la que deseas trabajar hoy:", list(opciones_proyectos.keys()), key="foc_proj_select")
        proyecto_id_seleccionado = opciones_proyectos[proyecto_seleccionado_label]
        
        for p in obras_visibles:
            p = dict(p)
            proj_id = p['id']
            if 'proyecto_id_seleccionado' in locals() and proj_id != proyecto_id_seleccionado:
                continue
            if proj_id != proyecto_id_seleccionado:
                continue # Omitir todos los demás proyectos y renderizar solo el enfocado
            
            target = datetime.strptime(p['target_date'], "%Y-%m-%d").date()
            dias_restantes = (target - date.today()).days
            
            # Formatear el badge de estatus comercial
            badge_status = ""
            if p['status'] == 'Ganado':
                badge_status = "🏆 GANADO"
                card_style = "border-left: 8px solid #2ecc71; padding: 15px; background-color: #f4fbf7; border-radius: 8px; margin-bottom: 15px;"
                sla_msg = "Finalizado con éxito"
            elif p['status'] == 'Perdido':
                badge_status = f"❌ PERDIDO ({p['lose_reason']}) | Desfase: {p['lose_percentage_gap']:.1f}%"
                card_style = "border-left: 8px solid #95a5a6; padding: 15px; background-color: #f2f4f4; border-radius: 8px; margin-bottom: 15px;"
                sla_msg = "Descartado"
            else:
                badge_status = "⏳ ACTIVO"
                if dias_restantes < 0:
                    card_style = "border-left: 8px solid #e74c3c; padding: 15px; background-color: #fff5f5; border-radius: 8px; margin-bottom: 15px;"
                    sla_msg = f"🔴 **ATRASADO POR {abs(dias_restantes)} DÍAS**"
                elif dias_restantes <= 3:
                    card_style = "border-left: 8px solid #f39c12; padding: 15px; background-color: #fffdf5; border-radius: 8px; margin-bottom: 15px;"
                    sla_msg = f"🟡 **Crítico: {dias_restantes} días de margen**"
                else:
                    card_style = "border-left: 8px solid #1e3a8a; padding: 15px; background-color: #fafbfc; border-radius: 8px; margin-bottom: 15px;"
                    sla_msg = f"🟢 **A tiempo ({dias_restantes} días de margen)**"
                
            st.markdown(f'<div style="{card_style}">', unsafe_allow_html=True)
            
            col_info, col_status = st.columns(2)
            with col_info:
                st.markdown(f"<h3 style='margin:0; color:#1e3a8a;'>{p['name']} — <em>{p['client']}</em></h3>", unsafe_allow_html=True)
                st.write(f"**Importe Cotizado Actual:** ${p['total_amount']:,.2f} | **Zona:** {p['zone']} | **Entrega:** {p['target_date']} ({sla_msg})")
                st.write(f"👥 **Responsables:** **{p['assigned_lider']}** y **{p['assigned_costos']}**")
            with col_status:
                etapas = ["1. Levantamiento Técnico", "2. Reunión de Alineación & Minuta", "3. Elaboración de Catálogo (Validación de Info)", "4. Presupuestación y Cotización", "5. Cierre Comercial"]
                st.markdown(f"<div style='text-align:right;'><span style='background-color:#1e3a8a; color:white; padding:5px 10px; border-radius:15px; font-size:12px; font-weight:bold;'>Etapa {etapas[p['current_stage'] - 1]}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:right; margin-top:5px;'><span style='font-size:14px; font-weight:bold; color:#16a085;'>{badge_status}</span></div>", unsafe_allow_html=True)
                
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            
            # =========================================
            # COMPUERTAS DE ARCHIVOS EN TIEMPO REAL
            # =========================================
            doc_counts = {}
            for s in [1, 3, 4]:
                # Verificar tanto en BD como la existencia física del archivo
                count_res = run_query("SELECT * FROM documents WHERE project_id = ? AND stage = ?", (proj_id, s))
                cnt = 0
                if count_res:
                    for d in count_res:
                        d_dict = dict(d)
                        fpath = os.path.join("uploaded_files", f"{d_dict['project_id']}_{d_dict['stage']}_{d_dict['filename']}")
                        if os.path.exists(fpath):
                            cnt += 1
                doc_counts[s] = cnt
                
            # ==========================================
            # SECCIÓN: MINUTA DE REUNIÓN (ETAPA 2)
            # ==========================================
            if p['current_stage'] == 2:
                st.markdown("#### 📝 Minuta de Reunión de Alineación (Requerido)")
                curr_date = p['meeting_minutes_date'] or date.today().isoformat()
                curr_attendance = p['meeting_minutes_attendance'] or ""
                curr_decisions = p['meeting_minutes_decisions'] or ""
                
                puedo_editar_minuta = role in ["Admin/Director", "Ventas", "Líder Regional - Sur", "Líder Regional - Norte"]
                
                if puedo_editar_minuta:
                    with st.expander("📝 Editar Minuta de Reunión Oficial", expanded=not curr_decisions):
                        with st.form(f"f_minuta_{proj_id}"):
                            m_date = st.date_input("Fecha de la Reunión:", value=datetime.strptime(curr_date, "%Y-%m-%d").date() if curr_date else date.today(), key=f"md_{proj_id}")
                            m_attendance = st.text_area("Integrantes Asistentes:", value=curr_attendance, placeholder="Ej: Carlos (Ventas), Sofía (Líder Regional)...", key=f"ma_{proj_id}")
                            m_decisions = st.text_area("Decisiones Clave y Acuerdos Técnicos:", value=curr_decisions, placeholder="Ej: Se definió que Ingeniería estructurará conceptos...", key=f"mdec_{proj_id}")
                            
                            submit_minuta = st.form_submit_button("💾 Guardar y Registrar Minuta")
                            if submit_minuta:
                                run_query('''
                                    UPDATE projects 
                                    SET meeting_minutes_date = ?, meeting_minutes_attendance = ?, meeting_minutes_decisions = ?
                                    WHERE id = ?
                                ''', (m_date.isoformat(), m_attendance, m_decisions, proj_id), is_select=False)
                                log_audit(proj_id, st.session_state.full_name, role, "Registró/Actualizó la minuta de reunión de alineación.")
                                st.success("¡Minuta de reunión guardada exitosamente!")
                                st.rerun()
                
                if curr_decisions:
                    st.markdown(f"""
                    <div style="background-color: #fdfefe; padding: 15px; border: 1px solid #dcdde1; border-radius: 5px; margin-top: 10px;">
                        <strong>📅 Fecha:</strong> {curr_date}<br/>
                        <strong>👥 Asistencia:</strong> {curr_attendance}<br/>
                        <strong>💡 Decisiones Tomadas:</strong><br/>
                        {curr_decisions.replace('\n', '<br/>')}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Advertencias de Documento Obligatorio (Bloqueo de Avance)
            if p['current_stage'] == 1 and doc_counts[1] == 0:
                st.error("⚠️ **COMPUERTA DE CONTROL DE CONTROL BLINDADA:** Debes cargar al menos un entregable de Levantamiento Técnico (Planos, Fotos o Notas de Campo) en la sección de archivos abajo para desbloquear las firmas y avanzar de etapa.")
            elif p['current_stage'] == 2 and not p['meeting_minutes_decisions']:
                st.error("⚠️ **COMPUERTA DE CONTROL DE REUNIÓN:** Se requiere llenar y guardar la Minuta de Reunión Oficial de arriba para poder validar las firmas de esta etapa.")
            elif p['current_stage'] == 3 and doc_counts[3] == 0:
                st.error("⚠️ **COMPUERTA DE VALIDACIÓN TÉCNICA:** Debes cargar el archivo del Catálogo de Conceptos (.xlsx) en la sección inferior para poder firmar y avanzar a Costos.")
            elif p['current_stage'] == 4 and doc_counts[4] == 0:
                st.error("⚠️ **COMPUERTA DE PROPUESTA ECONÓMICA:** Debes cargar el documento con el Presupuesto / Propuesta Final (.xlsx o .pdf) abajo antes de poder firmar y finalizar la cotización.")

            st.write("**📝 Tareas y Compuertas de Control de este Paso:**")
            tareas = run_query("SELECT * FROM tasks WHERE project_id = ?", (proj_id,))
            
            for t in tareas:
                t = dict(t)
                completado = t['is_completed'] == 1
                
                # Mapear rol de visualización real
                role_target = t['assigned_role']
                if role_target == "Líder Regional":
                    role_target = p['assigned_lider']
                elif role_target == "Analista de Costos":
                    role_target = p['assigned_costos']
                    
                assigned_fullname = obtener_nombre_asignado(role_target)
                
                # Traducir a descripciones claras solicitadas
                clean_title = t['title']
                if "Confirmar levantamiento técnico completo" in t['title']:
                    clean_title = "Levantamiento técnico completo y entregado en el sistema"
                elif "Confirmar recepción y validación técnica del levantamiento" in t['title']:
                    clean_title = "Confirmar recepción de levantamiento completo y validación técnica"
                elif "Confirmar realización de reunión de alineación" in t['title']:
                    if "Ventas" in t['title']:
                        clean_title = "Confirmar realización de reunión de alineación y minuta de acuerdos"
                    else:
                        clean_title = "Confirmar realización de reunión de alineación y acuerdos de minuta"
                elif "Subir catálogo de conceptos" in t['title']:
                    clean_title = "Catálogo de conceptos completo y cargado en el sistema"
                elif "Validar catálogo y confirmar" in t['title']:
                    clean_title = "Catálogo de conceptos revisado, completo y validado para presupuestar"
                elif "Vaciar catálogo de conceptos" in t['title']:
                    clean_title = "Propuesta económica y presupuesto final completado y cargado"
                elif "Revisión con el Director Comercial" in t['title']:
                    clean_title = "Aprobación y Visto Bueno de Dirección Comercial (Completado y Firmado)"
                
                label_display = f"👤 {role_target} ({assigned_fullname}): {clean_title}"
                
                # Validar permiso de firma
                puedo_editar_tarea = False
                if role == "Admin/Director":
                    puedo_editar_tarea = True
                else:
                    if role_target == role:
                        puedo_editar_tarea = True
                        
                # Comprobar si la compuerta de documentos está bloqueada para esta tarea
                bloqueado_por_compuerta = False
                if p['current_stage'] == 1 and doc_counts[1] == 0:
                    bloqueado_por_compuerta = True
                elif p['current_stage'] == 2 and not p['meeting_minutes_decisions']:
                    bloqueado_por_compuerta = True
                elif p['current_stage'] == 3 and doc_counts[3] == 0:
                    bloqueado_por_compuerta = True
                elif p['current_stage'] == 4 and doc_counts[4] == 0:
                    bloqueado_por_compuerta = True
                
                if completado:
                    st.success(f"✔️ {label_display} — Completado por {t['completed_by']} el {t['completed_at']}")
                else:
                    if puedo_editar_tarea:
                        marcar = st.checkbox(f"✔️ Marcar como completado: {label_display}", key=f"act_{t['id']}", disabled=bloqueado_por_compuerta)
                        if marcar:
                            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            run_query('''
                                UPDATE tasks 
                                SET is_completed = 1, completed_at = ?, completed_by = ? 
                                WHERE id = ?
                            ''', (ahora, st.session_state.full_name, t['id']), is_select=False)
                            
                            log_audit(proj_id, st.session_state.full_name, role, f"Firmó compuerta de control: '{clean_title}'")
                            
                            # Validar si todas las tareas de la etapa actual están completadas
                            siguiente_etapa = p['current_stage'] + 1
                            tareas_sin_hacer = run_query("SELECT COUNT(*) as count FROM tasks WHERE project_id = ? AND is_completed = 0", (proj_id,))
                            
                            if tareas_sin_hacer[0]['count'] == 0:
                                # AVANCE AUTOMÁTICO DE COMPUERTAS
                                if siguiente_etapa == 2:
                                    run_query('''
                                        INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                        VALUES (?, 'Confirmar realización de reunión de alineación (Ventas)', 'Ventas', 0, ?)
                                    ''', (proj_id, date.today().isoformat()), is_select=False)
                                    run_query('''
                                        INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                        VALUES (?, 'Confirmar realización de reunión de alineación (Líder Regional)', ?, 0, ?)
                                    ''', (proj_id, p['assigned_lider'], date.today().isoformat()), is_select=False)
                                    
                                    run_query("UPDATE projects SET current_stage = 2 WHERE id = ?", (proj_id,), is_select=False)
                                    log_audit(proj_id, "Sistema", "Admin", f"Proyecto avanzó a Etapa 2. Doble check de alineación (Ventas y {p['assigned_lider']}).")
                                    
                                elif siguiente_etapa == 3:
                                    run_query('''
                                        INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                        VALUES (?, 'Subir catálogo de conceptos y marcar completo (Líder Regional)', ?, 0, ?)
                                    ''', (proj_id, p['assigned_lider'], date.today().isoformat()), is_select=False)
                                    run_query('''
                                        INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                        VALUES (?, 'Validar catálogo y confirmar información completa (Analista de Costos)', ?, 0, ?)
                                    ''', (proj_id, p['assigned_costos'], date.today().isoformat()), is_select=False)
                                    
                                    run_query("UPDATE projects SET current_stage = 3 WHERE id = ?", (proj_id,), is_select=False)
                                    log_audit(proj_id, "Sistema", "Admin", f"Reunión de alineación validada. Avanzó a Etapa 3. Asignado a {p['assigned_lider']} y {p['assigned_costos']}.")
                                    
                                elif siguiente_etapa == 4:
                                    run_query('''
                                        INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                        VALUES (?, 'Vaciar catálogo de conceptos en bases de datos y armar propuesta de Costos final', ?, 0, ?)
                                    ''', (proj_id, p['assigned_costos'], date.today().isoformat()), is_select=False)
                                    
                                    # Si tiene activo el doble check del Director, se inserta la tarea del Director
                                    if p['director_review_required'] == 1:
                                        run_query('''
                                            INSERT INTO tasks (project_id, title, assigned_role, is_completed, created_at)
                                            VALUES (?, 'Aprobación y Visto Bueno de Dirección Comercial (Completado y Firmado)', 'Admin/Director', 0, ?)
                                        ''', (proj_id, date.today().isoformat()), is_select=False)
                                        
                                    run_query("UPDATE projects SET current_stage = 4 WHERE id = ?", (proj_id,), is_select=False)
                                    log_audit(proj_id, "Sistema", "Admin", f"Catálogo validado por Ingeniería y Costos. Avanzó a Etapa 4. Asignado a {p['assigned_costos']}.")
                                    
                                elif siguiente_etapa == 5:
                                    run_query("UPDATE projects SET current_stage = 5 WHERE id = ?", (proj_id,), is_select=False)
                                    log_audit(proj_id, "Sistema", "Admin", f"Presupuesto y propuesta final completados. Proyecto enviado a Ventas para Cierre Comercial.")
                                    enviar_correo_alerta(email_ventas, "Ventas", f"Cotización Terminada y Lista para Cliente: {p['name']}", p['name'], "Cierre Comercial con el Cliente")
                                    
                            st.success("¡Tarea actualizada exitosamente!")
                            st.rerun()
                    else:
                        st.warning(f"🔒 Firma exclusiva del responsable: **{role_target}** ({assigned_fullname}).")

            # =========================================
            # SECCIÓN INTERACTIVA DE COSTOS (ETAPA 4)
            # =========================================
            if p['current_stage'] == 4 and "Analista de Costos" in role or role == "Admin/Director":
                st.markdown("#### ⚙️ Registro de Monto de la Propuesta")
                with st.container(border=True):
                    monto_costos = st.number_input("Monto Cotizado Final ($):", min_value=0.0, value=p['total_amount'], key=f"mnt_cst_{proj_id}")
                    if st.button("💾 Guardar y Registrar Monto de Cotización", key=f"btn_mnt_{proj_id}"):
                        run_query("UPDATE projects SET total_amount = ? WHERE id = ?", (monto_costos, proj_id), is_select=False)
                        log_audit(proj_id, st.session_state.full_name, role, f"Registró el monto cotizado de la propuesta: ${monto_costos:,.2f}")
                        st.success("¡Monto registrado con éxito!")
                        st.rerun()

            # REPOSITORIO DE DOCUMENTOS (CON DESCARGA DE ARCHIVOS FÍSICOS)
            st.write("**📂 Documentación y Entregables:**")
            docs = run_query("SELECT * FROM documents WHERE project_id = ? ORDER BY stage ASC", (proj_id,))
            if docs:
                for doc in docs:
                    doc_dict = dict(doc)
                    filepath = os.path.join("uploaded_files", f"{doc_dict['project_id']}_{doc_dict['stage']}_{doc_dict['filename']}")
                    col_doc1, col_doc2 = st.columns([3, 1])
                    with col_doc1:
                        st.markdown(f"📄 **[Etapa {doc_dict['stage']}]** **{doc_dict['filename']}** *(Cargado por {doc_dict['uploaded_by']} el {doc_dict['uploaded_at']})*")
                    with col_doc2:
                        if os.path.exists(filepath):
                            with open(filepath, "rb") as f_in:
                                btn_bytes = f_in.read()
                            st.download_button(
                                label="📥 Descargar",
                                data=btn_bytes,
                                file_name=doc_dict['filename'],
                                key=f"dl_doc_{doc_dict['id']}_{proj_id}",
                                use_container_width=True
                            )
                        else:
                            st.caption("⚠️ Demo (No descargable)")
            else:
                st.caption("No se han adjuntado archivos técnicos aún.")
                
            puedo_subir = False
            if role == "Admin/Director":
                puedo_subir = True
            elif "Ventas" in role and p['current_stage'] == 1:
                puedo_subir = True
            elif "Líder Regional" in role and p['current_stage'] == 3:
                puedo_subir = True
            elif "Analista de Costos" in role and p['current_stage'] == 4:
                puedo_subir = True
                
            if puedo_subir:
                subidor = st.file_uploader(f"Subir entregable oficial para Etapa {p['current_stage']}:", key=f"f_{proj_id}_{st.session_state.uploader_key_suffix}")
                if subidor is not None:
                    # Guardado físico de archivos
                    UPLOAD_DIR = "uploaded_files"
                    if not os.path.exists(UPLOAD_DIR):
                        os.makedirs(UPLOAD_DIR)
                    
                    file_bytes = subidor.read()
                    safe_filename = f"{proj_id}_{p['current_stage']}_{subidor.name}"
                    filepath = os.path.join(UPLOAD_DIR, safe_filename)
                    with open(filepath, "wb") as f_out:
                        f_out.write(file_bytes)
                        
                    run_query('''
                        INSERT INTO documents (project_id, filename, uploaded_by, uploaded_at, stage)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (proj_id, subidor.name, st.session_state.full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), p['current_stage']), is_select=False)
                    
                    log_audit(proj_id, st.session_state.full_name, role, f"Subió archivo oficial en Etapa {p['current_stage']}: '{subidor.name}'")
                    st.success("¡Archivo físico guardado y registrado exitosamente!")
                    st.session_state.uploader_key_suffix += 1
                    st.rerun()

            # =========================================
            # ⚙️ REVISIÓN CON LA DIRECCIÓN COMERCIAL (Estatus pasivo)
            # =========================================
            if p['current_stage'] < 5:
                st.markdown("#### ⚙️ Gobernanza y Aprobación de Dirección Comercial")
                if p['director_review_required'] == 1:
                    st.success("✅ **Revisión Obligatoria Activa:** Este proyecto fue configurado desde su creación para requerir la aprobación y firma del Director Comercial en la Etapa 4 antes de proceder con el Cierre Comercial.")
                else:
                    st.info("ℹ️ **Revisión de Dirección:** Este proyecto NO requiere la aprobación especial de Dirección Comercial para finalizar su cotización.")

            # =========================================
            # FORMULARIO DE CIERRE (Etapa 5) - ADMIN ONLY
            # =========================================
            if p['current_stage'] == 5 and p['status'] == 'Activo':
                st.markdown("<div style='background-color:#e6f4ea; padding:15px; border-radius:8px; border-left:5px solid #2ecc71; margin-top:15px;'>", unsafe_allow_html=True)
                st.write("### 🏆 Registrar Resultado Comercial (Exclusivo Administrador)")
                
                if role != "Admin/Director":
                    st.warning("🔒 El registro del resultado comercial final es exclusivo del Administrador/Director General. Ventas puede ver las condiciones pero no registrar el cierre.")
                    st.write(f"**Monto de Cotización Final Calculado:** ${p['total_amount']:,.2f}")
                    st.write("Estatus: Esperando firma de cierre del Director.")
                else:
                    with st.form(f"f_cierre_{proj_id}"):
                        st.write("La cotización ha concluido todas las fases técnicas. Indica los resultados:")
                        c_entregado = st.radio("¿Se entregó formalmente la propuesta al cliente?", ["Sí", "No"], horizontal=True)
                        c_resultado = st.radio("¿Se ganó o se perdió el proyecto?", ["Ganado", "Perdido", "En Espera / Negociación"], horizontal=True)
                        c_monto = st.number_input("Monto de Cierre Real ($):", min_value=0.0, value=p['total_amount'])
                        c_motivo = st.selectbox("En caso de pérdida, ¿cuál fue el factor de descarte?:", 
                                                ["N/A", "Fuera de precio (alto)", "Tiempo de entrega lento", "No cumplíamos técnicamente", "Relación comercial con competencia"])
                        c_desfase = st.number_input("Porcentaje de desfase (%):", min_value=0.0, max_value=100.0, value=float(p.get('lose_percentage_gap', 0.0) or 0.0), help="¿Qué porcentaje por encima del precio ganador de la competencia estuvimos?")
                        c_observaciones = st.text_area("Observaciones y Notas de Cierre Comercial:", value=p.get('observations', '') or "")
                        
                        submit_cierre = st.form_submit_button("Guardar y Archivar Cotización")
                        if submit_cierre:
                            status_final = "Activo"
                            if c_resultado == "Ganado":
                                status_final = "Ganado"
                                motivo_final = None
                                desfase_final = 0.0
                            elif c_resultado == "Perdido":
                                status_final = "Perdido"
                                motivo_final = c_motivo
                                desfase_final = c_desfase
                            else:
                                status_final = "Activo"
                                motivo_final = None
                                desfase_final = 0.0
                                
                            run_query('''
                                UPDATE projects 
                                SET status = ?, total_amount = ?, lose_reason = ?, lose_percentage_gap = ?, observations = ? 
                                WHERE id = ?
                            ''', (status_final, c_monto, motivo_final, desfase_final, c_observaciones, proj_id), is_select=False)
                            
                            log_audit(proj_id, st.session_state.full_name, role, f"Cerró cotización comercial. Resultado: {status_final} por ${c_monto:,.2f} (Desfase: {desfase_final}%)")
                            st.success("¡Datos guardados! El proyecto se ha archivado de forma inmutable.")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # --- DESCARGA DE REPORTE INDIVIDUAL (DOSSIER DE OBRA) ---
            st.markdown("#### 📥 Ficha de Trazabilidad Total")
            txt_reporte = generar_reporte_proyecto(p)
            st.download_button(
                label="📥 Descargar Dossier y Trazabilidad de esta Obra (TXT)",
                data=txt_reporte,
                file_name=f"Reporte_Trazabilidad_{p['name'].replace(' ', '_')}.txt",
                mime="text/plain",
                key=f"dl_rep_{proj_id}"
            )

            # ELIMINAR PROYECTO (Solo Admin)
            if role == "Admin/Director":
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar Proyecto Definitivamente", key=f"del_{proj_id}", type="secondary"):
                    eliminar_proyecto(proj_id)
                    st.success(f"¡El proyecto '{p['name']}' y todos sus registros asociados han sido eliminados de raíz!")
                    st.rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MODULO: AGENDA DE TRABAJOS (Para todos los usuarios)
# ==========================================
if "📅 Agenda de Trabajos" in tab_index:
    with tab_index["📅 Agenda de Trabajos"]:
        st.subheader("📅 Agenda de Trabajos y Carga de Actividades")
        st.write("Visualiza en tiempo real en qué están trabajando todos los miembros del equipo y sus tareas pendientes:")
        
        # Query all active projects
        active_projects = run_query("SELECT id, name, client, zone, current_stage, assigned_lider, assigned_costos, target_date, status FROM projects WHERE status = 'Activo'")
        
        # Query all active tasks (not completed)
        active_tasks = run_query("""
            SELECT t.*, p.name as project_name, p.client as project_client, p.assigned_lider, p.assigned_costos
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.is_completed = 0 AND p.status = 'Activo'
        """)
        
        # Visual metrics of workload
        col_ag1, col_ag2 = st.columns([1, 2])
        
        with col_ag1:
            st.markdown("#### 👥 Tareas Pendientes por Colaborador")
            if active_tasks:
                df_active_tasks = pd.DataFrame([dict(x) for x in active_tasks])
                
                # Resolve actual names or roles
                def resolve_responsible(row):
                    r = row['assigned_role']
                    if r == "Líder Regional":
                        return row['assigned_lider']
                    elif r == "Analista de Costos":
                        return row['assigned_costos']
                    return r
                    
                df_active_tasks['Responsable'] = df_active_tasks.apply(resolve_responsible, axis=1)
                df_active_tasks['Responsable_Nombre'] = df_active_tasks['Responsable'].apply(obtener_nombre_asignado)
                df_active_tasks['Persona'] = df_active_tasks['Responsable'] + " (" + df_active_tasks['Responsable_Nombre'] + ")"
                
                df_count = df_active_tasks.groupby('Persona').size().reset_index(name='Tareas Pendientes')
                fig_count = px.bar(df_count, x='Tareas Pendientes', y='Persona', orientation='h', color='Persona', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_count.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0), height=220)
                st.plotly_chart(fig_count, use_container_width=True)
            else:
                st.info("No hay tareas pendientes en la empresa. ¡Todo al corriente!")
                
        with col_ag2:
            st.markdown("#### 📅 Próximas Entregas y Compromisos (Active SLA)")
            if active_projects:
                df_act_proj = pd.DataFrame([dict(x) for x in active_projects])
                df_act_proj['Entrega'] = pd.to_datetime(df_act_proj['target_date'])
                df_act_proj['Días Restantes'] = df_act_proj['Entrega'].apply(lambda d: (d.date() - date.today()).days)
                
                # Sort by days remaining
                df_act_proj = df_act_proj.sort_values(by='Días Restantes')
                
                def format_sla_status(days):
                    if days < 0:
                        return f"🔴 Atrasado ({abs(days)} días)"
                    elif days <= 3:
                        return f"🟡 Crítico ({days} días)"
                    else:
                        return f"🟢 A tiempo ({days} días)"
                        
                df_act_proj['SLA / Estatus'] = df_act_proj['Días Restantes'].apply(format_sla_status)
                
                etapas_nombres = {
                    1: "1. Levantamiento Técnico",
                    2: "2. Reunión & Minuta",
                    3: "3. Elaboración Catálogo",
                    4: "4. Presupuestación",
                    5: "5. Cierre Comercial"
                }
                df_act_proj['Etapa_Txt'] = df_act_proj['current_stage'].map(etapas_nombres)
                df_proj_view = df_act_proj[['name', 'client', 'zone', 'Etapa_Txt', 'target_date', 'SLA / Estatus']].copy()
                df_proj_view.columns = ["Obra / Proyecto", "Cliente", "Zona/Región", "Etapa", "Fecha Límite", "Estatus SLA"]
                st.dataframe(df_proj_view, use_container_width=True, hide_index=True)
            else:
                st.info("No hay proyectos activos en este momento.")
                
        st.markdown("#### 📝 Detalle de Tareas Técnicas y Responsabilidades en Curso")
        if active_tasks:
            df_tasks_table = pd.DataFrame([dict(x) for x in active_tasks])
            
            def resolve_responsible_tbl(row):
                r = row['assigned_role']
                if r == "Líder Regional":
                    return row['assigned_lider']
                elif r == "Analista de Costos":
                    return row['assigned_costos']
                return r
                
            df_tasks_table['Responsable'] = df_tasks_table.apply(resolve_responsible_tbl, axis=1)
            df_tasks_table['Nombre'] = df_tasks_table['Responsable'].apply(obtener_nombre_asignado)
            df_tasks_table['Fecha_Inicio'] = pd.to_datetime(df_tasks_table['created_at'])
            df_tasks_table['Días Transcurridos'] = df_tasks_table['Fecha_Inicio'].apply(lambda d: (date.today() - d.date()).days)
            
            # Translate titles
            def translate_task_title(title):
                if "Confirmar levantamiento técnico completo" in title: return "Levantamiento técnico completo y entregado en el sistema"
                if "Confirmar recepción y validación técnica del levantamiento" in title: return "Confirmar recepción de levantamiento completo y validación técnica"
                if "Confirmar realización de reunión de alineación (Ventas)" in title: return "Confirmar realización de reunión de alineación y minuta de acuerdos"
                if "Confirmar realización de reunión de alineación (Líder Regional)" in title: return "Confirmar realización de reunión de alineación y acuerdos de minuta"
                if "Subir catálogo de conceptos" in title: return "Catálogo de conceptos completo y cargado en el sistema"
                if "Validar catálogo" in title: return "Catálogo de conceptos revisado, completo y validado para presupuestar"
                if "Vaciar catálogo de conceptos" in title: return "Propuesta económica y presupuesto final completado y cargado"
                if "Aprobación y Visto Bueno de Dirección Comercial" in title: return "Aprobación de Propuesta con el Director Comercial"
                return title
                
            df_tasks_table['Actividad Clara'] = df_tasks_table['title'].apply(translate_task_title)
            
            df_final_agenda = df_tasks_table[['project_name', 'Responsable', 'Nombre', 'Actividad Clara', 'created_at', 'Días Transcurridos']].copy()
            df_final_agenda.columns = ["Obra / Proyecto", "Departamento/Puesto", "Colaborador Asignado", "Tarea en Curso", "Fecha de Asignación", "Días en Espera"]
            
            st.dataframe(df_final_agenda, use_container_width=True, hide_index=True)
        else:
            st.info("No hay tareas activas registradas actualmente.")

# ==========================================
# MODULO: KANBAN VISUAL
# ==========================================
if "🗺️ Kanban Visual" in tab_index:
    with tab_index["🗺️ Kanban Visual"]:
        st.subheader("Mapa de Progreso de Obras Activas (Pipeline)")
        
        kanban_projs = run_query("SELECT * FROM projects WHERE status = 'Activo'")
        
        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        
        with col_e1:
            st.markdown("<h4 style='color:#1e3a8a; border-bottom:3px solid #1e3a8a; padding-bottom:5px;'>1. Levantamiento</h4>", unsafe_allow_html=True)
            for kp in [dict(x) for x in kanban_projs if x['current_stage'] == 1]:
                st.info(f"**{kp['name']}**  \n*Cliente:* {kp['client']}  \n*Monto:* ${kp['total_amount']:,.2f}  \n*Zona:* {kp['zone']}")
                
        with col_e2:
            st.markdown("<h4 style='color:#f39c12; border-bottom:3px solid #f39c12; padding-bottom:5px;'>2. Reunión & Minuta</h4>", unsafe_allow_html=True)
            for kp in [dict(x) for x in kanban_projs if x['current_stage'] == 2]:
                st.warning(f"**{kp['name']}**  \n*Cliente:* {kp['client']}  \n*Monto:* ${kp['total_amount']:,.2f}  \n*Zona:* {kp['zone']}")
                
        with col_e3:
            st.markdown("<h4 style='color:#2ecc71; border-bottom:3px solid #2ecc71; padding-bottom:5px;'>3. Elaboración Catálogo</h4>", unsafe_allow_html=True)
            for kp in [dict(x) for x in kanban_projs if x['current_stage'] == 3]:
                target = datetime.strptime(kp['target_date'], "%Y-%m-%d").date()
                if (target - date.today()).days < 0:
                    st.error(f"🚨 **{kp['name']}** (ATRASADO)  \n*Cliente:* {kp['client']}  \n*Zona:* {kp['zone']}")
                else:
                    st.success(f"**{kp['name']}**  \n*Cliente:* {kp['client']}  \n*Zona:* {kp['zone']}")
                
        with col_e4:
            st.markdown("<h4 style='color:#2980b9; border-bottom:3px solid #2980b9; padding-bottom:5px;'>4. Presupuestando (Costos)</h4>", unsafe_allow_html=True)
            for kp in [dict(x) for x in kanban_projs if x['current_stage'] == 4]:
                st.markdown(f"""
                <div style="background-color:#ebf5fb; padding:12px; border-radius:5px; border-left: 5px solid #2980b9; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <strong style="color:#2980b9;">{kp['name']}</strong><br/>
                    <small>Cliente: {kp['client']}</small><br/>
                    <strong>Monto: ${kp['total_amount']:,.2f}</strong><br/>
                    <small>Zona: {kp['zone']}</small>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# MODULO: CONSULTA HISTÓRICA DE TAREAS
# ==========================================
if "🔍 Consulta Histórica de Tareas" in tab_index:
    with tab_index["🔍 Consulta Histórica de Tareas"]:
        st.subheader("🔍 Panel de Visualización y Auditoría de Tareas (Solo Lectura)")
        st.write("Consulta el estado detallado de cualquier tarea del pipeline técnico o comercial de la empresa:")
        
        all_tasks_raw = run_query("""
            SELECT t.*, p.name as project_name, p.client as project_client, p.status as project_status, p.current_stage as project_stage
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            ORDER BY t.id DESC
        """)
        
        if all_tasks_raw:
            df_tasks_p = pd.DataFrame([dict(x) for x in all_tasks_raw])
            
            def calcular_estado_tarea(row):
                if row['is_completed'] == 1:
                    return "Concluida"
                elif row['project_status'] in ['Ganado', 'Perdido']:
                    return "Cancelada / Cerrada"
                else:
                    return "Abierta / En Espera"
            
            df_tasks_p['Estado Tarea'] = df_tasks_p.apply(calcular_estado_tarea, axis=1)
            df_tasks_p['Completada?'] = df_tasks_p['is_completed'].map({1: "Sí", 0: "No"})
            
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                search_proj = st.selectbox("Filtrar por Obra / Proyecto:", ["Todos"] + sorted(list(df_tasks_p['project_name'].dropna().unique())))
            with col_f2:
                search_role = st.selectbox("Filtrar por Responsable:", ["Todos"] + sorted(list(df_tasks_p['assigned_role'].dropna().unique())))
            with col_f3:
                search_status = st.selectbox("Filtrar por Estatus:", ["Todas", "Abierta / En Espera", "Concluida"])
                
            df_filtered = df_tasks_p.copy()
            if search_proj != "Todos":
                df_filtered = df_filtered[df_filtered['project_name'] == search_proj]
            if search_role != "Todos":
                df_filtered = df_filtered[df_filtered['assigned_role'] == search_role]
            if search_status != "Todas":
                df_filtered = df_filtered[df_filtered['Estado Tarea'] == search_status]
                
            df_view = df_filtered[["project_name", "title", "assigned_role", "Completada?", "Estado Tarea", "completed_by", "completed_at"]].copy()
            df_view.columns = ["Obra / Proyecto", "Descripción de Tarea", "Responsable Asignado", "¿Completada?", "Estatus actual", "Completada Por", "Fecha de Cierre"]
            
            st.dataframe(df_view, use_container_width=True)
        else:
            st.info("No hay tareas registradas en el sistema todavía.")

# ==========================================
# MODULO: GESTIÓN DE USUARIOS (Solo Admin)
# ==========================================
if "👥 Gestión de Usuarios" in tab_index:
    with tab_index["👥 Gestión de Usuarios"]:
        st.subheader("👥 Gestión de Accesos y Logins")
        st.write("Crea, administra y elimina cuentas de usuario para tus colaboradores. Los cambios son instantáneos:")
        
        with st.expander("➕ Registrar Nuevo Usuario"):
            with st.form("form_nuevo_usuario"):
                new_user = st.text_input("Nombre de Usuario (Ej: carlos.perez):").strip().lower()
                new_pass = st.text_input("Contraseña de Acceso:", type="password")
                new_fullname = st.text_input("Nombre Completo:")
                new_role = st.selectbox("Puesto / Rol en el Flujo:", [
                    "Admin/Director", 
                    "Ventas", 
                    "Líder Regional - Sur", 
                    "Líder Regional - Norte", 
                    "Analista de Costos Jefe", 
                    "Analista de Costos Junior 1", 
                    "Analista de Costos Junior 2",
                    "Ingeniero"
                ])
                
                submit_user = st.form_submit_button("Dar de Alta Usuario")
                if submit_user and new_user and new_pass and new_fullname:
                    exists = run_query("SELECT COUNT(*) as count FROM users WHERE username = ?", (new_user,))
                    if exists[0]['count'] > 0:
                        st.error("⚠️ Este nombre de usuario ya existe en el sistema.")
                    else:
                        run_query("INSERT INTO users VALUES (?, ?, ?, ?)", (new_user, new_pass, new_role, new_fullname), is_select=False)
                        st.success(f"¡El usuario '{new_fullname}' (`{new_user}`) ha sido creado de forma segura!")
                        st.rerun()
        
        usuarios = run_query("SELECT username, role, full_name FROM users")
        if usuarios:
            df_users = pd.DataFrame([dict(u) for u in usuarios])
            df_users.columns = ["Usuario", "Rol en Sistema", "Nombre Completo"]
            st.dataframe(df_users, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🗑️ Eliminar Usuario")
            cuentas_disponibles = [u['username'] for u in usuarios if u['username'] != st.session_state.user_name]
            
            if cuentas_disponibles:
                user_to_delete = st.selectbox("Selecciona la cuenta que deseas eliminar permanentemente:", cuentas_disponibles)
                confirm_delete = st.button("Eliminar Cuenta del Sistema", type="secondary")
                if confirm_delete:
                    run_query("DELETE FROM users WHERE username = ?", (user_to_delete,), is_select=False)
                    st.success(f"¡La cuenta de usuario `{user_to_delete}` ha sido eliminada con éxito!")
                    st.rerun()
            else:
                st.caption("No puedes eliminar tu propia cuenta mientras tengas la sesión activa.")
                
        st.markdown("---")
        st.markdown("### 🚨 Configuración de Seguridad y Limpieza Completa")
        with st.expander("⚠️ RESTABLECER BASE DE DATOS POR COMPLETO", expanded=False):
            st.warning("⚠️ Esta acción es irreversible y borrará absolutamente todo: todas las obras, entregables físicos, bitácoras de auditoría, tareas e historiales, dejando el pipeline en cero absoluto ($0.00). IMPORTANTE: Las cuentas de usuario registradas NO serán eliminadas de la base de datos, conservando todos los accesos del equipo.")
            modo_restablecer = st.radio("Elige el estado inicial tras el reseteo:", ["Dejar en Cero Absoluto ($0.00 pesos y vacío)", "Volver a inyectar proyectos muestra (Demos)"], key="mode_reset")
            
            confirmar_purga = st.button("💥 EFECTUAR REESTABLECIMIENTO DEL SISTEMA", type="primary")
            if confirmar_purga:
                if modo_restablecer == "Dejar en Cero Absoluto ($0.00 pesos y vacío)":
                    restabelecer_base_de_datos(incluir_demos=False)
                    st.success("¡Base de datos limpiada por completo! El sistema está en cero absoluto ($0.00).")
                else:
                    restabelecer_base_de_datos(incluir_demos=True)
                    st.success("¡Base de datos reestablecida e inicializada con proyectos demo de prueba!")
                st.rerun()

# ==========================================
# MODULO: AUDITORÍA COMPLETA
# ==========================================
if "📜 Auditoría Completa" in tab_index:
    with tab_index["📜 Auditoría Completa"]:
        st.subheader("Bitácora de Trazabilidad Total (Audit Trail)")
        st.write("Registro inmutable de todas las acciones efectuadas en el sistema:")
        
        logs = run_query('''
            SELECT a.*, p.name as project_name 
            FROM audit_log a
            LEFT JOIN projects p ON a.project_id = p.id
            ORDER BY a.id DESC
        ''')
        
        if logs:
            df_logs = pd.DataFrame([dict(l) for l in logs])
            df_logs.columns = ["ID Log", "ID Proy.", "Usuario", "Rol", "Acción Realizada", "Fecha y Hora", "Obra / Proyecto"]
            st.dataframe(df_logs[["Fecha y Hora", "Obra / Proyecto", "Usuario", "Rol", "Acción Realizada"]], use_container_width=True)
        else:
            st.info("No hay registros en la bitácora aún.")
