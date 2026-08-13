#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import re
import os

EQUIVALENCIAS = {
    'AGROMAIS': 'AGRO',
    'AGRO+': 'AGRO',
    'GLOBOSAT+': 'GLOBOSAT',
    'AMCBRASIL': 'AMC',
    'DISCOVERYCHANNEL': 'DISCOVERY',
    'DISCOVERYSCIENE': 'DISCOVERYSCIENCE',
    'DUMDUM': 'ZOOMOO',
    'ZOOMOOKIDS': 'ZOOMOO',
    'ESPN1': 'ESPN',
    'FILMARTS': 'FILMARTES',
    'FOXNEWSCHANNEL': 'FOXNEWS',
    'FOODNETWORKHDBRASIL': 'FOODNETWORK',
    'CARTOONNETWORKBRAZIL': 'CARTOONNETWORK',
    'H2': 'HISTORY2',
    'INVESTIGACAODISCOVERY': 'DISCOVERYINVESTIGACAO',
    'DISCOVERYINVESTIGACAO': 'DISCOVERYINVESTIGACAO',
    'JPNEWS': 'JOVEMPANNEWS',
    'LIFETIMEBRAZIL': 'LIFETIME',
    'MAXPRIMEE': 'MAXPRIME',
    'MUSICBOXBRAZIL': 'MUSICBOXBRASIL',
    'PARAMOUNTNETWORK': 'PARAMOUNTCHANNEL',
    'PREMIEREHD2': 'PREMIERE2',
    'PREMIEREHD4': 'PREMIERE4',
    'PREMIEREHD5': 'PREMIERE5',
    'PREMIEREFC': 'PREMIERE',
    'PREMIERECLUBES': 'PREMIERE',
    'PRIMEBOXBRASIL': 'PRIMEBOXBRAZIL',
    'SICTV': 'SIC',
    'SYFY': 'USA',
    'USABR': 'USA',
    'USAHD': 'USA',
    'USANETWORK': 'USA',
    'TRACEBRAZUCA': 'TRACEBRASIL',
    'UNIVERSAL': 'UNIVERSALTV',
    'UNIVERSALCHANNEL': 'UNIVERSALTV',
    'WARNERCHANNEL': 'WARNER',
    'EENTERTAINMENTTELEVISION': 'E',
    'HISTORYCHANNEL': 'HISTORY',
    'DISCOVERYHDTHEATER': 'DISCOVERYTHEATER',
    'TCMTURNERCLASSIC': 'TCM',
    'TRAVELBOXBRAZIL': 'TRAVELBOXBRASIL',
    'VIVA': 'GLOBOPLAYNOVELAS',
    'SONY': 'SONYCHANNEL',
    'PREMIERE5BRAZIL': 'PREMIERE5',
}

NOMES_FINAIS = {
    'WARNER': 'Warner Channel',
    'DISCOVERYTHEATER': 'Discovery Theater',
    'E': 'E!',
    'GLOBOSAT': 'Globosat',
    'GLOBOPLAYNOVELAS': 'Globoplay Novelas',
    'USA': 'USA',
    'SONYCHANNEL': 'Sony Channel',
    'PREMIERE5': 'Premiere 5',
    'PREMIERE': 'Premiere',
    'DISCOVERYINVESTIGACAO': 'Discovery Investigação',
    'AGRO': 'Agro+',
    'AMC': 'AMC',
    'DISCOVERY': 'Discovery',
    'DISCOVERYSCIENCE': 'Discovery Science',
    'ZOOMOO': 'ZooMoo',
    'ESPN': 'ESPN',
    'FILMARTES': 'Film & Arts',
    'FOXNEWS': 'Fox News',
    'FOODNETWORK': 'Food Network',
    'CARTOONNETWORK': 'Cartoon Network',
    'HISTORY': 'History',
    'HISTORY2': 'History 2',
    'JOVEMPANNEWS': 'Jovem Pan News',
    'LIFETIME': 'Lifetime',
    'MAXPRIME': 'Maxprime',
    'MUSICBOXBRASIL': 'Music Box Brasil',
    'PARAMOUNTCHANNEL': 'Paramount Channel',
    'PREMIERE2': 'Premiere 2',
    'PREMIERE3': 'Premiere 3',
    'PREMIERE4': 'Premiere 4',
    'PREMIERE6': 'Premiere 6',
    'PREMIERE7': 'Premiere 7',
    'PREMIERE8': 'Premiere 8',
    'PRIMEBOXBRAZIL': 'Prime Box Brazil',
    'SIC': 'SIC',
    'TRACEBRASIL': 'Trace Brasil',
    'UNIVERSALTV': 'Universal TV',
    'TCM': 'TCM',
    'TRAVELBOXBRASIL': 'Travel Box Brasil',
}

def normalizar_nome(nome):
    nome = nome.upper()
    nome = nome.replace('Ç', 'C').replace('Ã', 'A').replace('Õ', 'O').replace('É', 'E')
    nome = nome.replace('Ê', 'E').replace('Á', 'A').replace('Ó', 'O').replace('Í', 'I')
    nome = nome.replace('Ú', 'U').replace('Â', 'A').replace('Ô', 'O')
    nome = re.sub(r'\s*(HD|FHD|4K|SD|HEVC|H265)\s*$', '', nome)
    nome = nome.replace(' ', '').replace('_', '').replace('-', '').replace('!', '')
    nome = nome.replace('+', '').replace('&', '').replace('.', '').replace(',', '')
    
    if nome in EQUIVALENCIAS:
        return EQUIVALENCIAS[nome]
    
    return nome

def carregar_xml(caminho):
    if not os.path.exists(caminho):
        return None
    tree = ET.parse(caminho)
    root = tree.getroot()
    
    canais = {}
    for ch in root.findall('.//channel'):
        cid = ch.get('id', '')
        nome = ch.find('display-name').text if ch.find('display-name') is not None else ''
        canais[cid] = nome
    
    programas = []
    for prog in root.findall('.//programme'):
        programas.append({
            'start': prog.get('start', ''),
            'stop': prog.get('stop', ''),
            'channel': prog.get('channel', ''),
            'title': prog.find('title').text if prog.find('title') is not None else '',
            'sub_title': prog.find('sub-title').text if prog.find('sub-title') is not None else '',
            'desc': prog.find('desc').text if prog.find('desc') is not None else '',
            'categories': [c.text for c in prog.findall('category') if c.text],
            'date': prog.find('date').text if prog.find('date') is not None else '',
            'length': prog.find('length').text if prog.find('length') is not None else '',
            'country': prog.find('country').text if prog.find('country') is not None else '',
            'rating': prog.find('rating').find('value').text if prog.find('rating') is not None and prog.find('rating').find('value') is not None else '',
        })
    
    return {'canais': canais, 'programas': programas}

def mesclar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    arquivos = [
        os.path.join(base_dir, 'epg_guiadetv.xml'),
        os.path.join(base_dir, 'epg_meuguia.xml'),
        os.path.join(base_dir, 'epg_tvplus.xml'),
        os.path.join(base_dir, 'epg_mitv.xml'),
        os.path.join(base_dir, 'epg_webfinal.xml'),
        os.path.join(base_dir, 'epg_UFCfightpass.xml'),
    ]
    
    root = ET.Element('tv')
    root.set('generator-info-name', 'EPG Mesclado')
    
    nomes_processados = {}
    total_eventos = 0
    
    for arquivo in arquivos:
        dados = carregar_xml(arquivo)
        if not dados:
            print(f'  Pulando {os.path.basename(arquivo)} (não encontrado)')
            continue
        
        print(f'  Processando {os.path.basename(arquivo)}...')
        adicionados = 0
        
        for cid, nome in dados['canais'].items():
            nome_norm = normalizar_nome(nome)
            if nome_norm in nomes_processados:
                continue
            
            nome_final = NOMES_FINAIS.get(nome_norm, nome)
            nomes_processados[nome_norm] = nome_final
            
            channel = ET.SubElement(root, 'channel')
            channel.set('id', nome_final)
            display = ET.SubElement(channel, 'display-name')
            display.text = nome_final
            
            for prog in dados['programas']:
                if prog['channel'] == cid:
                    p = ET.SubElement(root, 'programme')
                    p.set('start', prog['start'])
                    p.set('stop', prog['stop'])
                    p.set('channel', nome_final)
                    
                    title = ET.SubElement(p, 'title')
                    title.text = prog['title']
                    
                    if prog['sub_title']:
                        sub = ET.SubElement(p, 'sub-title')
                        sub.text = prog['sub_title']
                    
                    for cat in prog['categories']:
                        c = ET.SubElement(p, 'category')
                        c.text = cat
                    
                    if prog['desc']:
                        desc = ET.SubElement(p, 'desc')
                        desc.text = prog['desc']
                    
                    if prog['date']:
                        date = ET.SubElement(p, 'date')
                        date.text = prog['date']
                    
                    if prog['length']:
                        length = ET.SubElement(p, 'length')
                        length.text = prog['length']
                    
                    if prog['country']:
                        country = ET.SubElement(p, 'country')
                        country.text = prog['country']
                    
                    if prog['rating']:
                        rating = ET.SubElement(p, 'rating')
                        value = ET.SubElement(rating, 'value')
                        value.text = prog['rating']
                    
                    total_eventos += 1
            
            adicionados += 1
        
        print(f'    {adicionados} canais adicionados')
    
    caminho_saida = os.path.join(base_dir, 'epg.xml')
    tree = ET.ElementTree(root)
    tree.write(caminho_saida, encoding='utf-8', xml_declaration=True)
    
    print()
    print(f'Total de canais: {len(nomes_processados)}')
    print(f'Total de eventos: {total_eventos}')
    print(f'XML salvo em: {caminho_saida}')
    print(f'Tamanho: {os.path.getsize(caminho_saida) / 1024:.0f} KB')

if __name__ == '__main__':
    mesclar()
