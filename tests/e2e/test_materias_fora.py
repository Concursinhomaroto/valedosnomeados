# -*- coding: utf-8 -*-
# "Materias que ja passaram": prova feita nao volta (ex.: Direito Administrativo da SESAU-AL). A
# materia — um chefao ou varios pela busca — sai das questoes (Treinar, revisao por questoes,
# simulados do cronograma, montar prova) sem apagar nada do Acervo; desmarcar devolve.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k3','name':'Complementar','icon':'🧩'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':[sub('s1','Pré-natal'),sub('s2','Puerpério')]}],
                'k3':[{'id':'t4','name':'Dir. Administrativo: Ética no serviço público','icon':'⚔️','subtopics':[sub('s3','Ética')]},
                      {'id':'t5','name':'Dir. Administrativo: Constituição de Alagoas','icon':'⚔️','subtopics':[sub('s4','Constituição')]},
                      {'id':'t6','name':'Informática: Hardware','icon':'⚔️','subtopics':[sub('s5','Hardware')]},
                      {'id':'t7','name':'Sem questão nenhuma','icon':'⚔️','subtopics':[sub('s6','Vazio')]}]}})

ACERVO="""()=>{db.acervo=[];const subs=[['s1','Pré-natal','Saúde da Mulher','k1','Enfermagem'],['s2','Puerpério','Saúde da Mulher','k1','Enfermagem'],
  ['s3','Ética','Dir. Administrativo: Ética no serviço público','k3','Complementar'],['s4','Constituição','Dir. Administrativo: Constituição de Alagoas','k3','Complementar'],
  ['s5','Hardware','Informática: Hardware','k3','Complementar']];
  subs.forEach(([sid,sn,tn,kid,kn])=>{for(let j=0;j<3;j++){const q={questao:'Q'+j+' '+sid+': julgue.',correta:'C',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:sid,subName:sn,topicName:tn,kingdomId:kid,kingdomName:kn,kingdomIcon:'x'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});}});return db.acervo.length;}"""

POOL="()=>{const p=treinoPoolCompleto();const c={};p.forEach(q=>{c[q.subId]=(c[q.subId]||0)+1;});return {n:p.length,c};}"

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        n=await page.evaluate(ACERVO)
        await page.evaluate("()=>{db.materiasFora={};treinoFiltro={materia:'',chefao:'',assunto:'',formato:'',estado:'',nivel:''};showScreen('simgeral');renderSimGeralScreen();return true;}")
        assert n==15

        print('=== A) painel fechado, so chefao que tem questao, com a contagem ===')
        r=await page.evaluate("""()=>{const d=document.getElementById('fora-painel');
          return {existe:!!d,aberto:d&&d.open,badge:!!d.querySelector('.fora-badge'),
                  nomes:[...d.querySelectorAll('.fora-nome')].map(x=>x.textContent),ns:[...d.querySelectorAll('.fora-n')].map(x=>x.textContent)};}""")
        print('   %s'%r)
        assert r['existe'] and not r['aberto'] and not r['badge']
        assert r['nomes']==['Saúde da Mulher','Dir. Administrativo: Ética no serviço público','Dir. Administrativo: Constituição de Alagoas','Informática: Hardware']
        assert r['ns'][:2]==['6 questões','3 questões']          # 'Sem questão nenhuma' nem aparece
        print('   OK\n')

        print('=== B) tirar um chefao: sai das questoes, nada e apagado, o motivo fica ===')
        r=await page.evaluate("""()=>{const antes=treinoPoolCompleto().length;
          document.getElementById('fora-painel').open=true;foraAberto=true;foraMotivo='SESAU-AL';
          foraAlternar('t4');
          const d=document.getElementById('fora-painel');
          return {antes,pool:(()=>{const p=treinoPoolCompleto();const c={};p.forEach(q=>{c[q.subId]=(c[q.subId]||0)+1;});return {n:p.length,c};})(),
                  acervo:db.acervo.length,mf:db.materiasFora.t4,badge:(d.querySelector('.fora-badge')||{}).textContent,
                  aberto:d.open,tag:(d.querySelector('.fora-tag')||{}).textContent,
                  riscado:!!d.querySelector('.fora-off .fora-nome')};}""")
        print('   %s'%r)
        assert r['antes']==15 and r['pool']['n']==12 and 's3' not in r['pool']['c'] and r['pool']['c']['s4']==3
        assert r['acervo']==15                                # o Acervo guarda tudo
        assert r['mf']['motivo']=='SESAU-AL' and r['mf']['em'] and '1 fora · 3 questões' in r['badge']
        assert r['aberto'] and 'SESAU-AL' in r['tag'] and r['riscado']
        print('   OK\n')

        print('=== C) busca "Dir. Administrativo" + Tirar os filtrados: so os dois, Informatica fica ===')
        r=await page.evaluate("""()=>{foraBusca='Dir. Administrativo';document.getElementById('fora-corpo').innerHTML=foraCorpoHTML();
          const vis=[...document.querySelectorAll('.fora-nome')].map(x=>x.textContent);
          foraLote('k3',true);
          const f=Object.keys(db.materiasFora).sort();
          foraBusca='';
          const p=treinoPoolCompleto();const subs=[...new Set(p.map(q=>q.subId))].sort();
          return {vis,f,subs,n:p.length};}""")
        print('   %s'%r)
        assert r['vis']==['Dir. Administrativo: Ética no serviço público','Dir. Administrativo: Constituição de Alagoas']
        assert r['f']==['t4','t5'] and r['subs']==['s1','s2','s5'] and r['n']==9
        print('   OK\n')

        print('=== D) vale onde se escolhe questao: revisao por questoes, montar prova e os decks do Treinar ===')
        r=await page.evaluate("""()=>{
          const rev=trevMontar();const revSubs=new Set(rev.itens.map(q=>q.subId));
          const mont=montarPool('todas').map(x=>x.q.subId);
          const deck=treinarDecks().find(d=>d.id==='nuncavistas').itens.map(q=>q.subId);
          return {revFora:['s3','s4'].some(s=>revSubs.has(s)),montFora:mont.some(s=>s==='s3'||s==='s4'),montN:mont.length,deckFora:deck.some(s=>s==='s3'||s==='s4'),deckN:deck.length};}""")
        print('   %s'%r)
        assert not r['revFora'] and not r['montFora'] and r['montN']==9 and not r['deckFora'] and r['deckN']==9
        print('   OK\n')

        print('=== E) voltar: o reino devolve os dois, o chefao volta sozinho ===')
        r=await page.evaluate("""()=>{foraLote('k3',false);const a=Object.keys(db.materiasFora).length;const n1=treinoPoolCompleto().length;
          foraAlternar('t6');foraAlternar('t6');
          return {fora:a,n:n1,depois:treinoPoolCompleto().length,acervo:db.acervo.length};}""")
        print('   %s'%r)
        assert r['fora']==0 and r['n']==15 and r['depois']==15 and r['acervo']==15
        print('   OK\n')

        print('=== F) prova realizada lembra do painel ===')
        r=await page.evaluate("""()=>{db.editais=[{id:'ed1',nome:'SESAU-AL',cargo:'Enf',banca:'X',data:'2026-08-01',status:'inscrito',icon:'🏥',color:'#6c47ff',disciplinas:[]}];
          changeEditalStatus('ed1','realizado');return true;}""")
        await page.wait_for_timeout(3300)
        t=await page.evaluate("()=>document.getElementById('toast').textContent")
        print('   toast: %s'%t)
        assert 'Matérias que já passaram' in t
        print('   OK\n')

        print('=== G) celular: sem rolagem lateral ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>{foraAberto=true;showScreen('simgeral');renderSimGeralScreen();return {w:document.documentElement.scrollWidth,iw:innerWidth};}")
        print('   %s'%r)
        assert r['w']<=r['iw']+1
        print('   OK\n')

        e=real_errors(errs)
        assert not e,e
        print('erros de JS: nenhum\nOK')
        await b.close()
asyncio.run(main())
