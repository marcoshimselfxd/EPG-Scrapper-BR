#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
import time

DIAS_PARA_FRENTE = 7

def descobrir_canais():
    url = 'https://mi.tv/br/sitemap'
    r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
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

def extrair_programacao(codigo, data_limite):
    hoje = datetime.now()
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
                
                titulo = titulo_bruto.replace('AO VIVO', '').strip()
                
                if tem_ao_vivo:
                    titulo_final = f'Ao vivo - {titulo}'
                else:
                    titulo_final = titulo
                
                if hora:
                    try:
                        h, m = map(int, hora.split(':'))
                        inicio = data_alvo.replace(hour=h, minute=m, second=0, microsecond=0)
                        
                        if inicio <= data_limite:
                            eventos.append({'inicio': inicio, 'titulo': titulo_final})
                    except:
                        pass
        
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
            eventos = extrair_programacao(codigo, data_limite)
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
            processados += 1
            time.sleep(0.05)
        except:
            pass
    
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print(f'Canais processados: {processados}/{len(canais)}')
    print(f'Eventos extraídos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')

if __name__ == '__main__':
    desktop = os.path.expanduser('~/Desktop')
    caminho = os.path.join(desktop, 'epg_mitv.xml')
    gerar_xml(caminho)