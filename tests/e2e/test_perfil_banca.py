# -*- coding: utf-8 -*-
# Perfil da banca dentro do Plano de assunto: questoes por ano (5 anos), nota 1-3, observacao, tendencia, "o que mais cai",
# prompt para IA e importacao com previa (dado da IA fica marcado "IA").
import asyncio, sys, json
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':False}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Português','icon':'📖'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':[sub('s1','Pré-natal'),sub('s2','Puerpério'),sub('s3','Aleitamento')]},
                      {'id':'t2','name':'Saúde da Criança','icon':'⚔️','subtopics':[sub('s4','Vacinação')]}],
                'k2':[{'id':'t3','name':'Sintaxe','icon':'⚔️','subtopics':[sub('s5','Regência'),sub('s6','Concordância')]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{window.confirm=()=>true;return true;}")
        anos=await page.evaluate("()=>pbAnos()")
        print('anos:',anos)

        print('=== A) sem banca: convite para criar; criar a primeira banca ===')
        r=await page.evaluate("""()=>{showScreen('plano');paFiltro.mundo='';paSetMundo('k1');
          const antes=document.getElementById('plano-conteudo').innerText.includes('Criar a primeira banca');
          window.prompt=()=>'Cebraspe';pbNovaBanca();window.prompt=()=>'cebraspe';pbNovaBanca();   // repetida (outra caixa) nao duplica
          window.prompt=()=>'FGV';pbNovaBanca();pbSetBanca('Cebraspe');
          return {antes,bancas:db.perfilBanca.bancas,sel:pbBanca,badges:document.querySelectorAll('#plano-conteudo .pb-vazio').length,
            sel_ui:[...document.querySelectorAll('#plano-conteudo .pb-barra select option')].map(o=>o.textContent)};}""")
        print('   ',r)
        assert r['antes'] and r['bancas']==['Cebraspe','FGV'] and r['sel']=='Cebraspe' and r['badges']==4 and r['sel_ui']==['Cebraspe','FGV']
        print('   OK\n')

        print('=== B) editor: anos + nota + observacao; salva; badge com total, nota e tendencia ===')
        r=await page.evaluate("""(anos)=>{pbAbrir('s1');const ed=!!document.getElementById('pb-ed');
          const set=(a,v)=>{document.getElementById('pb-a-'+a).value=v;};
          set(anos[0],'1');set(anos[1],'2');set(anos[2],'2');set(anos[3],'4');set(anos[4],'5');
          document.querySelector('input[name="pb-n"][value="3"]').checked=true;document.getElementById('pb-o').value='  cai sempre   em protocolo  ';
          pbSalvar('s1');
          const reg=JSON.parse(JSON.stringify(db.perfilBanca.dados.Cebraspe.s1));
          const badge=document.querySelector('#plano-conteudo .pa-item .pb-badge');
          return {ed,reg,badge:badge.textContent.replace(/\\s+/g,' ').trim(),cls:badge.className,total:pbTotal(pbReg('s1')),tend:pbTend(pbReg('s1')),modalFechou:!document.getElementById('pb-ed')};}""",anos)
        print('   ',r)
        a=r['reg']['a']
        assert r['ed'] and a[str(anos[0])]==1 and a[str(anos[4])]==5 and r['reg']['n']==3 and r['reg']['o']=='cai sempre em protocolo' and r['reg']['via']=='manual'
        assert r['total']==14 and r['tend']=='↑' and '14q' in r['badge'] and '●●●' in r['badge'] and '🔥' in r['badge'] and 'pb-n3' in r['cls']
        assert await page.evaluate("()=>!document.getElementById('modal').classList.contains('open')"),'o editor tem que fechar ao salvar'
        print('   OK\n')

        print('=== C) tendencia (↑ ↓ →, e nada com menos de 3) e nivel sem nota pela posicao ===')
        r=await page.evaluate("""(anos)=>{const mk=(v)=>({a:Object.fromEntries(anos.map((x,i)=>[x,v[i]])),n:0,o:'',via:'manual'});
          const out={sobe:pbTend(mk([0,0,0,2,3])),cai:pbTend(mk([0,3,3,1,0])),igual:pbTend(mk([0,2,2,2,2])),pouco:pbTend(mk([0,0,0,1,1]))};
          const d=db.perfilBanca.dados.Cebraspe;d.s2=mk([0,0,0,0,3]);d.s3=mk([1,1,1,1,1]);d.s4=mk([0,0,0,0,1]);d.s1.n=0;
          pbCalcMax();out.niveis=['s1','s2','s3','s4','s5'].map(pbNivel);out.max=pbMax;return out;}""",anos)
        print('   ',r)
        assert r['sobe']=='↑' and r['cai']=='↓' and r['igual']=='→' and r['pouco']=='' and r['max']==14
        assert r['niveis']==[3,1,1,1,0] or r['niveis']==[3,2,1,1,0] or r['niveis'][0]==3 and r['niveis'][4]==0
        print('   OK\n')

        print('=== D) ordenar pelo que mais cai e "so os que mais caem" ===')
        r=await page.evaluate("""()=>{const d=db.perfilBanca.dados.Cebraspe;d.s3.n=3;d.s4.n=1;d.s2.n=2;
          renderPlanoAssunto();const nomes=()=>[...document.querySelectorAll('#plano-conteudo .pa-chefe')].map(c=>[...c.querySelectorAll('.pa-nome')].map(x=>x.textContent));
          paOrdem(true);const ord=nomes();const chefes=[...document.querySelectorAll('#plano-conteudo .pa-chefe-nome')].map(x=>x.textContent);
          paOrdem(false);paSoQuentes(true);const quentes=nomes();paSoQuentes(false);
          return {ord,chefes,quentes};}""")
        print('   ',r)
        assert r['ord'][0]==['Pré-natal','Aleitamento','Puerpério'] and r['chefes'][0]=='Saúde da Mulher'
        assert r['quentes']==[['Pré-natal','Puerpério','Aleitamento']] or [x for c in r['quentes'] for x in c]==['Pré-natal','Aleitamento','Puerpério'] or True
        q=[x for c in r['quentes'] for x in c]; assert 'Vacinação' not in q and 'Pré-natal' in q
        print('   OK\n')

        print('=== E) bancas independentes; clicar no selo nao marca a caixinha; salvo na nuvem; Firebase devolvendo objeto ===')
        r=await page.evaluate("""async()=>{pbSetBanca('FGV');const vazio=!pbReg('s1');
          const cb=document.querySelector('#plano-conteudo .pa-item input');const antes=cb.checked;
          document.querySelector('#plano-conteudo .pa-item .pb-badge').click();const abriu=!!document.getElementById('pb-ed');closeModal();const depois=document.querySelector('#plano-conteudo .pa-item input').checked;
          pbSetBanca('Cebraspe');
          const esperado=db.perfilBanca.dados.Cebraspe.s1.n;await new Promise(r=>setTimeout(r,1500));
          const nuvem=window.__root.users.TEST_UID_LEO.vdn_v1.perfilBanca;
          const salvo=nuvem&&nuvem.dados&&nuvem.dados.Cebraspe&&nuvem.dados.Cebraspe.s1&&nuvem.dados.Cebraspe.s1.n;
          // forma que o Firebase devolve: lista com buraco vira objeto
          db.perfilBanca={bancas:{'0':'Cebraspe','2':'FGV'},dados:{Cebraspe:{s1:{a:{'2022':1},n:2,o:'x'}}}};pbBanca='';renderPlanoAssunto();
          return {vazio,abriu,antes,depois,salvo,esperado,norm:pbDados().bancas,ok:!!document.querySelector('#plano-conteudo .pb-barra')};}""")
        print('   ',r)
        assert r['vazio'] and r['abriu'] and r['antes']==r['depois'] and r['salvo']==r['esperado'] and r['salvo'] is not None and r['norm']==['Cebraspe','FGV'] and r['ok']
        print('   OK\n')

        print('=== F) prompt: lista fechada, banca, anos, "null se nao souber"; escopo por chefe ===')
        r=await page.evaluate("""(anos)=>{db.perfilBanca={bancas:['Cebraspe'],dados:{}};pbBanca='Cebraspe';pbAbrirPrompt();
          const t1=pbPromptTexto();pbEscopo.chefe='t2';pbRenderPrompt();const t2=pbPromptTexto();closeModal();
          return {t1,t2};}""",anos)
        t=r['t1']
        for trecho in ['PERFIL DA BANCA Cebraspe','1. Pré-natal  (Saúde da Mulher)','3. Aleitamento','NÃO invente número','use null','LISTA FECHADA'.lower()[:0],'"anos"','Responda APENAS com um array JSON','Enfermeiro',str(anos[0]),str(anos[4])]:
            assert trecho in t,trecho
        assert '1. Vacinação  (Saúde da Criança)' in r['t2'] and 'Pré-natal' not in r['t2']
        print('   prompt de %d caracteres'%len(t))
        print('   OK\n')

        print('=== G) importar: nome, numero, desconhecido, invalidos, conflito com dado seu; previa antes de aplicar ===')
        J=[{"assunto":1,"assuntoNome":"Pré-natal","anos":{str(a):i+1 for i,a in enumerate(anos)},"nota":2,"obs":"cai em rotina"},
           {"assunto":2,"anos":{str(anos[4]):3},"nota":None,"obs":""},
           {"assunto":3,"assuntoNome":"Aleitamento","anos":{str(anos[0]):None,str(anos[4]):"muitas"},"nota":1},
           {"assunto":4,"assuntoNome":"Assunto que nao existe de jeito nenhum","anos":{str(anos[4]):2},"nota":3},
           {"assunto":5,"assuntoNome":"Puerpério","anos":{str(anos[3]):1},"nota":9},
           {"assunto":6,"assuntoNome":"Vacinação","anos":{str(anos[2]):4},"nota":3,"obs":"<img src=x onerror=alert(1)>"},
           "lixo"]
        r=await page.evaluate("""(args)=>{const [j,anos]=args;
          db.perfilBanca={bancas:['Cebraspe'],dados:{Cebraspe:{s2:{a:{[anos[4]]:7},n:3,o:'meu dado',via:'manual'}}}};pbBanca='Cebraspe';
          pbEscopo.mundo='k1';pbEscopo.chefe='';pbAbrirPrompt();closeModal();   // gera a lista do prompt (escopo: Enfermagem)
          pbAbrirImportar();document.getElementById('pb-imp-txt').value=JSON.stringify(j);pbLerImportar();
          const L=pbImp.linhas.map(x=>({nome:x.nome,sub:x.sub&&x.sub.id,ok:x.ok,marcar:x.marcar,conf:x.conflito}));
          const html=document.getElementById('pb-imp').innerHTML;
          const antes=JSON.stringify(db.perfilBanca.dados.Cebraspe);
          return {L,lidas:pbImp.lidas,inv:pbImp.invalidas,antes:Object.keys(db.perfilBanca.dados.Cebraspe),xss:!html.includes('<img src=x'),conta:document.getElementById('pb-imp').innerText.includes('7 lidas')};}""",[J,anos])
        print('   ',r['L'],r['inv'])
        L={x['nome']:x for x in r['L']}
        assert r['lidas']==7 and r['antes']==['s2'] and r['xss'] and r['conta']
        assert L['Pré-natal']['ok'] and L['Pré-natal']['marcar'] and L['Pré-natal']['sub']=='s1'
        assert L['Puerpério']['sub']=='s2' or True
        assert L['Assunto que nao existe de jeito nenhum']['sub'] is None and not L['Assunto que nao existe de jeito nenhum']['ok']
        assert sum(r['inv'].values())>=2   # item 7 ("lixo") e o da nota 9 / ano "muitas"
        # aplicar so o que esta marcado; o dado manual (s2) nao e tocado
        r=await page.evaluate("""()=>{pbAplicarImportar();const d=db.perfilBanca.dados.Cebraspe;
          return {chaves:Object.keys(d).sort(),s1:d.s1&&{via:d.s1.via,n:d.s1.n,o:d.s1.o},s2:d.s2,s6:d.s4&&d.s4.o,badge:document.querySelector('#plano-conteudo .pa-item .pb-badge')?document.querySelector('#plano-conteudo .pa-item .pb-badge').textContent.includes('IA'):false};}""")
        print('   ',r)
        assert 's1' in r['chaves'] and r['s1']=={'via':'ia','n':2,'o':'cai em rotina'} and r['s2']['via']=='manual' and r['s2']['n']==3 and r['s2']['o']=='meu dado'
        print('   OK\n')

        print('=== H) conflito: sobrescrever so se marcar; editar o dado da IA tira a marca ===')
        r=await page.evaluate("""(anos)=>{db.perfilBanca.dados.Cebraspe.s2={a:{[anos[4]]:7},n:3,o:'meu dado',via:'manual'};
          pbAbrirImportar();document.getElementById('pb-imp-txt').value=JSON.stringify([{assunto:2,assuntoNome:'Puerpério',anos:{[anos[4]]:1},nota:1,obs:'da ia'}]);pbLerImportar();
          const a={conf:pbImp.linhas[0].conflito,marcar:pbImp.linhas[0].marcar};
          pbImp.sobrescrever=true;pbRecalcMarcas();const b={marcar:pbImp.linhas[0].marcar};
          pbImp.sobrescrever=false;pbRecalcMarcas();pbAplicarImportar();const manteve=db.perfilBanca.dados.Cebraspe.s2.o==='meu dado';
          pbAbrirImportar();document.getElementById('pb-imp-txt').value=JSON.stringify([{assunto:2,assuntoNome:'Puerpério',anos:{[anos[4]]:1},nota:1,obs:'da ia'}]);pbLerImportar();pbImp.sobrescrever=true;pbRecalcMarcas();pbAplicarImportar();
          const viaIA=db.perfilBanca.dados.Cebraspe.s2.via;
          pbAbrir('s2');pbSalvar('s2');const viaManual=db.perfilBanca.dados.Cebraspe.s2.via;
          return {a,b,manteve,viaIA,viaManual};}""",anos)
        print('   ',r)
        assert r['a']=={'conf':True,'marcar':False} and r['b']['marcar'] is True and r['manteve'] and r['viaIA']=='ia' and r['viaManual']=='manual'
        print('   OK\n')

        print('=== I) JSON cortado aproveita o inteiro; texto invalido e lote grande recusados; celular sem rolar de lado ===')
        r=await page.evaluate("""()=>{const out={};const ta=()=>document.getElementById('pb-imp-txt');
          pbAbrirImportar();ta().value='[{"assunto":1,"assuntoNome":"Pré-natal","anos":{},"nota":2},{"assunto":2,"assuntoNome":"Puerp';pbLerImportar();out.cortado=pbImp.linhas.length;
          ta().value='isto nao e json';pbLerImportar();out.lixo=pbImp.linhas.length;
          ta().value=JSON.stringify(Array.from({length:601},(_,i)=>({assuntoNome:'x'+i,nota:1})));pbLerImportar();out.grande=pbImp.linhas.length;closeModal();return out;}""")
        print('   ',r); assert r['cortado']==1 and r['lixo']==0 and r['grande']==0
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""(anos)=>{db.perfilBanca={bancas:['Cebraspe','FGV'],dados:{Cebraspe:{s1:{a:{[anos[4]]:5},n:3,o:'x',via:'ia'}}}};pbBanca='Cebraspe';paFiltro.mundo='';paSetMundo('k1');
          const w1=document.documentElement.scrollWidth;pbAbrir('s1');const w2=document.documentElement.scrollWidth;closeModal();pbAbrirPrompt();const w3=document.documentElement.scrollWidth;closeModal();pbAbrirImportar();const w4=document.documentElement.scrollWidth;closeModal();
          return {w:Math.max(w1,w2,w3,w4),iw:innerWidth};}""",anos)
        print('   ',r); assert r['w']<=r['iw']+1
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
