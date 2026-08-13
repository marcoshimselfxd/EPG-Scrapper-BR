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

def extrair_programacao(url_canal, data_limite, hoje):
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
            mes_nome = match_dia.group(3).lower()
            mes_num = MESES.get(mes_nome, 0)
            data_atual = datetime(hoje.year, mes_num, int(match_dia.group(2)))
            continue
        
        titulo_elem = info.find('a', class_='black')
        if not titulo_elem:
            continue
        
        titulo = titulo_elem.get_text().strip()
        url_prog = titulo_elem['href']
        if url_prog.startswith('/'):
            url_prog = 'https://www.tvplus.com.br' + url_prog
        
        vivo = info.find('span', class_='live')
        tem_ao_vivo = vivo is not None
        
        classificacao = ''
        img_class = info.find('img', src=re.compile(r'/classificacao/'))
        if img_class:
            match_class = re.search(r'(\d{1,2})\.png', img_class['src'])
            if match_class:
                classificacao = match_class.group(1)
        
        details = info.find('div', class_='details')
        details_texto = details.get_text().strip() if details else ''
        match_hora = re.match(r'(\d{2})h(\d{2})\s*-\s*(\d{2})h(\d{2})\s*\|\s*(.+)', details_texto)
        
        if not match_hora or not data_atual:
            continue
        
        h1, m1, h2, m2 = map(int, match_hora.groups()[:4])
        genero_bruto = match_hora.group(5).strip()
        
        inicio = data_atual.replace(hour=h1, minute=m1, second=0, microsecond=0)
        fim = data_atual.replace(hour=h2, minute=m2, second=0, microsecond=0)
        if fim < inicio:
            fim = fim + timedelta(days=1)
        
        if inicio > data_limite:
            continue
        
        categorias = []
        if ',' in genero_bruto:
            partes = genero_bruto.split(',')
            if partes[0].strip():
                categorias.append(partes[0].strip())
            if len(partes) > 1 and partes[1].strip():
                categorias.append(partes[1].strip())
        elif genero_bruto:
            categorias.append(genero_bruto)
        
        titulo_original = ''
        ano_lancamento = ''
        pais = ''
        duracao = ''
        
        if 'Filme' in categorias:
            try:
                r_prog = requests.get(url_prog, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                soup_prog = BeautifulSoup(r_prog.content, 'html.parser')
                main_info = soup_prog.find('div', class_='main-info-sinopse')
                if main_info:
                    texto_meta = main_info.get_text().strip()
                    linhas_meta = [l.strip() for l in texto_meta.split('\n') if l.strip()]
                    if len(linhas_meta) >= 2:
                        titulo_original = linhas_meta[1]
                    if len(linhas_meta) >= 3:
                        info_meta = linhas_meta[2]
                        match_meta = re.match(r'([^/]+)\s*/\s*([^/]+)\s*/\s*(\d{4})\s*/\s*(\d+)\s*Min', info_meta)
                        if match_meta:
                            pais = match_meta.group(2).strip()
                            ano_lancamento = match_meta.group(3)
                            duracao = match_meta.group(4)
                time.sleep(0.03)
            except:
                pass
        
        if tem_ao_vivo:
            titulo_final = f'Ao vivo - {titulo}'
        elif titulo.upper().startswith('VT'):
            titulo_final = titulo
        else:
            titulo_final = titulo
        
        evento = {
            'inicio': inicio,
            'fim': fim,
            'titulo': titulo_final,
            'classificacao': classificacao,
            'categorias': categorias,
            'titulo_original': titulo_original,
            'ano': ano_lancamento,
            'pais': pais,
            'duracao': duracao
        }
        
        eventos.append(evento)
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper TVPlus')
    
    total_eventos = 0
    processados = 0
    
    for nome, url in sorted(canais.items()):
        try:
            eventos = extrair_programacao(url, data_limite, hoje)
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
                
                if ev['titulo_original'] and ev['titulo_original'] != ev['titulo']:
                    sub = ET.SubElement(prog, 'sub-title')
                    sub.text = ev['titulo_original']
                
                for cat in ev['categorias']:
                    c = ET.SubElement(prog, 'category')
                    c.text = cat
                
                if ev['ano']:
                    date = ET.SubElement(prog, 'date')
                    date.text = ev['ano']
                
                if ev['duracao']:
                    length = ET.SubElement(prog, 'length')
                    length.set('units', 'minutes')
                    length.text = ev['duracao']
                
                if ev['pais']:
                    country = ET.SubElement(prog, 'country')
                    country.text = ev['pais']
                
                if ev['classificacao']:
                    rating = ET.SubElement(prog, 'rating')
                    value = ET.SubElement(rating, 'value')
                    value.text = ev['classificacao']
            
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
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_tvplus.xml')
    gerar_xml(caminho)
