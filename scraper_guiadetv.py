#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 7

CATEGORIAS = [
    'https://www.guiadetv.com/categorias/variedades.html',
    'https://www.guiadetv.com/categorias/tv-aberta.html',
    'https://www.guiadetv.com/categorias/noticias.html',
    'https://www.guiadetv.com/categorias/infantil.html',
    'https://www.guiadetv.com/categorias/filmes-e-series.html',
    'https://www.guiadetv.com/categorias/esportes.html',
    'https://www.guiadetv.com/categorias/documentarios.html',
]

def descobrir_canais():
    canais = {}
    for url_cat in CATEGORIAS:
        try:
            r = requests.get(url_cat, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/canal/' in href and href.startswith('http'):
                    nome_elem = a.find(['h2', 'h3'])
                    nome = nome_elem.get_text().strip() if nome_elem else ''
                    if nome and nome not in canais:
                        canais[nome] = href
        except:
            pass
    return canais

def extrair_programacao(url_canal, data_limite):
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    html = r.text
    
    datas = re.findall(r'data-dt="(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2}', html)
    titulos_blocos = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    
    titulos = []
    for bloco in titulos_blocos:
        badges = re.findall(r'badge[^>]*>\s*([^<]+?)\s*</span>', bloco, re.IGNORECASE)
        texto = re.sub(r'<[^>]+>', '', bloco)
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        tem_ao_vivo = any('AO VIVO' in b.upper() for b in badges)
        tem_vt = any('VT' in b.upper() for b in badges)
        
        for badge in badges:
            texto = texto.replace(badge.strip(), '').strip()
        
        if tem_ao_vivo:
            titulo_final = f'Ao vivo - {texto}'
        elif tem_vt:
            titulo_final = f'VT - {texto}'
        else:
            titulo_final = texto
        
        titulos.append(titulo_final)
    
    eventos = []
    for i in range(min(len(datas), len(titulos))):
        try:
            inicio = datetime.strptime(datas[i], '%Y-%m-%d %H:%M')
            if inicio <= data_limite:
                eventos.append({'inicio': inicio, 'titulo': titulos[i]})
        except:
            pass
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper GuiaDeTV')
    
    total_eventos = 0
    
    for nome, url in sorted(canais.items()):
        try:
            eventos = extrair_programacao(url, data_limite)
            if not eventos:
                continue
            
            eventos.sort(key=lambda x: x['inicio'])
            for i in range(len(eventos) - 1):
                eventos[i]['fim'] = eventos[i + 1]['inicio']
            eventos[-1]['fim'] = eventos[-1]['inicio'] + timedelta(hours=1)
            
            channel = ET.SubElement(root, 'channel')
            channel.set('id', nome)
            display = ET.SubElement(channel, 'display-name')
            display.text = nome
            
            for ev in eventos:
                prog = ET.SubElement(root, 'programme')
                prog.set('start', ev['inicio'].strftime('%Y%m%d%H%M%S -0300'))
                prog.set('stop', ev['fim'].strftime('%Y%m%d%H%M%S -0300'))
                prog.set('channel', nome)
                title = ET.SubElement(prog, 'title')
                title.text = ev['titulo']
            
            total_eventos += len(eventos)
            time.sleep(0.05)
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    desktop = os.path.expanduser('~/Desktop')
    caminho = os.path.join(desktop, 'epg_guiadetv.xml')
    gerar_xml(caminho)
