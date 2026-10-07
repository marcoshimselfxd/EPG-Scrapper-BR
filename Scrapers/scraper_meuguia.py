#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 4

BASE = 'https://www.guiadetv.com'

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
            for a in soup.find_all('a', href=re.compile(r'/canal/')):
                href = a['href']
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = BASE + href
                nome = ' '.join(a.get_text().split())
                if nome and nome not in canais:
                    canais[nome] = href
        except:
            pass
    return canais


def extrair_programacao(url_canal, data_limite):
    r = requests.get(url_canal, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.content, 'html.parser')

    eventos = []
    for sec in soup.find_all('section', id=re.compile(r'^dia-\d{4}-\d{2}-\d{2}$')):
        for li in sec.find_all('li'):
            time_tag = li.find('time', attrs={'datetime': True})
            if not time_tag:
                continue

            try:
                inicio = datetime.strptime(time_tag['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            except:
                continue

            if inicio > data_limite:
                continue

            link_prog = li.find('a', href=re.compile(r'/programa/'))
            if not link_prog:
                continue

            titulo = ' '.join(link_prog.get_text().split())
            if not titulo:
                continue

            sub_titulo = ''
            if ' : ' in titulo:
                titulo, sub_titulo = titulo.split(' : ', 1)

            duracao_min = 60
            if time_tag.parent:
                span_dur = time_tag.parent.find('span')
                if span_dur:
                    txt_dur = ' '.join(span_dur.get_text().split())
                    match_dur = re.match(r'(\d+)\s*h\s*(\d+)?', txt_dur)
                    if match_dur:
                        duracao_min = int(match_dur.group(1)) * 60 + int(match_dur.group(2) or 0)
                    else:
                        match_dur = re.match(r'(\d+)\s*min', txt_dur)
                        if match_dur:
                            duracao_min = int(match_dur.group(1))

            badges = []
            for span in li.find_all('span'):
                if span.find('span'):
                    continue
                txt_span = ' '.join(span.get_text().split())
                if txt_span and len(txt_span) < 30 and not re.match(r'^\d', txt_span):
                    badges.append(txt_span)
            tem_ao_vivo = any(b.lower() == 'ao vivo' for b in badges)

            sinopse = ''
            p_sinopse = li.find('p')
            if p_sinopse:
                sinopse = ' '.join(p_sinopse.get_text().split())
                if 'sinopse n' in sinopse.lower()[:12]:
                    sinopse = ''

            if tem_ao_vivo:
                titulo_final = 'Ao vivo - ' + titulo
            else:
                titulo_final = titulo

            evento = {
                'inicio': inicio,
                'fim': inicio + timedelta(minutes=duracao_min),
                'titulo': titulo_final,
            }
            if sub_titulo:
                evento['sub_titulo'] = sub_titulo
            if sinopse:
                evento['desc'] = sinopse

            eventos.append(evento)

    eventos.sort(key=lambda x: x['inicio'])
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
                if eventos[i]['fim'] > eventos[i + 1]['inicio']:
                    eventos[i]['fim'] = eventos[i + 1]['inicio']

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

                if ev.get('sub_titulo'):
                    sub = ET.SubElement(prog, 'sub-title')
                    sub.text = ev['sub_titulo']

                if 'desc' in ev:
                    desc = ET.SubElement(prog, 'desc')
                    desc.text = ev['desc']

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
