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
    soup = BeautifulSoup(r.content, 'html.parser')
    
    elementos_dt = soup.find_all(attrs={'data-dt': True})
    
    eventos = []
    for elem in elementos_dt:
        data_hora = elem['data-dt']
        try:
            inicio = datetime.strptime(data_hora[:16], '%Y-%m-%d %H:%M')
            if inicio > data_limite:
                continue
        except:
            continue
        
        bloco = elem.parent
        while bloco and not bloco.find('h3'):
            bloco = bloco.parent
        
        if not bloco:
            continue
        
        h3 = bloco.find('h3')
        link_prog = h3.find('a', href=re.compile(r'/programa/'))
        if not link_prog:
            continue
        
        titulo = link_prog.get_text().strip()
        url_programa = link_prog['href']
        if url_programa.startswith('/'):
            url_programa = 'https://www.guiadetv.com' + url_programa
        
        badges = re.findall(r'badge[^>]*>\s*([^<]+?)\s*</span>', str(bloco), re.IGNORECASE)
        tem_ao_vivo = any('AO VIVO' in b.upper() for b in badges)
        tem_vt = any('VT' in b.upper() for b in badges)
        
        sinopse = ''
        p_fs7 = bloco.find('p', class_='fs-7')
        if p_fs7:
            sinopse = p_fs7.get_text().strip()[:200]
        else:
            p_any = bloco.find('p')
            if p_any:
                sinopse = p_any.get_text().strip()[:200]
        
        classificacao = ''
        if not sinopse:
            try:
                r_prog = requests.get(url_programa, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                soup_prog = BeautifulSoup(r_prog.content, 'html.parser')
                
                box = soup_prog.find('div', class_='box')
                if box:
                    p_sinopse = box.find('p')
                    if p_sinopse:
                        sinopse = p_sinopse.get_text().strip()[:200]
                
                faixa = soup_prog.find('div', class_='faixa')
                if faixa:
                    match_class = re.search(r'(\d{1,2})', faixa.get_text().strip())
                    if match_class:
                        classificacao = match_class.group(1)
                
                time.sleep(0.05)
            except:
                pass
        
        if tem_ao_vivo:
            titulo_final = f'Ao vivo - {titulo}'
        elif tem_vt:
            titulo_final = f'VT - {titulo}'
        else:
            titulo_final = titulo
        
        evento = {'inicio': inicio, 'titulo': titulo_final}
        if sinopse:
            evento['desc'] = sinopse
        if classificacao:
            evento['rating'] = classificacao
        
        eventos.append(evento)
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper GuiaDeTV')
    
    total_eventos = 0
    processados = 0
    
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
                
                if 'desc' in ev:
                    desc = ET.SubElement(prog, 'desc')
                    desc.text = ev['desc']
                
                if 'rating' in ev:
                    rating = ET.SubElement(prog, 'rating')
                    value = ET.SubElement(rating, 'value')
                    value.text = ev['rating']
            
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
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_guiadetv.xml')
    gerar_xml(caminho)
