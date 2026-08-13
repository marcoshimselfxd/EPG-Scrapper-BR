#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 4

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

def extrair_programacao(url_canal, data_limite, hoje):
    if url_canal.startswith('/'):
        url_canal = 'https://meuguia.tv' + url_canal
    
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content, 'html.parser')
    texto = soup.get_text()
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    
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
            
            titulo = ''
            genero = ''
            
            if i + 1 < len(linhas):
                titulo = linhas[i + 1]
            
            if i + 2 < len(linhas):
                genero_bruto = linhas[i + 2]
                if '/' in genero_bruto and not genero_bruto.startswith('Publicidade'):
                    genero = genero_bruto
            
            if titulo and not titulo.startswith('Publicidade'):
                eventos.append({
                    'inicio': inicio,
                    'titulo': titulo,
                    'genero': genero
                })
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper MeuGuia')
    
    total_eventos = 0
    processados = 0
    
    for nome, url in sorted(canais.items()):
        try:
            eventos = extrair_programacao(url, data_limite, hoje)
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
                
                if ev['genero']:
                    partes = ev['genero'].split('/')
                    if len(partes) > 0 and partes[0].strip():
                        cat1 = ET.SubElement(prog, 'category')
                        cat1.text = partes[0].strip()
                    if len(partes) > 1 and partes[1].strip():
                        cat2 = ET.SubElement(prog, 'category')
                        cat2.text = partes[1].strip()
            
            total_eventos += len(eventos)
            processados += 1
            time.sleep(0.03)
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Canais processados: {processados}/{len(canais)}')
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_meuguia.xml')
    gerar_xml(caminho)
