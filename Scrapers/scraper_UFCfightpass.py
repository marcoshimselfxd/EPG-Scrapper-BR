#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os

DIAS_PARA_FRENTE = 60
DURACAO_ESTIMADA = 3  # horas

def extrair_eventos():
    todos_eventos = []
    
    for page in [0, 1]:
        url = f'https://www.ufc.com.br/events?page={page}' if page > 0 else 'https://www.ufc.com.br/events'
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'html.parser')
        
        cards = soup.find_all('article', class_='c-card-event--result')
        
        for card in cards:
            headline = card.find('h3', class_='c-card-event--result__headline')
            titulo = headline.get_text().strip() if headline else ''
            
            date_elem = card.find('div', class_='c-card-event--result__date')
            timestamp = date_elem.get('data-main-card-timestamp', '') if date_elem else ''
            
            venue = card.find('h5')
            local = venue.get_text().strip() if venue else ''
            
            country_elem = card.find('span', class_='country')
            pais = country_elem.get_text().strip() if country_elem else ''
            
            if timestamp and titulo:
                inicio = datetime.fromtimestamp(int(timestamp))
                fim = inicio + timedelta(hours=DURACAO_ESTIMADA)
                
                todos_eventos.append({
                    'inicio': inicio,
                    'fim': fim,
                    'titulo': titulo,
                    'local': local,
                    'pais': pais
                })
    
    return todos_eventos

def gerar_xml(caminho_saida):
    eventos = extrair_eventos()
    
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    eventos_validos = []
    for ev in eventos:
        if 'TBD' in ev['titulo'].upper():
            continue
        if ev['inicio'] < hoje:
            continue
        if ev['inicio'] > data_limite:
            continue
        eventos_validos.append(ev)
    
    eventos_validos.sort(key=lambda x: x['inicio'])
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper UFC Fight Pass')
    
    channel = ET.SubElement(root, 'channel')
    channel.set('id', 'UFC Fight Pass')
    display = ET.SubElement(channel, 'display-name')
    display.text = 'UFC Fight Pass'
    
    for ev in eventos_validos:
        prog = ET.SubElement(root, 'programme')
        prog.set('start', ev['inicio'].strftime('%Y%m%d%H%M%S -0300'))
        prog.set('stop', ev['fim'].strftime('%Y%m%d%H%M%S -0300'))
        prog.set('channel', 'UFC Fight Pass')
        
        title = ET.SubElement(prog, 'title')
        title.text = ev['titulo']
        
        desc_texto = ev['titulo']
        if ev['local']:
            desc_texto += f' - {ev["local"]}'
        if ev['pais']:
            desc_texto += f', {ev["pais"]}'
        
        desc = ET.SubElement(prog, 'desc')
        desc.text = desc_texto
        
        category = ET.SubElement(prog, 'category')
        category.text = 'Luta'
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Eventos encontrados: {len(eventos_validos)}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_UFCfightpass.xml')
    gerar_xml(caminho)
