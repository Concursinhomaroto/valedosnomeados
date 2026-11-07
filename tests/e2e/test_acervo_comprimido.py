# -*- coding: utf-8 -*-
# Banco comprimido (vdn_acervoz) e carregamento adiado: ida e volta sem perda, migracao do no antigo (que fica intacto),
# versao igual nao baixa, pacote quebrado volta pro no antigo, e nada grava antes do banco carregar.
import asyncio, sys, json
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from test_treino_filtros import seed, ACERVO

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{window.confirm=()=>true;return true;}")

        print('=== A) comprimir e abrir: igual ao original, bem menor, em pedacos ===')
        r=await page.evaluate("""async()=>{
          const lista=sanitizeForFirebase(db.acervo);
          // um banco grande de verdade: 8.000 questoes com acento, aspas e emoji
          const grande=[];for(let i=0;i<8000;i++)grande.push({questao:'Questão "'+i+'" sobre assistência — 💉 paciente de 62 anos, conduta correta segundo o protocolo vigente.',explicacao:'Explicação longa número '+i+' com acentuação: ção, ã, é, ô. '.repeat(6),correta:'C',subId:'s'+(i%40),formato:'certoerrado',tags:[],_chaveForte:'k'+i,vezesRespondida:i%5});
          const t0=performance.now();const pk=await acervoEmpacotar(grande);const t1=performance.now();const volta=await acervoDesempacotar(pk);const t2=performance.now();
          const bytesZ=pk.parts.join('').length;
          return {igual:JSON.stringify(volta)===JSON.stringify(grande),chars:pk.chars,bytesZ,razao:Math.round(pk.chars/bytesZ*10)/10,partes:pk.parts.length,n:pk.n,msComp:Math.round(t1-t0),msDesc:Math.round(t2-t1),
            pequeno:JSON.stringify(await acervoDesempacotar(await acervoEmpacotar(lista)))===JSON.stringify(lista)};}""")
        print('   ',r)
        assert r['igual'] and r['pequeno'] and r['razao']>=4 and r['partes']>=1 and r['n']==8000
        print('   OK\n')

        print('=== B) gravar: vai o pacote comprimido (no novo), o no antigo nao e tocado, copia local tambem ===')
        r=await page.evaluate("""async()=>{
          window.__root.users.TEST_UID_LEO.vdn_acervo=[{questao:'ANTIGA no no velho',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],correta:'C'}];
          const antes=JSON.stringify(window.__root.users.TEST_UID_LEO.vdn_acervo);
          window.__updateCalls=[];
          ACERVO_PRONTO=true;acervoSalvar(true);await acervoAguardar();
          const z=window.__root.users.TEST_UID_LEO.vdn_acervoz;
          const chamadas=window.__updateCalls.filter(c=>/vdn_acervo/.test(c.path)).map(c=>c.path.replace('users/TEST_UID_LEO/',''));
          const local=await idbLer(acervoChaveCache()+'z');
          const lista=await acervoDesempacotar(z);
          return {antigoIntacto:JSON.stringify(window.__root.users.TEST_UID_LEO.vdn_acervo)===antes,chamadas,n:z&&z.n,igual:JSON.stringify(lista)===JSON.stringify(sanitizeForFirebase(db.acervo)),localTs:local&&local.ts===z.ts,tipo:z&&z.z};}""")
        print('   ',r)
        assert r['antigoIntacto'] and r['chamadas']==['vdn_acervoz'] and r['igual'] and r['localTs'] and r['tipo']=='gzip64' and r['n']==16
        print('   OK\n')

        print('=== C) recarregar: versao igual nao baixa; nuvem mudou -> baixa e atualiza a copia local ===')
        r=await page.evaluate("""async()=>{
          const z=window.__root.users.TEST_UID_LEO.vdn_acervoz;
          const n0=db.acervo.length;
          // 1) copia local igual a nuvem: nao pode ler o no inteiro
          let leituras=0;const refOrig=ACERVO_REF_Z;
          const once0=firebase.database().ref('x').once;
          const r1=await acervoCarregarZ();
          const ref=ACERVO_REF_Z;let baixou=false;const o=ref.once.bind(ref);ref.once=(...a)=>{baixou=true;return o(...a);};
          const r2=await acervoCarregarZ();
          const semBaixar=!baixou&&r2.via==='local'&&r2.lista.length===n0;
          // 2) outro aparelho gravou: o carimbo mudou
          const nova=sanitizeForFirebase(db.acervo).concat([{questao:'veio de outro aparelho '+Date.now(),alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],correta:'C',formato:'certoerrado',_chaveForte:'outro1'}]);
          window.__root.users.TEST_UID_LEO.vdn_acervoz=await acervoEmpacotar(nova);
          const r3=await acervoCarregarZ();
          const ts=(await idbLer(acervoChaveCache()+'z')).ts;
          return {semBaixar,via3:r3.via,n3:r3.lista.length,tsAtualizado:ts===window.__root.users.TEST_UID_LEO.vdn_acervoz.ts};}""")
        print('   ',r)
        assert r['semBaixar'] and r['via3']=='nuvem' and r['n3']==17 and r['tsAtualizado']
        print('   OK\n')

        print('=== D) migracao: so existe o no antigo -> carrega dele, cria o pacote e deixa o antigo intacto ===')
        r=await page.evaluate("""async()=>{
          const root=window.__root.users.TEST_UID_LEO;
          const antigo=sanitizeForFirebase(db.acervo).slice(0,10);
          root.vdn_acervo=antigo;delete root.vdn_acervoz;root.vdn_acervo_ver=null;
          try{await idbGravar(acervoChaveCache()+'z',null);}catch(e){}
          try{await idbGravar(acervoChaveCache(),antigo);}catch(e){}
          db.acervo=[];ACERVO_PRONTO=false;acervoCarga=null;
          const n=await acervoCarregarJa();await acervoAguardar();
          const z=root.vdn_acervoz;
          return {n,db:db.acervo.length,pronto:ACERVO_PRONTO,pacote:z&&z.n,antigoIntacto:root.vdn_acervo.length===10};}""")
        print('   ',r)
        assert r['db']==10 and r['pronto'] and r['pacote']==10 and r['antigoIntacto']
        print('   OK\n')

        print('=== E) pacote quebrado ou com contagem errada: volta para o no antigo, sem perder nada ===')
        r=await page.evaluate("""async()=>{
          const root=window.__root.users.TEST_UID_LEO;
          const base=sanitizeForFirebase(db.acervo);
          root.vdn_acervo=base;                       // antigo completo
          const ruim=await acervoEmpacotar(base);ruim.n=999;root.vdn_acervoz=ruim;   // contagem nao bate
          try{await idbGravar(acervoChaveCache()+'z',null);}catch(e){}
          try{await idbGravar(acervoChaveCache(),base);}catch(e){}
          db.acervo=[];ACERVO_PRONTO=false;acervoCarga=null;
          await acervoCarregarJa();await acervoAguardar();
          const a=db.acervo.length;
          root.vdn_acervoz={v:1,ts:1,n:3,z:'gzip64',parts:['isto-nao-e-gzip']};
          try{await idbGravar(acervoChaveCache()+'z',null);}catch(e){}
          db.acervo=[];ACERVO_PRONTO=false;acervoCarga=null;
          await acervoCarregarJa();await acervoAguardar();
          return {a,b:db.acervo.length,esperado:base.length,consertou:(await acervoDesempacotar(root.vdn_acervoz)||[]).length};}""")
        print('   ',r)
        assert r['a']==r['esperado'] and r['b']==r['esperado'] and r['consertou']==r['esperado']
        print('   OK\n')

        print('=== F) nada grava antes do banco carregar; o que foi marcado grava depois, com tudo junto ===')
        r=await page.evaluate("""async()=>{
          const root=window.__root.users.TEST_UID_LEO;const base=sanitizeForFirebase(db.acervo);
          root.vdn_acervoz=await acervoEmpacotar(base);root.vdn_acervo=base;
          try{await idbGravar(acervoChaveCache()+'z',null);}catch(e){}
          db.acervo=[{questao:'nova antes do carregamento',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],correta:'C',formato:'certoerrado',_chaveForte:'nova-antes',subId:'s1'}];
          ACERVO_PRONTO=false;acervoCarga=null;window.__updateCalls=[];
          acervoSalvar(true);await acervoAguardar();
          const antes=window.__updateCalls.filter(c=>/vdn_acervo/.test(c.path)).length;
          await acervoCarregarJa();await acervoAguardar();
          const z=await acervoDesempacotar(root.vdn_acervoz);
          return {antes,db:db.acervo.length,nuvem:z.length,tem:z.some(q=>q._chaveForte==='nova-antes'),esperado:base.length+1};}""")
        print('   ',r)
        assert r['antes']==0 and r['db']==r['esperado'] and r['nuvem']==r['esperado'] and r['tem']
        print('   OK\n')

        print('=== G) abrir uma tela que depende do banco antes dele carregar: espera carregar e abre ===')
        r=await page.evaluate("""async()=>{
          ACERVO_PRONTO=false;acervoCarga=null;
          showScreen('simgeral');
          const logo=document.getElementById('screen-simgeral').classList.contains('active');
          await acervoCarregarJa();await new Promise(r=>setTimeout(r,300));
          return {logo,depois:document.getElementById('screen-simgeral').classList.contains('active'),pronto:ACERVO_PRONTO};}""")
        print('   ',r); assert r['logo'] is False and r['depois'] and r['pronto']
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
