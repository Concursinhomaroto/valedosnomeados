# -*- coding: utf-8 -*-
# A distribuicao do prompt saia da PROPORCAO DE ASSUNTOS por reino, que nao e como a
# banca monta a prova: um reino com 40 assuntos ganhava de um com 5, mesmo quando a
# banca cobra 10 questoes do primeiro e 30 do segundo. Agora a cota sai do numero
# DECLARADO no edital em foco.
import asyncio, json, re, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUBS={'Português':[('t1','Gramática',['Concordância verbal','Crase'])],
      'Legislação de Alagoas':[('t2','Estatuto do servidor',['Regime disciplinar'])],
      'Saúde Pública':[('t3','SUS',['Princípios do SUS','Lei 8080'])],
      'Enfermagem':[('t4','Urgência',['Choque séptico','PCR','Sondagem vesical'])]}

def seed():
    kingdoms,topics=[],{}
    n=0
    for i,(kn,tops) in enumerate(SUBS.items()):
        kid='k%d'%(i+1)
        kingdoms.append({'id':kid,'name':kn,'icon':'🏰','color':'#22d3ee'})
        topics[kid]=[]
        for tid,tn,subs in tops:
            lst=[]
            for sn in subs:
                n+=1
                lst.append({'id':'s%d'%n,'name':sn,'priority':70,'studied':True})
            topics[kid].append({'id':tid,'name':tn,'icon':'⚔️','subtopics':lst})
    return make_seed({'studyNickname':'Leo','kingdoms':kingdoms,'topics':topics})

EDITAL = """(questoes)=>{
  const d=(nome,q,nomes)=>({nome,questoes:q,assuntos:nomes.map(x=>({nome:x,prev:1}))});
  db.editais=[{id:'e1',nome:'SESAU/AL 2026',cargo:'Enfermeiro',banca:'Cebraspe',
    data:'2026-11-01',status:'inscrito',createdAt:'2026-01-01',
    disciplinas:[
      d('Português',questoes[0],['Concordância verbal','Crase']),
      d('Legislação de Alagoas',questoes[1],['Regime disciplinar']),
      d('Saúde Pública',questoes[2],['Princípios do SUS','Lei 8080']),
      d('Conhecimentos Específicos',questoes[3],['Choque séptico','PCR','Sondagem vesical'])]}];
  db.editalFoco='e1';
  renderSimGeralScreen();
  return true;}"""

def cabecalhos(txt):
    return re.findall(r'^■ (.+)$', txt, re.M)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) sem edital em foco: a tela avisa que a distribuicao e chute ===')
        r=await page.evaluate("""()=>{
          const t=simColarPromptTexto();
          const box=document.querySelector('.sg-cota-falta');
          return {temAviso:!!box,texto:box?box.innerText:'',estimativa:t.includes('É uma estimativa'),
                  cota:t.includes('COTA DE CADA BLOCO')};}""")
        print('   caixa de aviso na tela: %s'%r['temAviso'])
        print('   o prompt assume que é estimativa: %s · promete cota: %s'%(r['estimativa'],r['cota']))
        assert r['temAviso'] and r['estimativa'] and not r['cota']
        assert 'Editais' in r['texto'] and 'foco' in r['texto']
        print('   OK\n')

        print('=== B) com o edital: cota de cada bloco, com os numeros da banca ===')
        await page.evaluate(EDITAL,[20,10,20,70])
        txt=await page.evaluate("""()=>{document.getElementById('sg-colar-qtd').value='120';
          return simColarPromptTexto();}""")
        cabs=cabecalhos(txt)
        for c in cabs: print('   %s'%c)
        assert cabs==['PORTUGUÊS — 20 itens (o edital cobra 20)',
                      'LEGISLAÇÃO DE ALAGOAS — 10 itens (o edital cobra 10)',
                      'SAÚDE PÚBLICA — 20 itens (o edital cobra 20)',
                      'CONHECIMENTOS ESPECÍFICOS — 70 itens (o edital cobra 70)'], cabs
        assert 'Conferência: 20 + 10 + 20 + 70 = 120 itens' in txt
        assert 'SESAU/AL 2026' in txt
        assert 'A COTA DE CADA BLOCO É OBRIGATÓRIA' in txt
        assert 'É uma estimativa' not in txt
        print('   conferência e nome do edital no prompt: ok')
        print('   OK\n')

        print('=== C) a numeracao impressa bate com a ordem de simColarLista ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-qtd').value='120';
          const t=simColarPromptTexto();
          const nums={};
          t.split('\\n').forEach(l=>{const m=l.match(/^(\\d+)\\. (.+?) \\(/);if(m)nums[+m[1]]=m[2];});
          return {impresso:nums,lista:simColarLista.map(c=>c.sub.name)};}""")
        imp=[r['impresso'][str(i+1)] for i in range(len(r['lista']))]
        print('   lista: %s'%r['lista'])
        assert imp==r['lista'], (imp,r['lista'])
        print('   os %s números batem com a ordem que o simColarMapa usa'%len(imp))
        print('   OK\n')

        print('=== D) prova menor: a cota encolhe junto e ainda fecha a conta ===')
        for qtd in (60,40,180):   # o select so tem 40/60/120/180
            r=await page.evaluate("""(qtd)=>{document.getElementById('sg-colar-qtd').value=String(qtd);
              const t=simColarPromptTexto();
              const m=t.match(/Conferência: (.+?) = (\\d+)/);
              return {conta:m?m[1]:null,soma:m?+m[2]:null};}""",qtd)
            print('   %s itens -> %s = %s'%(qtd,r['conta'],r['soma']))
            assert r['soma']==qtd, (qtd,r['soma'])
            assert sum(int(x) for x in r['conta'].split(' + '))==qtd
        print('   arredondamento nunca desfaz o total pedido')
        print('   OK\n')

        print('=== E) numeros que nao dividem redondo ===')
        await page.evaluate(EDITAL,[17,13,29,61])
        r=await page.evaluate("""()=>{document.getElementById('sg-colar-qtd').value='120';
          const t=simColarPromptTexto();
          const m=t.match(/Conferência: (.+?) = (\\d+)/);
          return {conta:m[1],soma:+m[2]};}""")
        print('   edital 17/13/29/61 (=120) -> %s = %s'%(r['conta'],r['soma']))
        assert r['soma']==120
        print('   OK\n')

        print('=== F) bloco sem assunto estudado nao ganha cota ===')
        r=await page.evaluate("""()=>{
          // ninguem estudou Português ainda
          db.topics['k1'][0].subtopics.forEach(s=>s.studied=false);
          document.getElementById('sg-colar-qtd').value='120';
          const t=simColarPromptTexto();
          const m=t.match(/Conferência: (.+?) = (\\d+)/);
          return {cabs:(t.match(/^■ .+$/gm)||[]),conta:m[1],soma:+m[2],
                  temPt:/PORTUGU/.test(t)};}""")
        for c in r['cabs']: print('   %s'%c)
        print('   soma: %s'%r['soma'])
        assert not r['temPt'], 'bloco sem assunto estudado nao pode aparecer'
        assert r['soma']==120
        print('   a cota dele se redistribui, em vez de pedir item de um bloco vazio')
        print('   OK\n')

        print('=== G) assunto estudado fora do edital fica de fora por padrao ===')
        r=await page.evaluate("""()=>{
          db.topics['k1'][0].subtopics.forEach(s=>s.studied=true);
          db.topics['k4'][0].subtopics.push({id:'s99',name:'Assunto avulso',priority:70,studied:true});
          document.getElementById('sg-colar-qtd').value='120';
          const t=simColarPromptTexto();
          const semEle={fora:/FORA DOS BLOCOS ACIMA/.test(t),temNome:t.includes('Assunto avulso'),
                        n:simColarLista.length};
          // ligando a opcao, ele volta — no fim da lista, sem cota
          try{localStorage.setItem(COLAR_FORA_KEY,'1');}catch(e){}
          const t2=simColarPromptTexto();
          return {semEle,
                  comEle:{fora:/FORA DOS BLOCOS ACIMA/.test(t2),
                          temNome:t2.includes('Assunto avulso'),
                          n:simColarLista.length,
                          ultimo:simColarLista[simColarLista.length-1].sub.name}};}""")
        print('   padrão: %s assuntos, bloco "fora": %s'
              %(r['semEle']['n'],r['semEle']['fora']))
        print('   com a opção ligada: %s assuntos, último: %r'
              %(r['comEle']['n'],r['comEle']['ultimo']))
        assert not r['semEle']['fora'] and not r['semEle']['temNome']
        assert r['comEle']['fora'] and r['comEle']['ultimo']=='Assunto avulso'
        assert r['comEle']['n']==r['semEle']['n']+1
        await page.evaluate("()=>{try{localStorage.setItem(COLAR_FORA_KEY,'0');}catch(e){}return true;}")
        print('   OK\n')

        print('=== H) o conversor agrupa igual, mas sem inventar cota ===')
        c=await page.evaluate("()=>simColarPromptConverter()")
        cabs=cabecalhos(c)
        for x in cabs: print('   %s'%x)
        assert all('o edital cobra' in x or 'não declara' in x or 'sem cota' in x for x in cabs), cabs
        assert 'itens (o edital cobra' not in c, 'o conversor nao pode pedir cota: a prova ja existe'
        assert 'SESAU/AL 2026' in c
        print('   OK\n')

        print('=== I) a tela mostra a mesma reparticao do prompt ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-qtd').value='120';
          renderSimGeralScreen();
          const box=document.querySelector('.sg-cota-ok');
          return box?box.innerText.replace(/\\n/g,' '):null;}""")
        print('   %s'%r)
        assert r and 'SESAU/AL 2026' in r
        print('   OK\n')

        print('=== J) ponta a ponta: o numero do bloco pousa no miniboss certo ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-qtd').value='120';
          simColarPromptTexto();
          const achar=n=>simColarLista.findIndex(c=>c.sub.name===n)+1;
          const iCrase=achar('Crase'), iPCR=achar('PCR');
          simColarLote=[];
          document.getElementById('sg-colar-txt').value=JSON.stringify([
            {assunto:iCrase,assuntoNome:'Crase',afirmacao:'Bla.',gabarito:'C',explicacao:'x'},
            {assunto:iPCR,assuntoNome:'PCR',afirmacao:'Ble.',gabarito:'E',explicacao:'y'}]);
          simColarAdicionar();
          const {grupos}=simColarMapa();
          return {iCrase,iPCR,alvos:grupos.map(g=>g.alvo?g.alvo.sub.name:null)};}""")
        print('   Crase = nº %s · PCR = nº %s -> pousaram em %s'%(r['iCrase'],r['iPCR'],r['alvos']))
        assert sorted(x for x in r['alvos'] if x)==['Crase','PCR']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
