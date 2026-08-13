#!/usr/bin/env python3
import requests
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os

DIAS_PARA_FRENTE = 4

CANAIS_PTBR = [
    ('Otaku', 'otaku'),
    ('Urban Docs', 'docs'),
    ('Urban Drive', 'drive'),
    ('Urban Kids', 'kids'),
    ('Urban Movie', 'movie'),
    ('Urban Retro', 'retro'),
    ('Urban Series', 'series'),
    ('Urban Travel', 'travel'),
    ('ZooKids', 'zookids'),
    ('Moove Cine', 'moove-cine'),
    ('Moove Cult', 'moove-cult'),
    ('Moove Explore', 'moove-explore'),
    ('Villa Kids', 'villa-kids'),
]

def extrair_canal(nome, slug):
    timestamp = int(time.time() * 1000)
    url = f'https://urbantv.com.br/grade/data/{slug}.json?t={timestamp}'
    r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    data = r.json()
    return data.get('programs', [])

def gerar_xml(caminho_saida):
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper UrbanTV')
    
    data_limite = datetime.now() + timedelta(days=DIAS_PARA_FRENTE)
    
    total_eventos = 0
    
    for nome, slug in CANAIS_PTBR:
        try:
            programs = extrair_canal(nome, slug)
            
            channel = ET.SubElement(root, 'channel')
            channel.set('id', nome)
            display = ET.SubElement(channel, 'display-name')
            display.text = nome
            
            for prog in programs:
                start_utc = datetime.fromisoformat(prog['start'].replace('Z', '+00:00'))
                stop_utc = datetime.fromisoformat(prog['stop'].replace('Z', '+00:00'))
                
                start_brasil = start_utc - timedelta(hours=3)
                stop_brasil = stop_utc - timedelta(hours=3)
                
                if start_brasil > data_limite:
                    continue
                
                p = ET.SubElement(root, 'programme')
                p.set('start', start_brasil.strftime('%Y%m%d%H%M%S') + ' -0300')
                p.set('stop', stop_brasil.strftime('%Y%m%d%H%M%S') + ' -0300')
                p.set('channel', nome)
                
                title = ET.SubElement(p, 'title')
                title.text = prog['title']
                
                desc_texto = prog.get('description', '')
                if desc_texto and not desc_texto.endswith('.'):
                    desc_texto += '...'
                
                if desc_texto:
                    desc = ET.SubElement(p, 'desc')
                    desc.text = desc_texto
                
                if prog.get('year'):
                    date = ET.SubElement(p, 'date')
                    date.text = prog['year']
                
                if prog.get('actors'):
                    credits = ET.SubElement(p, 'credits')
                    actor = ET.SubElement(credits, 'actor')
                    actor.text = ', '.join(prog['actors'])
                
                total_eventos += 1
        
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_urbantv.xml')
    gerar_xml(caminho)
