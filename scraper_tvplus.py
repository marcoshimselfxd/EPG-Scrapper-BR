#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

CATEGORIAS = [
    'https://www.tvplus.com.br/categoria/documentario',
    'https://www.tvplus.com.br/categoria/esportes',
    'https://www.tvplus.com.br/categoria/filmes',
    'https://www.tvplus.com.br/categoria/kids',
    'https://www.tvplus.com.br/categoria/musica',
    'https://www.tvplus.com.br/categoria/noticias',
    'https://www.tvplus.com.br/categoria/series',
    'https://www.tvplus.com.br/categoria/tvaberta',
    'https://www.tvplus.com.br/categoria/variedades',
]

MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def descobrir_canais():
    canais = {}
    for url_cat in CATEGORIAS:
        try:
            r = requests.get(url_cat, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            blocos = soup.find_all('div', class_='program')
            
            for bloco in blocos:
                link = bloco.find('a', href=re.compile(r'/programacao/'))
                if link:
                    nome_elem = link.find('img')
                    nome = nome_elem.get('alt', '') if nome_elem else link.get_text().strip()
                    url_canal = link['href']
                    if nome and nome not in canais:
                        canais[nome] = url_canal
        except:
            pass
    return canais

def extrair_programacao(url_canal):
    if url_canal.startswith('/'):
        url_canal = 'https://www.tvplus.com.br' + url_canal
    
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content, 'html.parser')
    
    eventos = []
    data_atual = None
    
    for bloco in soup.find_all('div', class_='program'):
        info = bloco.find('div', class_='program-info')
        if not info:
            continue
        
        texto_info = info.get_text().strip()
        
        match_dia = re.match(r'^([A-Za-z]+),\s*(\d+)\s*de\s*([A-Za-z]+)', texto_info)
        if match_dia:
            dia_num = int(match_dia.group(2))
            mes_nome = match_dia.group(3).lower()
            mes_num = MESES.get(mes_nome, 0)
            ano = datetime.now().year
            data_atual = datetime(ano, mes_num, dia_num)
            continue
        
        titulo_elem = info.find('a', class_='black')
        titulo = titulo_elem.get_text().strip() if titulo_elem else ''
        
        vivo = info.find('span', class_='live')
        tem_ao_vivo = vivo is not None
        
        details = info.find('div', class_='details')
        horario_texto = details.get_text().strip() if details else ''
        
        match_hora = re.match(r'(\d{2})h(\d{2})\s*-\s*(\d{2})h(\d{2})', horario_texto)
        if match_hora and data_atual and titulo:
            h1, m1, h2, m2 = map(int, match_hora.groups())
            inicio = data_atual.replace(hour=h1, minute=m1, second=0, microsecond=0)
            fim = data_atual.replace(hour=h2, minute=m2, second=0, microsecond=0)
            
            if fim < inicio:
                fim = fim + timedelta(days=1)
            
            if tem_ao_vivo:
                titulo_final = f'Ao vivo - {titulo}'
            else:
                titulo_final = titulo
            
            eventos.append({'inicio': inicio, 'fim': fim, 'titulo': titulo_final})
    
    return eventos

def gerar_xml(caminho_saida):
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper TVPlus')
    
    total_eventos = 0
    processados = 0
    
    for nome, url in sorted(canais.items()):
        try:
            eventos = extrair_programacao(url)
            if not eventos:
                continue
            
            eventos.sort(key=lambda x: x['inicio'])
            
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
            processados += 1
            time.sleep(0.05)
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Canais processados: {processados}/{len(canais)}')
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    desktop = os.path.expanduser('~/Desktop')
    caminho = os.path.join(desktop, 'epg_tvplus.xml')
    gerar_xml(caminho)