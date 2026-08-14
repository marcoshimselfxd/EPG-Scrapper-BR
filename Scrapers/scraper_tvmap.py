#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os

DIAS_PARA_FRENTE = 4

def pegar_grade(url_grid=None):
    if url_grid:
        url = f'https://tvmap.com.br/api/Programacao?availWidth=2560&grid={url_grid}'
    else:
        url = 'https://tvmap.com.br/api/Programacao?availWidth=2560'
    
    r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    return r.json()

def extrair_todos():
    todos_canais = {}
    url_grid = None
    paginas = 0
    
    while paginas < 50:
        try:
            data = pegar_grade(url_grid)
        except:
            break
        
        channels = data.get('channels', [])
        
        for ch in channels:
            nome = ch.get('displayName', '')
            exhibitions = ch.get('exhibitions', [])
            if nome not in todos_canais:
                todos_canais[nome] = []
            todos_canais[nome].extend(exhibitions)
        
        next_grid = data.get('nextGridUrl', '')
        if not next_grid:
            break
        
        url_grid = next_grid
        paginas += 1
    
    return todos_canais

def gerar_xml(caminho_saida):
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    todos_canais = extrair_todos()
    print(f'Canais: {len(todos_canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper TVMap')
    
    total_eventos = 0
    
    for nome, exhibitions in sorted(todos_canais.items()):
        channel = ET.SubElement(root, 'channel')
        channel.set('id', nome)
        display = ET.SubElement(channel, 'display-name')
        display.text = nome
        
        for ex in exhibitions:
            start_str = ex.get('exhibitionStartDate', '')
            end_str = ex.get('exhibitionCalculatedEndDate', '')
            
            if not start_str or not end_str:
                continue
            
            try:
                inicio = datetime.fromisoformat(start_str).replace(tzinfo=None)
                fim = datetime.fromisoformat(end_str).replace(tzinfo=None)
            except:
                continue
            
            if inicio < hoje:
                continue
            if inicio > data_limite:
                continue
            
            p = ET.SubElement(root, 'programme')
            p.set('start', inicio.strftime('%Y%m%d%H%M%S') + ' -0300')
            p.set('stop', fim.strftime('%Y%m%d%H%M%S') + ' -0300')
            p.set('channel', nome)
            
            title = ET.SubElement(p, 'title')
            title.text = ex.get('title', '')
            
            desc_texto = ex.get('description', '')
            if desc_texto:
                desc = ET.SubElement(p, 'desc')
                desc.text = desc_texto
            
            total_eventos += 1
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Eventos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_tvmap.xml')
    gerar_xml(caminho)
