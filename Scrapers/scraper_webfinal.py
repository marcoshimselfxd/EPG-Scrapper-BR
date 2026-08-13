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
    'https://webfinal.com.br/programacao/tv-aberta',
    'https://webfinal.com.br/programacao/filmes',
    'https://webfinal.com.br/programacao/series',
    'https://webfinal.com.br/programacao/futebol',
    'https://webfinal.com.br/programacao/esportes',
    'https://webfinal.com.br/programacao/variedades',
    'https://webfinal.com.br/programacao/noticias',
    'https://webfinal.com.br/programacao/infantil',
    'https://webfinal.com.br/programacao/documentarios',
    'https://webfinal.com.br/programacao/catolica',
    'https://webfinal.com.br/programacao/evangelica',
    'https://webfinal.com.br/programacao/agronegocio',
    'https://webfinal.com.br/programacao/publicos',
    'https://webfinal.com.br/programacao/internacional',
]

def descobrir_canais():
    canais = {}
    for url_cat in CATEGORIAS:
        try:
            r = requests.get(url_cat, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            
            cards = soup.find_all('article', class_='pfcx-card')
            for card in cards:
                h3 = card.find('h3', class_='pfcx-canal')
                link = card.find('a', class_='pfcx-link')
                
                nome = h3.get_text().strip() if h3 else ''
                href = link.get('href', '') if link else ''
                
                if nome and href and nome not in canais:
                    canais[nome] = href
        except:
            pass
    return canais

def extrair_programacao(url_canal, data_limite):
    if url_canal.startswith('/'):
        url_canal = 'https://webfinal.com.br' + url_canal
    
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content, 'html.parser')
    
    eventos = []
    cards = soup.find_all('div', class_=re.compile(r'program-card'))
    
    for card in cards:
        data_start = card.get('data-start', '')
        data_end = card.get('data-end', '')
        titulo_attr = card.get('data-title', '')
        
        if not data_start or not data_end:
            continue
        
        try:
            inicio = datetime.fromtimestamp(int(data_start) / 1000)
            fim = datetime.fromtimestamp(int(data_end) / 1000)
        except:
            continue
        
        if inicio > data_limite:
            continue
        
        h3 = card.find('h3')
        titulo = h3.get_text().strip() if h3 else titulo_attr
        
        desc = card.find('p', class_='descricao')
        descricao = desc.get_text().strip() if desc else ''
        
        # Extrai ano da descrição
        ano = ''
        descricao_limpa = descricao
        match_ano = re.match(r'^(\d{4})\.\s*(.+)', descricao)
        if match_ano:
            ano = match_ano.group(1)
            descricao_limpa = match_ano.group(2)
        
        duracao_elem = card.find('span', class_='duration-badge')
        duracao_texto = duracao_elem.get_text().strip() if duracao_elem else ''
        
        # Converte duração para minutos
        duracao_minutos = ''
        if duracao_texto:
            match_duracao = re.match(r'(\d+)h\s*(\d+)min', duracao_texto)
            if match_duracao:
                horas = int(match_duracao.group(1))
                minutos = int(match_duracao.group(2))
                duracao_minutos = str(horas * 60 + minutos)
            else:
                match_min = re.match(r'(\d+)\s*min', duracao_texto)
                if match_min:
                    duracao_minutos = match_min.group(1)
        
        evento = {
            'inicio': inicio,
            'fim': fim,
            'titulo': titulo,
            'ano': ano,
            'descricao': descricao_limpa,
            'duracao': duracao_minutos
        }
        
        eventos.append(evento)
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper WebFinal')
    
    total_eventos = 0
    processados = 0
    
    for nome, url in sorted(canais.items()):
        try:
            eventos = extrair_programacao(url, data_limite)
            if not eventos:
                continue
            
            eventos.sort(key=lambda x: x['inicio'])
            
            channel = ET.SubElement(root, 'channel')
            channel.set('id', nome)
            display = ET.SubElement(channel, 'display-name')
            display.text = nome
            
            for ev in eventos:
                prog = ET.SubElement(root, 'programme')
                inicio_utc = ev['inicio'] - timedelta(hours=3)
                fim_utc = ev['fim'] - timedelta(hours=3)
                prog.set('start', inicio_utc.strftime('%Y%m%d%H%M%S') + ' -0300')
                prog.set('stop', fim_utc.strftime('%Y%m%d%H%M%S') + ' -0300')
                prog.set('channel', nome)
                
                title = ET.SubElement(prog, 'title')
                title.text = ev['titulo']
                
                if ev['ano']:
                    date = ET.SubElement(prog, 'date')
                    date.text = ev['ano']
                
                if ev['descricao']:
                    desc = ET.SubElement(prog, 'desc')
                    desc.text = ev['descricao']
                
                if ev['duracao']:
                    length = ET.SubElement(prog, 'length')
                    length.set('units', 'minutes')
                    length.text = ev['duracao']
            
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
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_webfinal.xml')
    gerar_xml(caminho)
