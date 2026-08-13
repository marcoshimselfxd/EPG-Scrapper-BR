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
    'https://meuguia.tv/programacao/categoria/Filmes',
    'https://meuguia.tv/programacao/categoria/Series',
    'https://meuguia.tv/programacao/categoria/Esportes',
    'https://meuguia.tv/programacao/categoria/Infantil',
    'https://meuguia.tv/programacao/categoria/Variedades',
    'https://meuguia.tv/programacao/categoria/Documentarios',
    'https://meuguia.tv/programacao/categoria/Noticias',
    'https://meuguia.tv/programacao/categoria/Aberta',
]

def descobrir_canais():
    canais = {}
    for url_cat in CATEGORIAS:
        try:
            r = requests.get(url_cat, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/programacao/canal/' in href:
                    texto = a.get_text().strip()
                    nome = texto.split('\n')[0].strip()
                    if nome and nome not in canais:
                        canais[nome] = href
        except:
            pass
    return canais

def extrair_programacao(url_canal, data_limite):
    if url_canal.startswith('/'):
        url_canal = 'https://meuguia.tv' + url_canal
    
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content, 'html.parser')
    texto = soup.get_text()
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    hoje = datetime.now()
    eventos = []
    data_atual = None
    
    for i, linha in enumerate(linhas):
        match_dia = re.match(r'^(\w+(?:-feira)?),\s*(\d+)/(\d+)', linha, re.IGNORECASE)
        if match_dia:
            dia_num = int(match_dia.group(2))
            mes_num = int(match_dia.group(3))
            ano = hoje.year
            if mes_num < hoje.month:
                ano += 1
            data_atual = datetime(ano, mes_num, dia_num)
            continue
        
        match_hora = re.match(r'^(\d{2}:\d{2})$', linha)
        if match_hora and data_atual:
            hora = match_hora.group(1)
            h, m = map(int, hora.split(':'))
            inicio = data_atual.replace(hour=h, minute=m, second=0, microsecond=0)
            
            if inicio > data_limite:
                continue
            
            if i + 1 < len(linhas):
                titulo_bruto = linhas[i + 1]
                ja_tem_vt = titulo_bruto.upper().startswith('VT')
                tem_ao_vivo = 'ao vivo' in titulo_bruto.lower()
                
                titulo_limpo = re.sub(r'\s*-\s*Ao Vivo\s*$', '', titulo_bruto, flags=re.IGNORECASE)
                titulo_limpo = titulo_limpo.strip()
                
                if not titulo_limpo.startswith('Publicidade'):
                    if tem_ao_vivo and not titulo_limpo.upper().startswith('AO VIVO'):
                        titulo_final = f'Ao vivo - {titulo_limpo}'
                    elif ja_tem_vt:
                        titulo_final = titulo_limpo
                    else:
                        titulo_final = titulo_limpo
                    
                    eventos.append({'inicio': inicio, 'titulo': titulo_final})
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper MeuGuia')
    
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
    caminho = os.path.join(desktop, 'epg_meuguia.xml')
    gerar_xml(caminho)