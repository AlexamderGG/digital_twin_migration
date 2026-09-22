import os
from groq import Groq
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from io import BytesIO

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# ReportLab para PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# python-docx para Word
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

# openpyxl / xlsxwriter para Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import LineChart, BarChart, Reference

from config import Config

logger = logging.getLogger(__name__)

# 1. Inicializar el cliente de Groq a nivel de módulo
try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"No se pudo inicializar Groq: {e}")
    groq_client = None

class ReportGenerator:
    """Generador de reportes en múltiples formatos"""
    
    def __init__(self, datos_reporte: Dict[str, Any]):
        """
        Args:
            datos_reporte: Diccionario con toda la información del reporte
                - titulo: str
                - subtitulo: str
                - especie: str
                - escenario: str
                - fecha_generacion: datetime
                - autor: str
                - resumen_ejecutivo: str
                - metricas: Dict[str, Any]
                - df_metricas: pd.DataFrame (con columnas: año, estatico_pc, dinamico_pc, etc.)
                - mejora_promedio: float
                - hipotesis_soportada: bool
                - recomendaciones: List[str]
                - graficos: Dict[str, plt.Figure]
        """
        self.datos = datos_reporte
        self.fecha = datos_reporte.get('fecha_generacion', datetime.now())

        self.idioma = datos_reporte.get('idioma', 'es')
        self._traducir_textos_dinamicos()
    
    def _traducir(self, texto_original: str) -> str:
        """Método interno para traducir usando Groq"""
        if self.idioma == "es" or not groq_client or not texto_original:
            return texto_original
            
        idiomas = {"en": "inglés"}
        idioma_dest = idiomas.get(self.idioma, "inglés")
        
        prompt = f"""Traduce el siguiente texto técnico sobre conectividad ecológica y cambio climático al {idioma_dest}. 
        Mantén el tono formal y académico. Devuelve ÚNICAMENTE el texto traducido, sin introducciones ni comentarios adicionales.
        
        Texto a traducir:
        {texto_original}"""

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192", 
                temperature=0.3,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error en la traducción con Groq: {e}")
            return texto_original

    def _traducir_textos_dinamicos(self):
        """Sobrescribe los datos en memoria con sus versiones traducidas antes de generar los PDFs/Words"""
        if self.idioma == "es":
            return # No perdemos tiempo si es español
            
        logger.info("Traduciendo contenido dinámico del reporte...")
        
        # Traducimos el resumen ejecutivo
        if 'resumen_ejecutivo' in self.datos:
            self.datos['resumen_ejecutivo'] = self._traducir(self.datos['resumen_ejecutivo'])
            
        # Traducimos las recomendaciones (iterando la lista)
        if 'recomendaciones' in self.datos:
            self.datos['recomendaciones'] = [self._traducir(rec) for rec in self.datos['recomendaciones']]
            
        # Traducimos la conclusión (que generabas manualmente)
        mejora = self.datos.get('mejora_promedio', 0)
        hipotesis = self.datos.get('hipotesis_soportada', False)
        conclusion_base = f"El análisis comparativo demuestra que la planificación adaptativa {'mejora significativamente' if hipotesis else 'presenta ventajas en'} la conectividad, alcanzando una mejora promedio del {mejora:.2f}%."
        
        self.datos['conclusion_traducida'] = self._traducir(conclusion_base)
    # =========================================================================
    # GENERACIÓN DE PDF
    # =========================================================================
    
    def generar_pdf(self, ruta_salida: Path) -> Path:
        """Genera reporte en formato PDF"""
        logger.info(f"Generando reporte PDF: {ruta_salida}")
        
        doc = SimpleDocTemplate(
            str(ruta_salida),
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        
        elementos = []
        estilos = getSampleStyleSheet()
        
        # Estilos personalizados
        estilo_titulo = ParagraphStyle(
            'TituloPersonalizado', parent=estilos['Title'],
            fontSize=20, textColor=colors.HexColor('#1a5276'),
            spaceAfter=20, alignment=TA_CENTER
        )
        estilo_subtitulo = ParagraphStyle(
            'Subtitulo', parent=estilos['Heading2'],
            fontSize=14, textColor=colors.HexColor('#2874a6'),
            spaceAfter=15, alignment=TA_CENTER
        )
        estilo_seccion = ParagraphStyle(
            'Seccion', parent=estilos['Heading2'],
            fontSize=14, textColor=colors.HexColor('#1a5276'),
            spaceBefore=15, spaceAfter=10
        )
        estilo_cuerpo = ParagraphStyle(
            'Cuerpo', parent=estilos['Normal'],
            fontSize=10, leading=14, alignment=TA_JUSTIFY,
            spaceAfter=8
        )
        
        # --- PORTADA ---
        elementos.append(Spacer(1, 3*cm))
        elementos.append(Paragraph("GEMELO DIGITAL DE CORREDORES DE MIGRACIÓN", estilo_titulo))
        elementos.append(Paragraph("DE ESPECIES BAJO CAMBIO CLIMÁTICO", estilo_subtitulo))
        elementos.append(Spacer(1, 1*cm))
        elementos.append(Paragraph(self.datos.get('titulo', 'Reporte de Simulación'), 
                                  ParagraphStyle('T', parent=estilo_titulo, fontSize=16)))
        elementos.append(Spacer(1, 2*cm))
        
        # Tabla de información
        info_data = [
            ['Especie:', self.datos.get('especie', 'N/A')],
            ['Escenario Climático:', self.datos.get('escenario', 'N/A')],
            ['Fecha de Generación:', self.fecha.strftime('%d/%m/%Y %H:%M')],
            ['Autor:', self.datos.get('autor', 'Sistema Gemelo Digital')],
            ['Versión:', Config.APP_VERSION]
        ]
        tabla_info = Table(info_data, colWidths=[5*cm, 10*cm])
        tabla_info.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eaf2f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#aed6f1'))
        ]))
        elementos.append(tabla_info)
        
        elementos.append(PageBreak())
        
        # --- RESUMEN EJECUTIVO ---
        elementos.append(Paragraph("1. Resumen Ejecutivo", estilo_seccion))
        elementos.append(Paragraph(
            self.datos.get('resumen_ejecutivo', 
                         'Este reporte presenta los resultados de la simulación de conectividad funcional.'),
            estilo_cuerpo
        ))
        
        # Resultados clave
        mejora = self.datos.get('mejora_promedio', 0)
        hipotesis = self.datos.get('hipotesis_soportada', False)
        
        elementos.append(Spacer(1, 0.5*cm))
        elementos.append(Paragraph("<b>Resultados Clave:</b>", estilo_cuerpo))
        
        resultados_clave = [
            f"Mejora promedio en conectividad (PC): <b>{mejora:.2f}%</b>",
            f"Hipótesis principal (≥25% mejora): <b>{'SOPORTADA' if hipotesis else 'NO SOPORTADA'}</b>",
            f"Periodo de simulación: {self.datos.get('año_inicio', 2024)} - {self.datos.get('año_fin', 2050)}",
            f"Diseño evaluado: Estático vs Dinámico"
        ]
        
        elementos.append(ListFlowable(
            [ListItem(Paragraph(r, estilo_cuerpo)) for r in resultados_clave],
            bulletType='bullet', leftIndent=20
        ))
        
        # --- MÉTRICAS ---
        elementos.append(PageBreak())
        elementos.append(Paragraph("2. Métricas de Conectividad", estilo_seccion))
        
        if 'df_metricas' in self.datos:
            df = self.datos['df_metricas']
            
            # Tabla resumen anual
            elementos.append(Paragraph("2.1 Evolución Anual", 
                                      ParagraphStyle('S', parent=estilos['Heading3'], fontSize=12)))
            
            # Preparar datos para tabla
            columnas_mostrar = ['año', 'estatico_pc', 'dinamico_pc', 'estatico_iic', 'dinamico_iic']
            cols_existentes = [c for c in columnas_mostrar if c in df.columns]
            
            if cols_existentes:
                tabla_data = [['Año', 'PC Estático', 'PC Dinámico', 'IIC Estático', 'IIC Dinámico']]
                for _, row in df[cols_existentes].iterrows():
                    tabla_data.append([
                        str(int(row['año'])),
                        f"{row.get('estatico_pc', 0):.4f}",
                        f"{row.get('dinamico_pc', 0):.4f}",
                        f"{row.get('estatico_iic', 0):.4f}",
                        f"{row.get('dinamico_iic', 0):.4f}"
                    ])
                
                tabla_res = Table(tabla_data, colWidths=[2.5*cm]*5)
                tabla_res.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), 
                     [colors.white, colors.HexColor('#f4f6f7')])
                ]))
                elementos.append(tabla_res)
        
        # --- GRÁFICOS ---
        elementos.append(PageBreak())
        elementos.append(Paragraph("3. Análisis Gráfico", estilo_seccion))
        
        if 'graficos' in self.datos:
            for nombre_grafico, figura in self.datos['graficos'].items():
                if isinstance(figura, plt.Figure):
                    # Guardar figura temporalmente
                    ruta_temp = Config.TEMP_DIR / f"grafico_{nombre_grafico}.png"
                    figura.savefig(ruta_temp, dpi=150, bbox_inches='tight', facecolor='white')
                    
                    img = Image(str(ruta_temp))
                    original_w, original_h = img.drawWidth, img.drawHeight
                    aspect = original_w / original_h
                    max_width = 16 * cm
                    
                    if original_w > max_width:
                        img.drawWidth = max_width
                        img.drawHeight = max_width / aspect
                    
                    elementos.append(Paragraph(f"<b>{nombre_grafico}</b>", 
                                              ParagraphStyle('G', parent=estilos['Normal'],
                                                            fontSize=11, spaceAfter=5)))
                    elementos.append(img)
                    elementos.append(Spacer(1, 0.5*cm))
        
        # --- RECOMENDACIONES ---
        elementos.append(PageBreak())
        elementos.append(Paragraph("4. Recomendaciones", estilo_seccion))
        
        recomendaciones = self.datos.get('recomendaciones', [
            'Implementar corredores dinámicos con revisión anual.',
            'Monitorear continuamente el cambio climático y de uso del suelo.',
            'Integrar datos de telemetría para calibración empírica.',
            'Priorizar corredores con mayor importancia de corriente.',
            'Establecer programas de ciencia ciudadana para validación.'
        ])
        
        elementos.append(ListFlowable(
            [ListItem(Paragraph(r, estilo_cuerpo)) for r in recomendaciones],
            bulletType='bullet', leftIndent=20
        ))
        
        # --- CONCLUSIONES ---
        elementos.append(Spacer(1, 1*cm))
        elementos.append(Paragraph("5. Conclusiones", estilo_seccion))
        
        conclusion_texto = f"""
        El análisis comparativo entre el diseño estático y el diseño dinámico de corredores 
        ecológicos demuestra que la planificación adaptativa basada en gemelo digital 
        {'mejora significativamente' if hipotesis else 'presenta ventajas en'} la conectividad 
        funcional, alcanzando una mejora promedio del <b>{mejora:.2f}%</b>. 
        Estos resultados respaldan la necesidad de transitar hacia enfoques de planificación 
        que consideren explícitamente la dinámica del paisaje bajo escenarios de cambio climático.
        """
        elementos.append(Paragraph(conclusion_texto, estilo_cuerpo))
        
        # Construir PDF
        doc.build(elementos)
        logger.info(f"Reporte PDF generado: {ruta_salida}")
        return ruta_salida
    
    # =========================================================================
    # GENERACIÓN DE WORD
    # =========================================================================
    
    def generar_word(self, ruta_salida: Path) -> Path:
        """Genera reporte en formato Word (.docx)"""
        logger.info(f"Generando reporte Word: {ruta_salida}")
        
        doc = Document()
        
        # Configurar estilo por defecto
        estilo_normal = doc.styles['Normal']
        estilo_normal.font.name = 'Calibri'
        estilo_normal.font.size = Pt(11)
        
        # --- PORTADA ---
        titulo = doc.add_heading('GEMELO DIGITAL DE CORREDORES DE MIGRACIÓN', level=0)
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        subtitulo = doc.add_heading('DE ESPECIES BAJO CAMBIO CLIMÁTICO', level=1)
        subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()
        p = doc.add_heading(self.datos.get('titulo', 'Reporte de Simulación'), level=2)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Tabla de información
        tabla = doc.add_table(rows=5, cols=2)
        tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        tabla.style = 'Light Grid Accent 1'
        
        info = [
            ('Especie:', self.datos.get('especie', 'N/A')),
            ('Escenario:', self.datos.get('escenario', 'N/A')),
            ('Fecha:', self.fecha.strftime('%d/%m/%Y %H:%M')),
            ('Autor:', self.datos.get('autor', 'Sistema')),
            ('Versión:', Config.APP_VERSION)
        ]
        
        for i, (etiqueta, valor) in enumerate(info):
            tabla.rows[i].cells[0].text = etiqueta
            tabla.rows[i].cells[1].text = valor
        
        doc.add_page_break()
        
        # --- RESUMEN EJECUTIVO ---
        doc.add_heading('1. Resumen Ejecutivo', level=1)
        doc.add_paragraph(self.datos.get('resumen_ejecutivo', 'Resumen ejecutivo del reporte.'))
        
        mejora = self.datos.get('mejora_promedio', 0)
        hipotesis = self.datos.get('hipotesis_soportada', False)
        
        doc.add_paragraph()
        doc.add_paragraph('Resultados Clave:', style='List Bullet')
        doc.add_paragraph(f'Mejora promedio en conectividad: {mejora:.2f}%', style='List Bullet 2')
        doc.add_paragraph(
            f'Hipótesis principal (≥25%): {"SOPORTADA" if hipotesis else "NO SOPORTADA"}',
            style='List Bullet 2'
        )
        
        # --- MÉTRICAS ---
        doc.add_page_break()
        doc.add_heading('2. Métricas de Conectividad', level=1)
        
        if 'df_metricas' in self.datos:
            df = self.datos['df_metricas']
            
            doc.add_heading('2.1 Evolución Anual', level=2)
            
            cols = ['año', 'estatico_pc', 'dinamico_pc', 'estatico_iic', 'dinamico_iic']
            cols = [c for c in cols if c in df.columns]
            
            if cols:
                tabla_m = doc.add_table(rows=len(df) + 1, cols=len(cols))
                tabla_m.style = 'Light Grid Accent 1'
                
                # Encabezados
                encabezados = ['Año', 'PC Estático', 'PC Dinámico', 'IIC Estático', 'IIC Dinámico']
                for i, enc in enumerate(encabezados[:len(cols)]):
                    celda = tabla_m.rows[0].cells[i]
                    celda.text = enc
                    for run in celda.paragraphs[0].runs:
                        run.bold = True
                
                # Datos
                for idx, (_, row) in enumerate(df[cols].iterrows()):
                    fila = tabla_m.rows[idx + 1].cells
                    fila[0].text = str(int(row['año']))
                    if 'estatico_pc' in cols:
                        fila[1].text = f"{row.get('estatico_pc', 0):.4f}"
                    if 'dinamico_pc' in cols:
                        fila[2].text = f"{row.get('dinamico_pc', 0):.4f}"
                    if len(fila) > 3 and 'estatico_iic' in cols:
                        fila[3].text = f"{row.get('estatico_iic', 0):.4f}"
                    if len(fila) > 4 and 'dinamico_iic' in cols:
                        fila[4].text = f"{row.get('dinamico_iic', 0):.4f}"
        
        # --- GRÁFICOS ---
        doc.add_page_break()
        doc.add_heading('3. Análisis Gráfico', level=1)
        
        if 'graficos' in self.datos:
            for nombre_grafico, figura in self.datos['graficos'].items():
                if isinstance(figura, plt.Figure):
                    ruta_temp = Config.TEMP_DIR / f"word_{nombre_grafico}.png"
                    figura.savefig(ruta_temp, dpi=150, bbox_inches='tight', facecolor='white')
                    
                    doc.add_paragraph(nombre_grafico, style='Strong')
                    doc.add_picture(str(ruta_temp), width=Inches(6))
                    doc.add_paragraph()
        
        # --- RECOMENDACIONES ---
        doc.add_page_break()
        doc.add_heading('4. Recomendaciones', level=1)
        
        recomendaciones = self.datos.get('recomendaciones', [
            'Implementar corredores dinámicos con revisión anual.',
            'Monitorear continuamente el cambio climático y de uso del suelo.',
            'Integrar datos de telemetría para calibración empírica.'
        ])
        
        for rec in recomendaciones:
            doc.add_paragraph(rec, style='List Bullet')
        
        # --- CONCLUSIONES ---
        doc.add_heading('5. Conclusiones', level=1)
        doc.add_paragraph(
            f"El diseño dinámico mejora la conectividad en un {mejora:.2f}% en promedio, "
            f"{'superando' if hipotesis else 'sin alcanzar'} el umbral del 25% de la hipótesis."
        )
        
        doc.save(str(ruta_salida))
        logger.info(f"Reporte Word generado: {ruta_salida}")
        return ruta_salida
    
    # =========================================================================
    # GENERACIÓN DE EXCEL
    # =========================================================================
    
    def generar_excel(self, ruta_salida: Path) -> Path:
        """Genera reporte en formato Excel (.xlsx)"""
        logger.info(f"Generando reporte Excel: {ruta_salida}")
        
        wb = Workbook()
        
        # Estilos
        fuente_titulo = Font(name='Calibri', size=14, bold=True, color='FFFFFF')
        fuente_encabezado = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        fuente_normal = Font(name='Calibri', size=10)
        
        relleno_titulo = PatternFill(start_color='1A5276', end_color='1A5276', fill_type='solid')
        relleno_encabezado = PatternFill(start_color='2874A6', end_color='2874A6', fill_type='solid')
        relleno_par = PatternFill(start_color='EBF5FB', end_color='EBF5FB', fill_type='solid')
        
        alineacion_centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
        alineacion_izq = Alignment(horizontal='left', vertical='center', wrap_text=True)
        
        borde_fino = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        
        # --- HOJA 1: RESUMEN ---
        ws_resumen = wb.active
        ws_resumen.title = 'Resumen'
        
        ws_resumen.merge_cells('A1:D1')
        celda = ws_resumen['A1']
        celda.value = 'REPORTE DE SIMULACIÓN - GEMELO DIGITAL'
        celda.font = fuente_titulo
        celda.fill = relleno_titulo
        celda.alignment = alineacion_centro
        
        # Información general
        info = [
            ('Título', self.datos.get('titulo', '')),
            ('Especie', self.datos.get('especie', '')),
            ('Escenario', self.datos.get('escenario', '')),
            ('Fecha Generación', self.fecha.strftime('%d/%m/%Y %H:%M')),
            ('Mejora Promedio (%)', round(self.datos.get('mejora_promedio', 0), 2)),
            ('Hipótesis Soportada', 'SÍ' if self.datos.get('hipotesis_soportada') else 'NO'),
            ('Año Inicio', self.datos.get('año_inicio', 2024)),
            ('Año Fin', self.datos.get('año_fin', 2050))
        ]
        
        fila_inicio = 3
        for i, (etiqueta, valor) in enumerate(info):
            fila = fila_inicio + i
            ws_resumen.cell(row=fila, column=1, value=etiqueta).font = fuente_encabezado
            ws_resumen.cell(row=fila, column=1).fill = relleno_encabezado
            ws_resumen.cell(row=fila, column=1).border = borde_fino
            
            ws_resumen.cell(row=fila, column=2, value=valor).font = fuente_normal
            ws_resumen.cell(row=fila, column=2).border = borde_fino
        
        ws_resumen.column_dimensions['A'].width = 22
        ws_resumen.column_dimensions['B'].width = 45
        
        # --- HOJA 2: MÉTRICAS ANUALES ---
        if 'df_metricas' in self.datos:
            ws_metricas = wb.create_sheet('Métricas Anuales')
            df = self.datos['df_metricas']
            
            # Escribir encabezados
            for col, nombre_col in enumerate(df.columns, 1):
                celda = ws_metricas.cell(row=1, column=col, value=str(nombre_col))
                celda.font = fuente_encabezado
                celda.fill = relleno_encabezado
                celda.alignment = alineacion_centro
                celda.border = borde_fino
            
            # Escribir datos
            for fila_idx, (_, row) in enumerate(df.iterrows(), 2):
                for col_idx, valor in enumerate(row, 1):
                    celda = ws_metricas.cell(row=fila_idx, column=col_idx)
                    if isinstance(valor, (int, float)):
                        celda.value = round(float(valor), 6)
                    else:
                        celda.value = valor
                    celda.font = fuente_normal
                    celda.border = borde_fino
                    celda.alignment = alineacion_centro
                    
                    if fila_idx % 2 == 0:
                        celda.fill = relleno_par
            
            # Ajustar anchos de columna
            for col in range(1, len(df.columns) + 1):
                ws_metricas.column_dimensions[chr(64 + col)].width = 16
            
            # Gráfico de líneas
            if len(df) > 1 and 'año' in df.columns:
                chart = LineChart()
                chart.title = "Evolución de la Conectividad"
                chart.y_axis.title = "Valor"
                chart.x_axis.title = "Año"
                chart.height = 15
                chart.width = 25
                
                # Encontrar columna de año
                col_año = list(df.columns).index('año') + 1
                
                # Agregar series de PC
                if 'estatico_pc' in df.columns:
                    col_pc_e = list(df.columns).index('estatico_pc') + 1
                    data = Reference(ws_metricas, min_col=col_pc_e, min_row=1, 
                                    max_row=len(df) + 1)
                    cats = Reference(ws_metricas, min_col=col_año, min_row=2, 
                                    max_row=len(df) + 1)
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(cats)
                
                if 'dinamico_pc' in df.columns:
                    col_pc_d = list(df.columns).index('dinamico_pc') + 1
                    data = Reference(ws_metricas, min_col=col_pc_d, min_row=1, 
                                    max_row=len(df) + 1)
                    chart.add_data(data, titles_from_data=True)
                
                ws_metricas.add_chart(chart, f"A{len(df) + 4}")
        
        # --- HOJA 3: RECOMENDACIONES ---
        ws_rec = wb.create_sheet('Recomendaciones')
        
        ws_rec.merge_cells('A1:A1')
        celda = ws_rec['A1']
        celda.value = 'RECOMENDACIONES'
        celda.font = fuente_titulo
        celda.fill = relleno_titulo
        celda.alignment = alineacion_centro
        
        recomendaciones = self.datos.get('recomendaciones', [])
        for i, rec in enumerate(recomendaciones, 3):
            celda = ws_rec.cell(row=i, column=1, value=f"{i-2}. {rec}")
            celda.font = fuente_normal
            celda.alignment = alineacion_izq
        
        ws_rec.column_dimensions['A'].width = 100
        
        wb.save(str(ruta_salida))
        logger.info(f"Reporte Excel generado: {ruta_salida}")
        return ruta_salida
    
    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================
    
    def generar_todos(self, nombre_base: str) -> Dict[str, Path]:
        """Genera los tres formatos de reporte"""
        Config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        
        rutas = {}
        
        for formato, extension in [('PDF', 'pdf'), ('Word', 'docx'), ('Excel', 'xlsx')]:
            ruta = Config.OUTPUTS_DIR / f"{nombre_base}.{extension}"
            
            try:
                if formato == 'PDF':
                    rutas['pdf'] = self.generar_pdf(ruta)
                elif formato == 'Word':
                    rutas['word'] = self.generar_word(ruta)
                elif formato == 'Excel':
                    rutas['excel'] = self.generar_excel(ruta)
            except Exception as e:
                logger.error(f"Error generando {formato}: {e}")
        
        return rutas