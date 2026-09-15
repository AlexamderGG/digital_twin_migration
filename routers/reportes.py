# routers/reportes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from routers.auth import get_current_user_api
from config import DatabaseConnection

router = APIRouter()

def obtener_datos_ultima_simulacion():
    """Obtiene los datos de la última simulación para armar el reporte"""
    query_sim = """
        SELECT s.id_simulacion, s.nombre, s.tipo, s.año_inicio, s.año_fin, 
               s.fecha_inicio, e.nombre_cientifico, e.nombre_comun
        FROM simulaciones s
        LEFT JOIN especies e ON s.id_especie = e.id_especie
        ORDER BY s.id_simulacion DESC LIMIT 1
    """
    simulacion = DatabaseConnection.execute_query(query_sim)
    if not simulacion:
        raise HTTPException(status_code=404, detail="No hay simulaciones registradas.")
    
    sim = simulacion[0]
    
    query_resultados = """
        SELECT año, metrica, valor, unidad 
        FROM resultados_conectividad 
        WHERE id_simulacion = :id_sim
        ORDER BY año, metrica
    """
    resultados = DatabaseConnection.execute_query(query_resultados, {"id_sim": sim['id_simulacion']})
    
    return sim, resultados

@router.get("/excel")
def descargar_excel(current_user: dict = Depends(get_current_user_api)):
    try:
        sim, resultados = obtener_datos_ultima_simulacion()
        df = pd.DataFrame(resultados)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Resultados Conectividad', index=False)
            
            # Pestaña de metadatos
            meta_df = pd.DataFrame([sim])
            meta_df.to_excel(writer, sheet_name='Metadatos', index=False)
            
        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Reporte_Simulacion_{sim['id_simulacion']}.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/word")
def descargar_word(current_user: dict = Depends(get_current_user_api)):
    try:
        sim, resultados = obtener_datos_ultima_simulacion()
        
        doc = Document()
        doc.add_heading('Reporte de Simulación de Conectividad', 0)
        
        doc.add_heading('Datos Generales', level=1)
        doc.add_paragraph(f"Nombre: {sim['nombre']}")
        doc.add_paragraph(f"Especie: {sim['nombre_cientifico']} ({sim['nombre_comun']})")
        doc.add_paragraph(f"Periodo: {sim['año_inicio']} - {sim['año_fin']}")
        
        doc.add_heading('Resultados Anuales', level=1)
        
        if resultados:
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Año'
            hdr_cells[1].text = 'Métrica'
            hdr_cells[2].text = 'Valor'
            hdr_cells[3].text = 'Unidad'
            
            for res in resultados:
                row_cells = table.add_row().cells
                row_cells[0].text = str(res['año'])
                row_cells[1].text = str(res['metrica']).replace('_', ' ').title()
                row_cells[2].text = f"{res['valor']:.4f}"
                row_cells[3].text = str(res['unidad'])

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Reporte_Simulacion_{sim['id_simulacion']}.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pdf")
def descargar_pdf(current_user: dict = Depends(get_current_user_api)):
    try:
        sim, resultados = obtener_datos_ultima_simulacion()
        output = io.BytesIO()
        
        doc = SimpleDocTemplate(output, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("Reporte de Simulación - Gemelo Digital", styles['Title']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph(f"**Simulación:** {sim['nombre']}", styles['Normal']))
        story.append(Paragraph(f"**Especie:** {sim['nombre_cientifico']}", styles['Normal']))
        story.append(Paragraph(f"**Periodo:** {sim['año_inicio']} - {sim['año_fin']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        if resultados:
            data = [["Año", "Métrica", "Valor", "Unidad"]]
            for res in resultados:
                data.append([
                    str(res['año']), 
                    str(res['metrica']).replace('_', ' ').title(), 
                    f"{res['valor']:.4f}", 
                    str(res['unidad'])
                ])
                
            tabla = Table(data, colWidths=[60, 150, 100, 80])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')), # Verde esmeralda
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(tabla)
            
        doc.build(story)
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Reporte_Simulacion_{sim['id_simulacion']}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))