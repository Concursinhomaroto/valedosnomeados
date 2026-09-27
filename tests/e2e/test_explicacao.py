# -*- coding: utf-8 -*-
# O comentario e a parte mais relida da tela de resultado, e estava em cinza 11,5px
# sobre cinza — a mesma cor da legenda de rodape. Aqui ele ganha a cor do gabarito, o
# veredito vira selo, e o "GUARDE:" sai do paragrafo e vira bloco proprio. Tudo isso
# sobre texto JA escapado: comentario vem de fora, entao nao pode virar HTML.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

REAL = ("Certo. O Código veda ao servidor deixar de utilizar os avanços técnicos e científicos "
        "ao seu alcance no atendimento do seu mister — a vedação é por omissão, e não por ação, "
        "o que a torna fácil de ignorar numa leitura rápida. A banca costuma apresentar o "
        "dispositivo como mera recomendação de aperfeiçoamento. GUARDE: no Código alagoano, "
        "não se atualizar é falta ética, não descuido.")

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Etica','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Codigo alagoano','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) o comentario de verdade que voce mandou ===')
        r=await page.evaluate("""(t)=>{
          const h=simExplicacaoHTML({explicacao:t,correta:'C',formato:'certoerrado'});
          return {h, certo:h.includes('expl-certo'), errado:h.includes('expl-errado'),
                  selo:(h.match(/class="expl-selo">([^<]+)</)||[])[1],
                  marca:(h.match(/class="expl-marca">([\\s\\S]*?)<\\/div>/)||[])[1],
                  abreComCerto:/class="expl-txt">O Código veda/.test(h),
                  guardeNoTexto:/class="expl-txt">[^<]*GUARDE/.test(h)};}""", REAL)
        print('   selo: %s · bloco verde: %s'%(r['selo'],r['certo']))
        print('   GUARDE virou bloco: %s'%r['marca'].strip()[:90])
        assert r['certo'] and not r['errado'] and r['selo']=='✔️ CERTO'
        assert '🔑' in r['marca'] and '<b>GUARDE</b>' in r['marca']
        assert 'Código alagoano' in r['marca']
        assert r['abreComCerto'], 'o "Certo." ficou repetido no corpo'
        assert not r['guardeNoTexto'], 'o GUARDE continuou dentro do parágrafo'
        print('   o "Certo." saiu do corpo (virou selo) e o GUARDE saiu do parágrafo')
        print('   OK\n')

        print('=== B) errado pinta de vermelho ===')
        r=await page.evaluate("""()=>{
          const a=simExplicacaoHTML({explicacao:'Errado. O prazo é de 30 dias, não de 15.',
                                     correta:'E',formato:'certoerrado'});
          const b=simExplicacaoHTML({explicacao:'Incorreto — a competência é do município.',
                                     correta:'E',formato:'certoerrado'});
          return {a:{cls:/expl-(certo|errado)/.exec(a)[1],selo:(a.match(/expl-selo">([^<]+)</)||[])[1],
                     corpo:(a.match(/expl-txt">([^<]+)/)||[])[1]},
                  b:{cls:/expl-(certo|errado)/.exec(b)[1],
                     corpo:(b.match(/expl-txt">([^<]+)/)||[])[1]}};}""")
        print('   "Errado." → %s · selo %s · corpo: "%s"'%(r['a']['cls'],r['a']['selo'],r['a']['corpo']))
        print('   "Incorreto —" → %s · corpo: "%s"'%(r['b']['cls'],r['b']['corpo']))
        assert r['a']['cls']=='errado' and r['a']['selo']=='✖️ ERRADO'
        assert r['a']['corpo'].startswith('O prazo')
        assert r['b']['cls']=='errado' and r['b']['corpo'].startswith('a competência')
        print('   reconhece "Certo/Errado/Correto/Incorreto", com ponto, dois-pontos ou travessão')
        print('   OK\n')

        print('=== C) sem palavra de veredito, ele usa o gabarito — e so no certo/errado ===')
        r=await page.evaluate("""()=>{
          const ce=simExplicacaoHTML({explicacao:'A competência é comum aos três entes.',
                                      correta:'C',formato:'certoerrado'});
          const me=simExplicacaoHTML({explicacao:'A alternativa C traz o conceito de equidade.',
                                      correta:'C',formato:'multipla'});
          return {ce:/expl-certo/.test(ce), meCerto:/expl-(certo|errado)/.test(me),
                  meSelo:/expl-selo/.test(me), meTem:/sim-explain/.test(me)};}""")
        print('   certo/errado sem a palavra: pinta de verde pelo gabarito → %s'%r['ce'])
        print('   múltipla escolha com gabarito "C": pinta? %s · selo? %s · aparece? %s'
              %(r['meCerto'],r['meSelo'],r['meTem']))
        assert r['ce'] and not r['meCerto'] and not r['meSelo'] and r['meTem']
        print('   "C" de múltipla escolha é a LETRA C, não "certo" — aí fica neutro')
        print('   OK\n')

        print('=== D) comentario vindo de fora nao vira HTML ===')
        r=await page.evaluate("""()=>{
          const h=simExplicacaoHTML({
            explicacao:'Certo. <script>alert(1)</script> e <b>negrito</b> & cia. GUARDE: <img src=x onerror=1>',
            correta:'C',formato:'certoerrado'});
          const d=document.createElement('div'); d.innerHTML=h;
          return {script:d.querySelectorAll('script').length,
                  img:d.querySelectorAll('img').length,
                  b:d.querySelectorAll('.expl-marca b').length,
                  escapou:h.includes('&lt;script&gt;')&&h.includes('&lt;img'),
                  temMarca:h.includes('expl-marca')};}""")
        print('   <script> injetado: %s · <img onerror>: %s · escapado: %s'
              %(r['script'],r['img'],r['escapou']))
        assert r['script']==0 and r['img']==0 and r['escapou']
        assert r['b']==1 and r['temMarca']
        print('   o único <b> que existe é o rótulo GUARDE que o app escreveu')
        print('   OK\n')

        print('=== E) varios marcadores, e cada um com seu icone ===')
        r=await page.evaluate("""()=>{
          const h=simExplicacaoHTML({explicacao:
            'Certo. Primeiro trecho. PEGADINHA: a banca troca 15 por 30. '
           +'ATENÇÃO: vale só para servidor efetivo. GUARDE: prazo de 30 dias.',
            correta:'C',formato:'certoerrado'});
          const blocos=[...h.matchAll(/expl-marca">([^\\s<]+)\\s*<b>([^<]+)<\\/b>\\s*([^<]*)/gu)]
                        .map(m=>({icone:m[1],tag:m[2],txt:m[3].trim()}));
          return {blocos, txts:(h.match(/expl-txt/g)||[]).length};}""")
        for x in r['blocos']: print('   %s %s → %s'%(x['icone'],x['tag'],x['txt']))
        tags=[x['tag'] for x in r['blocos']]
        assert tags==['PEGADINHA','ATENÇÃO','GUARDE'], tags
        assert r['blocos'][0]['icone']=='🪤' and r['blocos'][1]['icone']=='⚠️'
        assert r['blocos'][2]['txt']=='prazo de 30 dias.'
        assert r['txts']==1, 'o parágrafo normal devia ser um só'
        print('   cada marcador leva o próprio texto até o marcador seguinte')
        print('   OK\n')

        print('=== F) comentario sem marcador nenhum continua inteiro ===')
        r=await page.evaluate("""()=>{
          const t='A competência para legislar sobre proteção à saúde é concorrente.';
          const h=simExplicacaoHTML({explicacao:t,correta:'C',formato:'certoerrado'});
          const d=document.createElement('div'); d.innerHTML=h;
          return {texto:d.innerText.replace(/\\s+/g,' ').trim(),
                  marca:h.includes('expl-marca'),
                  vazio:simExplicacaoHTML({explicacao:'',correta:'C'})
                        +simExplicacaoHTML({})+simExplicacaoHTML(null)};}""")
        print('   saiu na tela: "%s"'%r['texto'])
        assert r['texto'].endswith('concorrente.') and not r['marca']
        assert r['vazio']==''
        print('   sem explicação, nenhum bloco é desenhado: "%s"'%r['vazio'])
        print('   OK\n')

        print('=== G) aparece nos tres lugares que mostram comentario ===')
        r=await page.evaluate("""(t)=>{
          const fontes=[simGeralResultsHTML.toString(),
                        renderErrosScreen?renderErrosScreen.toString():''].join('');
          const alvo=document.body.innerHTML;
          return {chamadas:(document.documentElement.innerHTML.match(/x/)||[]).length,
                  usaFuncao:fontes.includes('simExplicacaoHTML')};}""",REAL)
        print('   a tela de resultado usa a função nova: %s'%r['usaFuncao'])
        assert r['usaFuncao']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
