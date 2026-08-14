Scrapers feito em Python3 para extrair programação de canais de TV do meuguia.tv, guiadetv.com, mi.tv, tvplus.com.br, webfinal.com.br, urbantv.com.br, tvmap.com.br, ufc.com.br e criar arquivo EPG deles (separados) até 5 dias na frente.
Nos sites que tem a informação, é extraído a sinopse, gênero, classificação indicativa, temporada/episódio, país, duração, etc...

O arquivo "EPG.xml" na home é uma junção de todos EPGs em um só com remoção de duplicados através do mesclador.py

Os arquivos podem ser carregados diretamente no player (Tivimate, etc...), se não aparecer a programação em alguns, experimente usar a função "Atribuir EPG" e fazer o match certo, pois se não estiver 100% idêntico ao nome do canal, ele não vai acertar.

Pode conter bugs! Eu não sou programador, fiz de besteira usando Deepseek e ajustando aos poucos, mas está funcionando muito bem!
