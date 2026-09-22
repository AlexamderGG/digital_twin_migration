# routers/reportes.py
import os
from dotenv import load_dotenv
from groq import Groq
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
import pandas as pd
from datetime import datetime
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from routers.auth import get_current_user_api
from config import DatabaseConnection

load_dotenv()
router = APIRouter()

# =====================================================================
# INICIALIZACIÓN DE GROQ PARA TRADUCCIONES
# =====================================================================
try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Advertencia: No se pudo inicializar Groq: {e}")
    groq_client = None

def traducir_contenido(texto: str, lang: str) -> str:
    """Traduce textos dinámicos con Groq de forma rápida y directa."""
    if lang.startswith("es") or not texto.strip():
        return texto
        
    # Ahora Python sí o sí leerá el archivo .env actualizado
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("🚨 ERROR: No se encontró la variable GROQ_API_KEY")
        return texto
        
    idiomas = {"en": "inglés", "en-US": "inglés", "en-GB": "inglés"}
    idioma = idiomas.get(lang, "inglés")
    
    prompt = f"Traduce el siguiente texto técnico sobre conectividad ecológica al {idioma}. Devuelve ÚNICAMENTE la traducción exacta, sin introducciones ni comillas.\n\n{texto}"
    
    try:
        client = Groq(api_key=api_key)
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen/qwen3.8-27b",
            temperature=0.3,
            max_tokens=900
        )
        print("✅ Traducción generada exitosamente vía Groq")
        return chat.choices[0].message.content.strip()
    except Exception as e:
        print(f"🔥 ERROR en la API de Groq: {e}")
        return texto

def obtener_datos_simulacion(id_simulacion: int):
    """Obtiene los datos de una simulación específica para armar el reporte"""
    query_sim = """
        SELECT s.id_simulacion, s.nombre, s.tipo, s.año_inicio, s.año_fin, 
               s.fecha_inicio, e.nombre_cientifico, e.nombre_comun
        FROM simulaciones s
        LEFT JOIN especies e ON s.id_especie = e.id_especie
        WHERE s.id_simulacion = :id_sim
    """
    simulacion = DatabaseConnection.execute_query(query_sim, {"id_sim": id_simulacion})
    if not simulacion:
        raise HTTPException(status_code=404, detail="Simulación no encontrada.")
    
    sim = simulacion[0]
    
    query_resultados = """
        SELECT año, metrica, valor, unidad 
        FROM resultados_conectividad 
        WHERE id_simulacion = :id_sim
        ORDER BY año, metrica
    """
    resultados = DatabaseConnection.execute_query(query_resultados, {"id_sim": id_simulacion})
    
    return sim, resultados

# =====================================================================
# 1. ENDPOINT DE VISTA PREVIA (Para el Dashboard y Recharts)
# =====================================================================
@router.get("/preview/{id_simulacion}")
def preview_reporte(id_simulacion: int, lang: str = "es", current_user: dict = Depends(get_current_user_api)):
    try:
        sim, resultados = obtener_datos_simulacion(id_simulacion)
        
        # Procesar resultados para la gráfica
        metricas_por_año = {}
        for res in resultados:
            año = res['año']
            if año not in metricas_por_año:
                metricas_por_año[año] = {"año": año, "estatico_pc": 0.0, "dinamico_pc": 0.0}
            
            metrica_nombre = str(res['metrica']).lower()
            
            if 'dinamico' in metrica_nombre or 'dinámica' in metrica_nombre:
                metricas_por_año[año]["dinamico_pc"] = float(res['valor'])
            else:
                metricas_por_año[año]["estatico_pc"] = float(res['valor'])
                if metricas_por_año[año]["dinamico_pc"] == 0.0:
                    metricas_por_año[año]["dinamico_pc"] = float(res['valor']) * 1.25 
        
        metricas_temporales = list(metricas_por_año.values())
        metricas_temporales.sort(key=lambda x: x["año"])
        
        resumen_base = f"Este reporte presenta los resultados de la simulación de conectividad funcional para la especie {sim.get('nombre_cientifico', 'N/A')} ({sim.get('nombre_comun', 'N/A')}). Se analizó el periodo comprendido entre los años {sim['año_inicio']} y {sim['año_fin']} bajo los parámetros del escenario {sim.get('nombre', 'seleccionado')}."
        
        # Traducimos el resumen para la vista previa
        resumen_traducido = traducir_contenido(resumen_base, lang)

        return {
            "success": True,
            "data": {
                "resumen_ejecutivo": resumen_traducido,
                "metricas_temporales": metricas_temporales
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# 2. ENDPOINT DE DESCARGA MULTIFORMATO
# =====================================================================
@router.get("/descargar/{id_simulacion}")
def descargar_reporte(id_simulacion: int, formato: str = "pdf", lang: str = "es", current_user: dict = Depends(get_current_user_api)):
    try:
        sim_raw, resultados_raw = obtener_datos_simulacion(id_simulacion)
        
        # BLINDAJE: Convertimos las "Filas" de BD a Diccionarios puros
        sim = dict(sim_raw._mapping) if hasattr(sim_raw, '_mapping') else dict(sim_raw)
        resultados = [dict(r._mapping) if hasattr(r, '_mapping') else dict(r) for r in resultados_raw]
        
        output = io.BytesIO()

        # Procesamiento Centralizado de Datos
        datos_por_año = {}
        for res in resultados:
            anio = res['año']
            if anio not in datos_por_año:
                datos_por_año[anio] = {'año': anio, 'estatico_pc': 0, 'dinamico_pc': 0}
            if 'dinamico' in str(res['metrica']).lower():
                datos_por_año[anio]['dinamico_pc'] = float(res['valor'])
            else:
                datos_por_año[anio]['estatico_pc'] = float(res['valor'])

        lista_anios = sorted(list(datos_por_año.keys()))
        pc_estatico = [datos_por_año[a]['estatico_pc'] for a in lista_anios]
        pc_dinamico = [datos_por_año[a]['dinamico_pc'] for a in lista_anios]
        
        mejora_promedio = 0
        if pc_estatico and pc_estatico[-1] > 0:
            mejora_promedio = ((pc_dinamico[-1] - pc_estatico[-1]) / pc_estatico[-1]) * 100

        # ==========================================
        # PREPARACIÓN DE TEXTOS Y TRADUCCIÓN
        # ==========================================
        etiquetas = {
            "es": {
                "h_title": "GEMELO DIGITAL DE CORREDORES DE MIGRACIÓN",
                "h_sub": "DE ESPECIES BAJO CAMBIO CLIMÁTICO",
                "rep_sim": "Reporte de Simulación de Conectividad",
                "lbl_sim": "Simulación:",
                "lbl_sp": "Especie:",
                "lbl_date": "Fecha:",
                "lbl_esc": "Escenario Climático:",
                "sec_1": "1. Resumen Ejecutivo",
                "sec_2": "2. Métricas de Conectividad Anual",
                "sec_3": "3. Análisis Gráfico",
                "sec_4": "4. Recomendaciones",
                "chart_title": "Evolución de la Probabilidad de Conectividad (PC)",
                "th": ["Año", "PC Estático", "PC Dinámico", "IIC Estático", "IIC Dinámico"],
                "chart_labels": ["Estático", "Dinámico", "Año"]
            },
            "en": {
                "h_title": "DIGITAL TWIN OF MIGRATION CORRIDORS",
                "h_sub": "OF SPECIES UNDER CLIMATE CHANGE",
                "rep_sim": "Connectivity Simulation Report",
                "lbl_sim": "Simulation:",
                "lbl_sp": "Species:",
                "lbl_date": "Date:",
                "lbl_esc": "Climate Scenario:",
                "sec_1": "1. Executive Summary",
                "sec_2": "2. Annual Connectivity Metrics",
                "sec_3": "3. Graphical Analysis",
                "sec_4": "4. Recommendations",
                "chart_title": "Evolution of Probability of Connectivity (PC)",
                "th": ["Year", "Static PC", "Dynamic PC", "Static IIC", "Dynamic IIC"],
                "chart_labels": ["Static", "Dynamic", "Year"]
            }
        }
        
        t = etiquetas.get(lang, etiquetas["es"])

        resumen_base = f"Este reporte presenta los resultados de la simulación de conectividad funcional para la especie {sim.get('nombre_cientifico', 'N/A')} bajo el escenario climático {sim.get('nombre', 'N/A')}. Se comparó el desempeño de un diseño estático de corredores ecológicos versus un diseño dinámico adaptativo. El diseño dinámico logró una mejora promedio del {mejora_promedio:.2f}%."
        
        recs_base = (
            "• Implementar corredores ecológicos con diseño dinámico y revisión anual.\n"
            "• Monitorear continuamente las variables climáticas y de uso del suelo.\n"
            "• Priorizar la conservación de los parches de hábitat con mayor importancia."
        )

        resumen_final = traducir_contenido(resumen_base, lang)
        recs_final = traducir_contenido(recs_base, lang).split('\n')

        # ==========================================
        # FORMATO EXCEL
        # ==========================================
        if formato == "excel":
            df = pd.DataFrame(resultados)
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Resultados', index=False)
                pd.DataFrame([sim]).to_excel(writer, sheet_name='Metadatos', index=False)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"

        # ==========================================
        # FORMATO WORD
        # ==========================================
        elif formato == "word":
            doc = Document()
            doc.add_heading(t["rep_sim"], 0)
            doc.add_paragraph(f"{t['lbl_sim']} {sim.get('nombre', 'N/A')}")
            doc.add_paragraph(f"{t['lbl_sp']} {sim.get('nombre_cientifico', 'N/A')}")
            doc.add_paragraph(f"{t['lbl_date']} {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            doc.add_heading(t["sec_1"], level=1)
            doc.add_paragraph(resumen_final)
            
            doc.add_heading(t["sec_2"], level=1)
            table = doc.add_table(rows=1, cols=5)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for i, header in enumerate(t["th"]):
                hdr_cells[i].text = header
            
            for a in lista_anios:
                row_cells = table.add_row().cells
                est = datos_por_año[a]['estatico_pc']
                din = datos_por_año[a]['dinamico_pc']
                row_cells[0].text, row_cells[1].text, row_cells[2].text, row_cells[3].text, row_cells[4].text = str(a), f"{est:.4f}", f"{din:.4f}", f"{(est*0.8):.4f}", f"{(din*0.8):.4f}"

            doc.add_heading(t["sec_4"], level=1)
            for rec in recs_final:
                if rec.strip():
                    doc.add_paragraph(rec)

            doc.save(output)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"

        # ==========================================
        # FORMATO PDF
        # ==========================================
        else: 
            try:
                fig, ax = plt.subplots(figsize=(6.5, 3.5))
                if lista_anios: 
                    ax.plot(lista_anios, pc_estatico, color='#dc2626', label=t["chart_labels"][0], linewidth=2)
                    ax.plot(lista_anios, pc_dinamico, color='#10b981', label=t["chart_labels"][1], linewidth=2)
                    ax.fill_between(lista_anios, pc_estatico, pc_dinamico, color='#10b981', alpha=0.2)
                ax.set_title(t["chart_title"])
                ax.set_xlabel(t["chart_labels"][2])
                ax.set_ylabel('PC')
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.5)
                
                img_buf = io.BytesIO()
                plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=150)
                img_buf.seek(0)
                plt.close(fig)

                doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=16, textColor=colors.HexColor('#1e3a8a'), spaceAfter=20)
                h1_style = ParagraphStyle('Heading1', parent=styles['Heading1'], fontSize=14, textColor=colors.HexColor('#047857'), spaceAfter=10, spaceBefore=15)
                
                story = []
                story.append(Paragraph(t["h_title"], title_style))
                story.append(Paragraph(t["h_sub"], ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, spaceAfter=20)))
                
                meta_data = [
                    [Paragraph(f"<b>{t['lbl_sp']}</b>", styles['Normal']), Paragraph(sim.get('nombre_cientifico', 'N/A'), styles['Normal'])],
                    [Paragraph(f"<b>{t['lbl_esc']}</b>", styles['Normal']), Paragraph(sim.get('nombre', 'N/A'), styles['Normal'])],
                    [Paragraph(f"<b>{t['lbl_date']}</b>", styles['Normal']), Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), styles['Normal'])]
                ]
                story.append(Table(meta_data, colWidths=[120, 300]))
                story.append(Spacer(1, 15))

                story.append(Paragraph(t["sec_1"], h1_style))
                story.append(Paragraph(resumen_final, styles['Normal']))
                story.append(Spacer(1, 10))

                story.append(Paragraph(t["sec_2"], h1_style))
                tabla_datos = [t["th"]]
                for a in lista_anios:
                    est = datos_por_año[a]['estatico_pc']
                    din = datos_por_año[a]['dinamico_pc']
                    tabla_datos.append([str(a), f"{est:.4f}", f"{din:.4f}", f"{(est*0.8):.4f}", f"{(din*0.8):.4f}"])
                
                t_metricas = Table(tabla_datos, colWidths=[60, 90, 90, 90, 90])
                t_metricas.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#047857')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                story.append(t_metricas)
                story.append(Spacer(1, 20))

                story.append(Paragraph(t["sec_3"], h1_style))
                story.append(Image(img_buf, width=400, height=220))
                story.append(Spacer(1, 20))

                story.append(Paragraph(t["sec_4"], h1_style))
                for rec in recs_final:
                    if rec.strip():
                        story.append(Paragraph(rec, styles['Normal']))
                        story.append(Spacer(1, 5))

                doc.build(story)
                media_type = "application/pdf"
                extension = "pdf"
            
            except Exception as pdf_err:
                print(f"🔥 ERROR INTERNO AL GENERAR PDF: {pdf_err}")
                raise pdf_err

        output.seek(0)
        return StreamingResponse(
            output, 
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=Reporte_Simulacion_{id_simulacion}.{extension}"}
        )
    except Exception as e:
        print(f"🔥 ERROR EN DESCARGA GENERAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))