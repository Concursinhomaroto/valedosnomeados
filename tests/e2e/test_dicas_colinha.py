# -*- coding: utf-8 -*-
# Dicas, etapa 3: "Numeros que caem" (quadro so com os numeros, por materia, inclusive os
# que voce ja sabe) e a Colinha — uma pagina so pra imprimir, com as dicas da materia ou do
# edital em foco. A janela de impressao e escrita de fora: o HTML gerado nao leva tag de
# script (um fechamento de script literal no codigo derruba o app inteiro — ver
# docs/plano-refatoracao.md), e o teste confere isso no proprio arquivo.
import asyncio, json, os, re, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, make_seed
from test_aba_dicas import abrir, graves, PACOTE, OUT

APP=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','app','index.html')

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'},
                  {'id':'kEnf','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'kPt':[{'id':'tP','name':'Gramática','icon':'✏️','subtopics':[
                  {'id':'sCrase','name':'Crase','priority':70},{'id':'sReg','name':'Regência verbal','priority':70}]}],
                'kEnf':[{'id':'tE','name':'Imunização','icon':'💉','subtopics':[
                  {'id':'sFrio','name':'Rede de frio','priority':70}]}]},
      'editais':[{'id':'ed1','nome':'Concurso X','banca':'IGEDUC','data':'2026-12-01','icon':'📋','color':'#6c47ff',
                  'disciplinas':[{'id':'d1','nome':'Português','questoes':20,'kingdomId':'kPt',
                                  'assuntos':[{'id':'a1','nome':'Crase','subId':'sCrase','manual':True}]}]}],
      'editalFoco':'ed1'})

EXTRAS=[{'tipo':'numero','materia':'Enfermagem','assunto':'Rede de frio','grupo':'Rede de frio','valor':'+2 a +8 °C',
         'rotulo':'Rede de frio, instância local','bancas':['IGEDUC']},
        {'tipo':'numero','materia':'Enfermagem','assunto':'Rede de frio','grupo':'Rede de frio','valor':'7 dias',
         'rotulo':'Número de exemplo do teste'},
        {'tipo':'numero','materia':'Português','grupo':'Ortografia e sentido','valor':'5','rotulo':'Exemplo: quantos porquês o teste conta'},
        {'materia':'Português','grupo':'Geral','titulo':'Dica geral sem assunto','regra':'Vale pra matéria toda.'}]

async def main():
    os.makedirs(OUT,exist_ok=True)
    fonte=open(APP,encoding='utf-8').read()
    print('=== 0) nenhum fechamento de script literal a mais no app ===')
    abre=len(re.findall(r'<script',fonte)); fecha=len(re.findall(r'</script>',fonte))
    print('   <script: %s · fechamentos: %s'%(abre,fecha))
    # 12 aberturas = 10 blocos + 2 citacoes antigas em texto (contadas na main antes desta etapa)
    assert (abre,fecha)==(12,10), (abre,fecha)
    print('   OK\n')
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':1440,'height':900})
        await page.evaluate("(t)=>{dicasImportarProcessar(t);dicasRelatorioFechar();}",open(PACOTE,encoding='utf-8').read())
        await page.evaluate("(t)=>{dicasImportarProcessar(JSON.stringify(t));dicasRelatorioFechar();}",EXTRAS)
        await page.evaluate("""()=>{const n=db.dicas.find(d=>d.valor==='7 dias');dicaJaSei(n.id,'aba');
          const c=db.dicas.find(d=>d.titulo==='Cujo');dicaJaSei(c.id,'aba');showScreen('dicas');}""")

        print('=== A) Numeros que caem: quadro por materia, com os que ja sei ===')
        r=await page.evaluate("""()=>{
          const chip=[...document.querySelectorAll('#dicas-chips-ver .banco-chip')].map(b=>b.textContent.trim());
          [...document.querySelectorAll('#dicas-chips-ver .banco-chip')][1].click();
          const secoes=[...document.querySelectorAll('#dicas-corpo .dica-grupo-tit')].map(x=>x.innerText.replace(/\\s+/g,' ').trim());
          const cels=[...document.querySelectorAll('#dicas-corpo .dicas-quadro-cel')];
          const r={chip,secoes,n:cels.length,valores:cels.map(c=>c.querySelector('.dica-num-valor').textContent),
                   sabido:cels.filter(c=>c.classList.contains('dica-sei')).length,
                   conta:document.getElementById('dicas-conta').innerText,
                   semCartaoComum:!document.querySelector('#dicas-corpo .dica-card')};
          dicasFiltrarMateria('kEnf');
          r.enf=[...document.querySelectorAll('#dicas-corpo .dicas-quadro-cel .dica-num-valor')].map(x=>x.textContent);
          dicasFiltrarMateria('');
          document.getElementById('dicas-busca').value='instância';dicasBuscar(document.getElementById('dicas-busca'));
          r.busca=[...document.querySelectorAll('#dicas-corpo .dicas-quadro-cel .dica-num-valor')].map(x=>x.textContent);
          return r;}""")
        print('   chips: %s'%r['chip'])
        print('   seções: %s'%r['secoes'])
        print('   %s números %s · sabidos à vista e marcados: %s · "%s"'%(r['n'],r['valores'],r['sabido'],r['conta'].replace('\n',' ')))
        print('   só Enfermagem: %s · busca "instância": %s'%(r['enf'],r['busca']))
        assert r['chip'][1]=='🔢 Números que caem · 3', r['chip']
        assert r['n']==3 and r['sabido']==1 and r['semCartaoComum'], r
        assert any('PORTUGUÊS' in s.upper() for s in r['secoes']) and any('ENFERMAGEM' in s.upper() for s in r['secoes'])
        assert '3 números' in r['conta'] and sorted(r['enf'])==['+2 a +8 °C','7 dias'] and r['busca']==['+2 a +8 °C']
        await page.set_viewport_size({'width':1440,'height':900})
        await page.evaluate("()=>{dicasFiltroLimpar();dicasVer('numeros');window.scrollTo(0,0);}")
        await page.wait_for_timeout(3500)
        await page.screenshot(path=os.path.join(OUT,'dicas_numeros_1440.png'))
        await page.evaluate("()=>{dicasVer('lista');}")
        r=await page.evaluate("()=>({cards:document.querySelectorAll('#dicas-corpo .dica-card').length})")
        assert r['cards']>20
        print('   volta pra lista: %s cartões'%r['cards'])
        print('   OK\n')

        print('=== B) Colinha da materia ===')
        r=await page.evaluate("""()=>{
          const pt=db.dicas.filter(d=>d.kingdomId==='kPt');
          const parse=h=>new DOMParser().parseFromString(h,'text/html');
          const h=dicasColinhaHTML({escopo:'materia',kingdomId:'kPt',comSei:false,comExemplos:true});
          const d=parse(h);
          const comSei=parse(dicasColinhaHTML({escopo:'materia',kingdomId:'kPt',comSei:true,comExemplos:false}));
          return {h1:d.querySelector('h1').textContent,cab:d.querySelector('header span').textContent,
                  dicas:d.querySelectorAll('.d').length,
                  esperado:pt.filter(x=>x.tipo!=='numero'&&!dicaSei(x.id)).length,
                  nums:[...d.querySelectorAll('table.nums tr')].map(t=>[...t.cells].map(c=>c.textContent).join(' ')),
                  temCujo:!!([...d.querySelectorAll('.t')].find(t=>t.textContent==='Cujo')),
                  exemplos:d.querySelectorAll('.ex span').length,
                  grupos:[...d.querySelectorAll('h3')].map(x=>x.textContent),
                  script:/script/i.test(h),
                  comSeiCujo:!!([...comSei.querySelectorAll('.t')].find(t=>t.textContent==='Cujo')),
                  semExemplo:comSei.querySelectorAll('.ex').length,
                  colunas:/column-count:2/.test(h)};}""")
        print('   "%s" · %s'%(r['h1'],r['cab']))
        print('   %s dicas (esperado %s) · números: %s · grupos: %s'%(r['dicas'],r['esperado'],r['nums'],r['grupos']))
        print('   a "já sei" (Cujo) fica de fora: %s · entra com a opção: %s · exemplos: %s · sem exemplos: %s'
              %(not r['temCujo'],r['comSeiCujo'],r['exemplos'],r['semExemplo']==0))
        print('   HTML sem nenhuma tag de script: %s · duas colunas: %s'%(not r['script'],r['colunas']))
        assert r['h1']=='Colinha — Português' and r['dicas']==r['esperado'] and r['nums']==['5 Exemplo: quantos porquês o teste conta']
        assert not r['temCujo'] and r['comSeiCujo'] and r['exemplos']>40 and r['semExemplo']==0
        assert not r['script'] and r['colunas'] and r['grupos'][0]=='Classes e pronomes'
        print('   OK\n')

        print('=== C) Colinha do edital em foco ===')
        r=await page.evaluate("""()=>{
          const d=new DOMParser().parseFromString(dicasColinhaHTML({escopo:'edital',comSei:true,comExemplos:true}),'text/html');
          const t=[...d.querySelectorAll('.t')].map(x=>x.textContent);
          const porTitulo=x=>db.dicas.find(dd=>dd.titulo===x&&dd.kingdomId==='kPt');
          return {h1:d.querySelector('h1').textContent,titulos:t,
                  assuntos:[...new Set(t.map(x=>(porTitulo(x)||{}).subId||'(sem assunto)'))].sort(),
                  semAssuntoPt:db.dicas.filter(dd=>dd.kingdomId==='kPt'&&!dd.subId&&dd.tipo!=='numero').length,
                  materias:[...d.querySelectorAll('h2')].map(x=>x.textContent),
                  temRegencia:t.includes('Preferir'),nums:d.querySelectorAll('table.nums tr').length};}""")
        print('   "%s" · matérias %s'%(r['h1'],r['materias']))
        print('   dicas: %s'%r['titulos'])
        assert r['h1']=='Colinha — Concurso X · IGEDUC' and r['materias']==['Português']
        print('   assuntos na colinha: %s · dicas sem assunto de Português: %s'%(r['assuntos'],r['semAssuntoPt']))
        # entra o assunto cobrado (Crase) e o que nao tem assunto ligado; Regencia (sReg) fica de fora
        assert r['assuntos']==['(sem assunto)','sCrase'], r['assuntos']
        assert 'Crase antes de horas' in r['titulos'] and 'Dica geral sem assunto' in r['titulos']
        assert len(r['titulos'])==r['semAssuntoPt']+1
        assert not r['temRegencia'] and r['nums']==1     # numero sem assunto da materia entra
        print('   entra o assunto que o edital cobra (Crase) e o sem assunto da matéria; Regência e Enfermagem ficam de fora')
        print('   OK\n')

        print('=== D) o botao abre, a janela imprime ===')
        r=await page.evaluate("""()=>{dicasColinhaAbrir();
          const ed=document.querySelector('input[name="dicas-colinha-escopo"][value="edital"]');
          return {aberto:document.getElementById('modal').classList.contains('open'),edital:!ed.disabled,
                  rotulo:ed.parentElement.innerText.trim(),materia:document.getElementById('dicas-colinha-materia').value};}""")
        print('   modal aberto: %s · edital disponível: %s ("%s") · matéria padrão %s'%(r['aberto'],r['edital'],r['rotulo'],r['materia']))
        assert r['aberto'] and r['edital'] and 'Concurso X' in r['rotulo']
        await page.evaluate("()=>{window.__imprimiu=0;}")
        async with page.expect_popup() as pop:
            await page.click('#dicas-colinha-form button:has-text("Gerar e imprimir")')
        jan=await pop.value
        await jan.wait_for_load_state()
        r=await jan.evaluate("()=>({h1:document.querySelector('h1').textContent,d:document.querySelectorAll('.d').length,scripts:document.scripts.length})")
        fechou=await page.evaluate("()=>!document.getElementById('modal').classList.contains('open')")
        print('   janela: "%s" com %s dicas · scripts na janela: %s · modal fechou: %s'%(r['h1'],r['d'],r['scripts'],fechou))
        assert r['h1'].startswith('Colinha — ') and r['d']>10 and r['scripts']==0 and fechou
        await jan.set_viewport_size({'width':900,'height':1200})
        await jan.screenshot(path=os.path.join(OUT,'dicas_colinha.png'))
        await jan.close()
        r=await page.evaluate("""()=>{db.editalFoco=null;dicasColinhaAbrir();
          const ed=document.querySelector('input[name="dicas-colinha-escopo"][value="edital"]');
          const r={desligado:ed.disabled,rotulo:ed.parentElement.innerText.trim()};closeModal();return r;}""")
        print('   sem edital em foco: opção desligada %s ("%s")'%(r['desligado'],r['rotulo']))
        assert r['desligado'] and 'nenhum edital' in r['rotulo']
        print('   OK\n')

        print('=== E) 375 px: quadro sem vazar ===')
        for tema in ['light','dark']:
            await page.evaluate("(t)=>{document.documentElement.setAttribute('data-theme',t);dicasVer('numeros');window.scrollTo(0,0);}",tema)
            await page.set_viewport_size({'width':375,'height':812})
            r=await page.evaluate("""()=>({vaza:[...document.querySelectorAll('#screen-dicas *')].filter(e=>{const r=e.getBoundingClientRect();
                return r.width&&r.right>window.innerWidth+1;}).length,
              cels:[...document.querySelectorAll('.dicas-quadro-cel')].filter(c=>c.getBoundingClientRect().width>0).length})""")
            print('   %-5s: %s células visíveis · elementos vazando %s'%(tema,r['cels'],r['vaza']))
            assert r['cels']==3 and r['vaza']==0
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(OUT,'dicas_numeros_375_escuro.png'))
        print('   OK\n')

        todos=graves(errs)
        print('erros de JS: %s'%(todos or 'nenhum'))
        assert not todos, todos
        await browser.close()
        print('OK')

if __name__=='__main__':
    asyncio.run(main())
