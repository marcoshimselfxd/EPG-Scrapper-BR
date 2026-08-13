#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 7
hoje = datetime.now()
data_limite = hoje + timedelta(days=DIAS_PARA_FRENTE)

EQUIVALENCIAS = {
    'TRAVELBOXBRAZIL': 'TRAVELBOXBRASIL',
    'DISCOVERYHDTHEATER': 'DISCOVERYTHEATER',
    'HISTORYCHANNEL': 'HISTORY',
    'EENTERTAINMENTTELEVISION': 'E',
    'PREMIERECLUBES': 'PREMIEREFC',
    'WARNERCHANNEL': 'WARNER',
    'TCMTURNERCLASSIC': 'TCM',
    'UNIVERSALCHANNEL': 'UNIVERSALTV',
    'DUMDUM': 'ZOOMOO',
    'ZOOMOOKIDS': 'ZOOMOO',
    'SYFY': 'USANETWORK',
}

def normalizar_nome(nome):
    nome = nome.upper()
    nome = nome.replace('Ç', 'C').replace('Ã', 'A').replace('Õ', 'O').replace('É', 'E')
    nome = nome.replace('Ê', 'E').replace('Á', 'A').replace('Ó', 'O').replace('Í', 'I')
    nome = nome.replace('Ú', 'U').replace('Â', 'A').replace('Ô', 'O')
    nome = re.sub(r'\s*(HD|FHD|4K|SD|HEVC|H265)\s*$', '', nome)
    nome = nome.replace(' ', '').replace('_', '').replace('-', '').replace('!', '')
    if nome in EQUIVALENCIAS:
        return EQUIVALENCIAS[nome]
    return nome

def extrair_guiadetv():
    print('📡 GUIADETV.COM')
    categorias = [
        'https://www.guiadetv.com/categorias/variedades.html',
        'https://www.guiadetv.com/categorias/tv-aberta.html',
        'https://www.guiadetv.com/categorias/noticias.html',
        'https://www.guiadetv.com/categorias/infantil.html',
        'https://www.guiadetv.com/categorias/filmes-e-series.html',
        'https://www.guiadetv.com/categorias/esportes.html',
        'https://www.guiadetv.com/categorias/documentarios.html',
    ]
    canais = {}
    for url_cat in categorias:
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
    dados = {}
    for nome, url in sorted(canais.items()):
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            html = r.text
            datas = re.findall(r'data-dt="(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2}', html)
            titulos_blocos = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            titulos = []
            for bloco in titulos_blocos:
                badges = re.findall(r'badge[^>]*>\s*([^<]+?)\s*</span>', bloco, re.IGNORECASE)
                texto = re.sub(r'<[^>]+>', '', bloco)
                texto = re.sub(r'\s+', ' ', texto).strip()
                tem_ao_vivo = any('AO VIVO' in b.upper() for b in badges)
                tem_vt = any('VT' in b.upper() for b in badges)
                for badge in badges:
                    texto = texto.replace(badge.strip(), '').strip()
                if tem_ao_vivo:
                    titulos.append(f'Ao vivo - {texto}')
                elif tem_vt:
                    titulos.append(f'VT - {texto}')
                else:
                    titulos.append(texto)
            eventos = []
            for i in range(min(len(datas), len(titulos))):
                try:
                    inicio = datetime.strptime(datas[i], '%Y-%m-%d %H:%M')
                    if inicio <= data_limite:
                        eventos.append({'inicio': inicio, 'titulo': titulos[i]})
                except:
                    pass
            if eventos:
                eventos.sort(key=lambda x: x['inicio'])
                dados[nome] = eventos
            time.sleep(0.03)
        except:
            pass
    return dados

def extrair_meuguia():
    print('📡 MEUGUIA.TV')
    categorias = [
        'https://meuguia.tv/programacao/categoria/Filmes',
        'https://meuguia.tv/programacao/categoria/Series',
        'https://meuguia.tv/programacao/categoria/Esportes',
        'https://meuguia.tv/programacao/categoria/Infantil',
        'https://meuguia.tv/programacao/categoria/Variedades',
        'https://meuguia.tv/programacao/categoria/Documentarios',
        'https://meuguia.tv/programacao/categoria/Noticias',
        'https://meuguia.tv/programacao/categoria/Aberta',
    ]
    canais = {}
    for url_cat in categorias:
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
    dados = {}
    for nome, url in sorted(canais.items()):
        try:
            if url.startswith('/'):
                url = 'https://meuguia.tv' + url
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
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
                    if i + 1 < len(linhas):
                        titulo_bruto = linhas[i + 1]
                        ja_tem_vt = titulo_bruto.upper().startswith('VT')
                        tem_ao_vivo = 'ao vivo' in titulo_bruto.lower()
                        titulo_limpo = re.sub(r'\s*-\s*Ao Vivo\s*$', '', titulo_bruto, flags=re.IGNORECASE)
                        titulo_limpo = titulo_limpo.strip()
                        if not titulo_limpo.startswith('Publicidade'):
                            if tem_ao_vivo and not titulo_limpo.upper().startswith('AO VIVO'):
                                eventos.append({'inicio': inicio, 'titulo': f'Ao vivo - {titulo_limpo}'})
                            elif ja_tem_vt:
                                eventos.append({'inicio': inicio, 'titulo': titulo_limpo})
                            else:
                                eventos.append({'inicio': inicio, 'titulo': titulo_limpo})
            if eventos:
                eventos.sort(key=lambda x: x['inicio'])
                dados[nome] = eventos
            time.sleep(0.03)
        except:
            pass
    return dados

def extrair_tvplus():
    print('📡 TVPLUS.COM.BR')
    categorias = [
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
    canais = {}
    for url_cat in categorias:
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
    dados = {}
    for nome, url in sorted(canais.items()):
        try:
            if url.startswith('/'):
                url = 'https://www.tvplus.com.br' + url
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
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
                    ano = hoje.year
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
                        eventos.append({'inicio': inicio, 'fim': fim, 'titulo': f'Ao vivo - {titulo}'})
                    else:
                        eventos.append({'inicio': inicio, 'fim': fim, 'titulo': titulo})
            if eventos:
                eventos.sort(key=lambda x: x['inicio'])
                dados[nome] = eventos
            time.sleep(0.03)
        except:
            pass
    return dados

def extrair_mitv():
    print('📡 MI.TV')
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
    except:
        return {}
    dados = {}
    for nome, codigo in sorted(canais.items()):
        try:
            eventos = []
            for dias in range(DIAS_PARA_FRENTE + 1):
                data_alvo = hoje + timedelta(days=dias)
                data_str = data_alvo.strftime('%Y-%m-%d')
                if dias == 0:
                    url = f'https://mi.tv/br/async/channel/{codigo}/-180'
                else:
                    url = f'https://mi.tv/br/async/channel/{codigo}/{data_str}/-180'
                r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(r.content, 'html.parser')
                programas = soup.find_all('a', class_='program-link')
                for prog in programas:
                    time_elem = prog.find('span', class_='time')
                    hora = time_elem.get_text().strip() if time_elem else ''
                    h2 = prog.find('h2')
                    titulo_bruto = h2.get_text().strip() if h2 else ''
                    vivo = h2.find('img', class_='vivo') if h2 else None
                    titulo = titulo_bruto.replace('AO VIVO', '').strip()
                    if hora:
                        try:
                            h, m = map(int, hora.split(':'))
                            inicio = data_alvo.replace(hour=h, minute=m, second=0, microsecond=0)
                            if vivo:
                                eventos.append({'inicio': inicio, 'titulo': f'Ao vivo - {titulo}'})
                            else:
                                eventos.append({'inicio': inicio, 'titulo': titulo})
                        except:
                            pass
            if eventos:
                eventos.sort(key=lambda x: x['inicio'])
                dados[nome] = eventos
            time.sleep(0.02)
        except:
            pass
    return dados

print('=' * 60)
print('EPG MESCLADO COMPLETO - 4 FONTES')
print('=' * 60)
print()

dados_guiadetv = extrair_guiadetv()
print(f'  ✅ {len(dados_guiadetv)} canais')
print()

dados_meuguia = extrair_meuguia()
print(f'  ✅ {len(dados_meuguia)} canais')
print()

dados_tvplus = extrair_tvplus()
print(f'  ✅ {len(dados_tvplus)} canais')
print()

dados_mitv = extrair_mitv()
print(f'  ✅ {len(dados_mitv)} canais')
print()

root = ET.Element('tv')
root.set('generator-info-name', 'EPG Mesclado 4 Fontes')

nomes_processados = {}
total_eventos = 0

for dados_fonte in [dados_guiadetv, dados_meuguia, dados_tvplus, dados_mitv]:
    for nome, eventos in dados_fonte.items():
        nome_norm = normalizar_nome(nome)
        if nome_norm in nomes_processados:
            continue
        nomes_processados[nome_norm] = nome
        
        channel = ET.SubElement(root, 'channel')
        channel.set('id', nome)
        display = ET.SubElement(channel, 'display-name')
        display.text = nome
        
        if not eventos:
            continue
        
        for i in range(len(eventos) - 1):
            if 'fim' not in eventos[i]:
                eventos[i]['fim'] = eventos[i + 1]['inicio']
        if 'fim' not in eventos[-1]:
            eventos[-1]['fim'] = eventos[-1]['inicio'] + timedelta(hours=1)
        
        for ev in eventos:
            prog = ET.SubElement(root, 'programme')
            prog.set('start', ev['inicio'].strftime('%Y%m%d%H%M%S -0300'))
            prog.set('stop', ev['fim'].strftime('%Y%m%d%H%M%S -0300'))
            prog.set('channel', nome)
            title = ET.SubElement(prog, 'title')
            title.text = ev['titulo']
            total_eventos += 1

caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'epg_final.xml')
tree = ET.ElementTree(root)
tree.write(caminho, encoding='utf-8', xml_declaration=True)

print('=' * 60)
print('✅ CONCLUSÃO:')
print(f'  📺 Total canais: {len(nomes_processados)}')
print(f'  📅 Total eventos: {total_eventos}')
print(f'  📁 XML salvo em: {caminho}')
print(f'  📦 Tamanho: {os.path.getsize(caminho) / 1024:.1f} KB')
print('=' * 60)
