#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 4

TRADUCOES = {
    'Action': 'Ação',
    'Adventure': 'Aventura',
    'Biography': 'Biografia',
    'Bus./Financial': 'Negócios/Finanças',
    'Children': 'Infantil',
    'Comedy': 'Comédia',
    'Comedy Drama': 'Comédia Dramática',
    'Community': 'Comunidade',
    'Consumer': 'Consumo',
    'Dark Comedy': 'Comédia Negra',
    'Documentary': 'Documentário',
    'Drama': 'Drama',
    'Educational': 'Educativo',
    'Entertainment': 'Entretenimento',
    'Health': 'Saúde',
    'History': 'História',
    'Horror': 'Terror',
    'Interview': 'Entrevista',
    'Music': 'Música',
    'Nature': 'Natureza',
    'News': 'Notícias',
    'Newsmagazine': 'Revista de Notícias',
    'Politics': 'Política',
    'Public Affairs': 'Assuntos Públicos',
    'Reality': 'Reality Show',
    'Religious': 'Religioso',
    'Romance': 'Romance',
    'Science Fiction': 'Ficção Científica',
    'Shopping': 'Compras',
    'Soap': 'Novela',
    'Special': 'Especial',
    'Sports Talk': 'Debate Esportivo',
    'Talk': 'Talk Show',
    'Thriller': 'Suspense',
    'Variety': 'Variedades',
}

def descobrir_canais():
    try:
        r = requests.get('https://mi.tv/br/sitemap', timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'html.parser')
        canais = {}
        for a in soup.find_all('a', href=True):
            href = a['href']
            texto = a.get_text().strip()
            if '/br/canais/' in href and texto and texto != '$nameFromProvider':
                codigo = href.split('/')[-1]
                if texto not in canais:
                    canais[texto] = codigo
        return canais
    except:
        return {}

def extrair_programacao(codigo, data_limite, hoje):
    eventos = []
    
    for dias in range(DIAS_PARA_FRENTE + 1):
        data_alvo = hoje + timedelta(days=dias)
        data_str = data_alvo.strftime('%Y-%m-%d')
        
        if dias == 0:
            url = f'https://mi.tv/br/async/channel/{codigo}/-180'
        else:
            url = f'https://mi.tv/br/async/channel/{codigo}/{data_str}/-180'
        
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            programas = soup.find_all('a', class_='program-link')
            
            for prog in programas:
                time_elem = prog.find('span', class_='time')
                hora = time_elem.get_text().strip() if time_elem else ''
                
                h2 = prog.find('h2')
                titulo_bruto = h2.get_text().strip() if h2 else ''
                
                vivo = h2.find('img', class_='vivo') if h2 else None
                tem_ao_vivo = vivo is not None
                
                sub = prog.find('span', class_='sub-title')
                sub_texto = sub.get_text().strip() if sub else ''
                
                sinopse = prog.find('p', class_='synopsis')
                sinopse_texto = sinopse.get_text().strip() if sinopse else ''
                
                nota = ''
                rating_elem = sub.find('span', class_='rating') if sub else None
                if rating_elem:
                    nota = rating_elem.get_text().strip()
                    sub_texto = sub_texto.replace(nota, '').strip()
                    sub_texto = sub_texto.rstrip('/').strip()
                
                if not hora:
                    continue
                
                try:
                    h, m = map(int, hora.split(':'))
                    inicio = data_alvo.replace(hour=h, minute=m, second=0, microsecond=0)
                    if inicio > data_limite:
                        continue
                except:
                    continue
                
                if tem_ao_vivo:
                    titulo_final = f'Ao vivo - {titulo_bruto}'
                else:
                    titulo_final = titulo_bruto
                
                categorias = []
                sub_title = ''
                ano = ''
                
                if 'Temporada' in sub_texto or 'Season' in sub_texto:
                    sub_title = sub_texto
                    categorias.append('Séries')
                elif '/' in sub_texto:
                    partes = sub_texto.split('/')
                    if len(partes) >= 1:
                        genero_original = partes[0].strip()
                        genero_traduzido = TRADUCOES.get(genero_original, genero_original)
                        categorias.append('Filme')
                        categorias.append(genero_traduzido)
                    if len(partes) >= 2:
                        ano_match = re.search(r'\d{4}', partes[1])
                        if ano_match:
                            ano = ano_match.group(0)
                elif sub_texto:
                    genero_traduzido = TRADUCOES.get(sub_texto, sub_texto)
                    categorias.append(genero_traduzido)
                
                evento = {
                    'inicio': inicio,
                    'titulo': titulo_final,
                    'categorias': categorias,
                    'sub_title': sub_title,
                    'ano': ano,
                    'nota': nota,
                    'sinopse': sinopse_texto
                }
                
                eventos.append(evento)
        
        except:
            pass
    
    return eventos

def gerar_xml(caminho_saida):
    hoje = datetime.now()
    data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)
    
    canais = descobrir_canais()
    print(f'Canais descobertos: {len(canais)}')
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'Scraper MiTV')
    
    total_eventos = 0
    processados = 0
    
    for nome, codigo in sorted(canais.items()):
        try:
            eventos = extrair_programacao(codigo, data_limite, hoje)
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
                
                if ev['sub_title']:
                    sub = ET.SubElement(prog, 'sub-title')
                    sub.text = ev['sub_title']
                
                for cat in ev['categorias']:
                    c = ET.SubElement(prog, 'category')
                    c.text = cat
                
                if ev['ano']:
                    date = ET.SubElement(prog, 'date')
                    date.text = ev['ano']
                
                if ev['nota']:
                    rating = ET.SubElement(prog, 'rating')
                    rating.set('system', 'IMDB')
                    value = ET.SubElement(rating, 'value')
                    value.text = ev['nota']
                
                if ev['sinopse']:
                    desc = ET.SubElement(prog, 'desc')
                    desc.text = ev['sinopse']
            
            total_eventos += len(eventos)
            processados += 1
            time.sleep(0.02)
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Canais processados: {processados}/{len(canais)}')
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'epg_mitv.xml')
    gerar_xml(caminho)
