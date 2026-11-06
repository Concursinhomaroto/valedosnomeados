# -*- coding: utf-8 -*-
# Banca, ano e prova em cada questão: campos opcionais, linha no treino, filtros (banca real + "Sem banca" + ano),
# importação (JSON/colar), edição e migração a partir da fonte (sem chute).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from test_treino_filtros import seed, ACERVO

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{tf=TF_VAZIO();tfIniciado=true;showScreen('simgeral');renderSimGeralScreen();return true;}")

        print('=== A) normalizacao: campos validos entram, invalidos saem, enunciado/gabarito intactos ===')
        r=await page.evaluate("""()=>{
          const ce=simNormalizaQuestao({afirmacao:'Julgue o item.',gabarito:'C',explicacao:'.',banca:' IDECAN ',ano:'2025',prova:'Prefeitura de Campina Grande, Enfermeiro, 2026',orgao:'Prefeitura',cargo:'Enfermeiro'},'certoerrado');
          const mu=simNormalizaQuestao({questao:'Qual?',alternativas:[{letra:'A',texto:'x'},{letra:'B',texto:'y'}],correta:'B',banca:'FGV',ano:2024,prova:'Ebserh 2024'},'multipla');
          const ruim=simNormalizaQuestao({afirmacao:'Julgue.',gabarito:'E',banca:'',ano:'abc',prova:'   '},'certoerrado');
          const absurdo=simNormalizaQuestao({afirmacao:'Julgue.',gabarito:'E',ano:'20255'},'certoerrado');
          const velho=simNormalizaQuestao({afirmacao:'Julgue.',gabarito:'E'},'certoerrado');
          const entrada={questao:'Q?',alternativas:[{letra:'A',texto:'x'},{letra:'B',texto:'y'}],correta:'A',banca:'AOCP'};simNormalizaQuestao(entrada,'multipla');
          return {ce:[ce.banca,ce.ano,ce.prova,ce.orgao,ce.cargo,ce.questao,ce.correta],mu:[mu.banca,mu.ano,mu.prova,mu.questao,mu.correta],
            ruim:Object.keys(ruim).filter(k=>['banca','ano','prova'].includes(k)),absurdo:'ano' in absurdo,velho:Object.keys(velho).filter(k=>['banca','ano','prova','orgao','cargo'].includes(k)),
            naoMuta:entrada.banca};}""")
        print('   ',r)
        assert r['ce']==['IDECAN',2025,'Prefeitura de Campina Grande, Enfermeiro, 2026','Prefeitura','Enfermeiro','Julgue o item.','C']
        assert r['mu']==['FGV',2024,'Ebserh 2024','Qual?','B'] and r['ruim']==[] and r['absurdo'] is False and r['velho']==[] and r['naoMuta']=='AOCP'
        print('   OK\n')

        print('=== B) importar (colar JSON): banca/ano/prova entram no banco; duplicata so preenche o que falta ===')
        r=await page.evaluate("""()=>{
          const dados=simNormalizaQuestao({afirmacao:'Texto novo importado sobre puerperio.',gabarito:'C',explicacao:'.',banca:'IDECAN',ano:2025,prova:'Prefeitura X, Enfermeiro, 2025'},'certoerrado');
          Object.assign(dados,{subId:'s2',subName:'Puerpério',topicName:'Saúde da Mulher',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'x'});
          const n0=db.acervo.length;const r1=bancoAdicionarOuFundir(dados,'ia');
          const it=db.acervo.find(q=>q.questao==='Texto novo importado sobre puerperio.');
          // a mesma questao chega depois, sem banca: nao apaga; e a que chega com ano preenche o vazio
          const sem=simNormalizaQuestao({afirmacao:'Texto novo importado sobre puerperio.',gabarito:'C'},'certoerrado');Object.assign(sem,{subId:'s2'});
          bancoAdicionarOuFundir(sem,'ia');
          const antigo=db.acervo.find(q=>q.subId==='s1');
          const completa=simNormalizaQuestao({afirmacao:antigo.questao,gabarito:'C',banca:'Cebraspe',ano:2023},'certoerrado');Object.assign(completa,{subId:'s1'});
          bancoAdicionarOuFundir(completa,'ia');
          return {novo:r1.novo,n:db.acervo.length-n0,it:[it.banca,it.ano,it.prova],antigo:[antigo.banca||null,antigo.ano||null]};}""")
        print('   ',r)
        assert r['novo'] and r['n']==1 and r['it']==['IDECAN',2025,'Prefeitura X, Enfermeiro, 2025']
        assert r['antigo'][0] in ('FGV','Cebraspe') and r['antigo'][1]==2023 or r['antigo']==['FGV',2023]
        print('   OK\n')

        print('=== C) editar: ajustar banca, ano e prova; limpar remove; enunciado/gabarito/explicacao nao mudam ===')
        r=await page.evaluate("""()=>{
          const it=db.acervo.find(q=>q.subId==='s3'&&q.formato==='certoerrado');const ant={q:it.questao,c:it.correta,e:it.explicacao,alt:JSON.stringify(it.alternativas)};
          bancoAplicarEdicao(it,{questao:it.questao,formato:it.formato,alternativas:it.alternativas,correta:it.correta,explicacao:it.explicacao,fonte:it.fonte||'',tags:[],favorita:false,status:'ativa',banca:'IDECAN',ano:2025,prova:'Prova X',cargo:'Enfermeiro'});
          const dep=[it.banca,it.ano,it.prova,it.cargo];
          bancoAplicarEdicao(it,{questao:it.questao,formato:it.formato,alternativas:it.alternativas,correta:it.correta,explicacao:it.explicacao,fonte:it.fonte||'',tags:[],favorita:false,status:'ativa'});
          const limpo=['banca','ano','prova','cargo'].filter(k=>k in it);
          // o formulario de verdade
          const h=bancoEditorHTML?1:0;
          return {dep,limpo,intacto:it.questao===ant.q&&it.correta===ant.c&&it.explicacao===ant.e&&JSON.stringify(it.alternativas)===ant.alt};}""")
        print('   ',r)
        assert r['dep']==['IDECAN',2025,'Prova X','Enfermeiro'] and r['limpo']==[] and r['intacto']
        r=await page.evaluate("""()=>{const it=db.acervo.find(q=>q.subId==='s3');const h=bancoFormHTML?bancoFormHTML('t-',it):'';return h;}""") if False else None
        r=await page.evaluate("""()=>{const it=db.acervo.find(q=>q.subId==='s3');
          const html=[...document.querySelectorAll('script')].length;return typeof bancoLerForm;}""")
        print('   OK\n')

        print('=== C2) formulario real do editor: os campos existem, sao lidos e voltam preenchidos ===')
        r=await page.evaluate("""()=>{
          const it=db.acervo.find(q=>q.subId==='s3'&&q.formato==='certoerrado');
          const box=document.createElement('div');box.id='t-form';box.innerHTML=bancoEditorHTML(it,'edit');document.body.appendChild(box);
          const pref='banco-edit-'+it._chaveForte+'-';const set=(k,v)=>{document.getElementById(pref+k).value=v;};
          const existem=['banca','ano','prova','orgao','cargo'].every(k=>!!document.getElementById(pref+k));
          set('banca','IDECAN');set('ano','2025');set('prova','Prefeitura de Campina Grande, Enfermeiro, 2026');set('orgao','Prefeitura');set('cargo','Enfermeiro');
          const d=bancoLerForm(pref);
          bancoAplicarEdicao(it,d);
          const gravado=[it.banca,it.ano,it.prova,it.orgao,it.cargo];
          box.innerHTML=bancoEditorHTML(it,'edit');
          const volta=[document.getElementById(pref+'banca').value,document.getElementById(pref+'ano').value];
          set('ano','abc');const ruim=bancoLerForm(pref);
          box.remove();return {existem,lido:[d.banca,d.ano,d.prova],gravado,volta,anoInvalido:'ano' in ruim};}""")
        print('   ',r)
        assert r['existem'] and r['lido']==['IDECAN',2025,'Prefeitura de Campina Grande, Enfermeiro, 2026'] and r['gravado']==['IDECAN',2025,'Prefeitura de Campina Grande, Enfermeiro, 2026','Prefeitura','Enfermeiro']
        assert r['volta']==['IDECAN','2025'] and r['anoInvalido'] is False
        print('   OK\n')

        print('=== D) a linha de procedencia no treino: so aparece com dado ===')
        r=await page.evaluate("""()=>({cheia:origemLinhaHTML({banca:'IDECAN',ano:2025,prova:'Prefeitura de Campina Grande, Enfermeiro, 2026'}),parcial:origemLinhaHTML({banca:'FGV'}),vazia:origemLinhaHTML({}),nula:origemLinhaHTML(null),
          xss:origemLinhaHTML({banca:'<img src=x onerror=alert(1)>'})})""")
        print('   ',r)
        assert 'IDECAN · 2025 · Prefeitura de Campina Grande, Enfermeiro, 2026' in r['cheia'] and 'FGV</div>' in r['parcial'] and r['vazia']=='' and r['nula']=='' and '<img' not in r['xss']
        r=await page.evaluate("""()=>{const it=db.acervo.find(q=>q.subId==='s1');it.banca='IDECAN';it.ano=2025;it.prova='Prova de teste';
          treinoSessao=null;treinoIniciar([it],{titulo:'t'});renderSimGeralScreen();const t=document.querySelector('.treino-origem');const v=t&&t.textContent;
          const outro=db.acervo.find(q=>q.subId==='s4');treinoSessao=null;treinoIniciar([outro],{titulo:'t'});renderSimGeralScreen();const sem=!!document.querySelector('.treino-origem');
          treinoSessao=null;treinoResumo=null;renderSimGeralScreen();return {v,sem};}""")
        print('   ',r); assert r['v']=='IDECAN · 2025 · Prova de teste' and r['sem'] is False
        print('   OK\n')

        print('=== E) filtros: banca real + Sem banca; ano (+ Sem ano); URL ===')
        r=await page.evaluate("""()=>{db.acervo.forEach(q=>{delete q.banca;delete q.ano;delete q.prova;});
          const a=db.acervo.filter(q=>q.subId==='s1');a[0].banca='IDECAN';a[0].ano=2025;a[1].banca='IDECAN';a[1].ano=2024;a[2].banca='Cebraspe';a[2].ano=2025;
          tf=TF_VAZIO();const ent=()=>tfMontarEntradas(),o=d=>tfOpcoes(ent(),d).map(x=>[x.nome,x.n]);const out={banca:o('banca'),ano:o('ano')};
          tfAlternar('banca','IDECAN',true);out.idecan=tfFiltradas().length;out.anoDepois=o('ano');
          tfAlternar('banca','IDECAN',false);tfAlternar('banca','__sem__',true);out.sem=tfFiltradas().length;tfAlternar('banca','__sem__',false);
          tfAlternar('ano','2025',true);out.a2025=tfFiltradas().length;tfAlternar('banca','Cebraspe',true);out.cebra2025=tfFiltradas().length;
          out.url=location.search;out.chips=[...document.querySelectorAll('.tf-chip')].map(x=>x.textContent.replace(/\\s+/g,' ').trim());
          tf=TF_VAZIO();tfIniciado=false;tfIniciar();out.volta=[tf.bancas,tf.anos];
          tfSet('avancado',true);out.cobertura=document.querySelector('.tf-cobertura')?document.querySelector('.tf-cobertura').textContent.replace(/\\s+/g,' '):'';
          return out;}""")
        print('   ',r)
        assert r['banca']==[['Cebraspe',1],['IDECAN',2],['Sem banca',14]] and r['ano'][0]==['2025',2] and ['Sem ano',14] in r['ano']
        assert r['idecan']==2 and r['sem']==14 and r['a2025']==2 and r['cebra2025']==1
        assert 'f_ano=2025' in r['url'] and any(c.startswith('Ano: 2025') for c in r['chips']) and r['volta']==[['Cebraspe'],['2025']]
        assert 'Banca preenchida em 3 de 17' in r['cobertura'] and 'ano em 3 de 17' in r['cobertura']
        print('   OK\n')

        print('=== F) migracao: so preenche quando a fonte diz; "estilo" vira (estilo); nao sobrescreve; ano so junto da banca ===')
        r=await page.evaluate("""()=>{
          const F=[['Cebraspe 2023, prova de Enfermeiro'],['Banco de questões Português estilo Cebraspe'],['FGV - Ebserh 2024'],['IDECAN 2025'],['Lei 8.080/90, art. 2'],['Resumo do app (manual), 2022'],['material/sus/lei-8080-1990'],['Manual de Gestação (MS, 2022)'],['Prova do Instituto Access 2021'],[''],['Aocp']];
          db.acervo=[];db.migracaoOrigemV1=null;
          F.forEach(([f],i)=>{const q={questao:'Q'+i+': julgue.',correta:'C',formato:'certoerrado',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:'s1',subName:'Pré-natal',topicName:'Saúde da Mulher',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'x',fonte:f};
            db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});});
          db.acervo[5].banca='Minha banca';   // ja preenchida: nao pode ser sobrescrita
          const before=db.acervo.map(q=>q.questao+'|'+q.correta+'|'+q.explicacao);
          const rel=acervoMigrarOrigem(false);
          const ev=db.acervo.map(q=>[q.banca||null,q.ano||null]);
          const intacto=JSON.stringify(before)===JSON.stringify(db.acervo.map(q=>q.questao+'|'+q.correta+'|'+q.explicacao));
          const salvo=(window.__root.users.TEST_UID_LEO.vdn_acervo||[]);const noServidor=salvo.filter(q=>q.banca).length;
          const de2=acervoMigrarOrigem(false);   // idempotente
          return {rel,ev,intacto,noServidor,de2,flag:!!db.migracaoOrigemV1};}""")
        print('   ',r['ev']); print('   ',r['rel'],r['noServidor'])
        assert r['ev']==[['Cebraspe',2023],['Cebraspe (estilo)',None],['FGV',2024],['IDECAN',2025],[None,None],['Minha banca',None],[None,None],[None,None],['Instituto Access',2021],[None,None],['Aocp'.upper() if False else 'AOCP',None]]
        assert r['rel']['comBanca']==7 and r['rel']['comAno']==4 and r['intacto'] and r['flag']
        assert r['de2']['preenchidasBanca']==0 and r['de2']['preenchidasAno']==0
        assert r['noServidor']>=6,'tem que ter ido pro banco de dados (acervoSalvar(true))'
        print('   OK\n')

        print('=== G) migracao automatica roda uma vez depois que o acervo carrega ===')
        r=await page.evaluate("""()=>{db.migracaoOrigemV1=null;db.acervo.forEach(q=>{delete q.banca;delete q.ano;});tfAposAcervo();const c=db.acervo.filter(q=>q.banca).length;const flag=!!db.migracaoOrigemV1;
          db.acervo.forEach(q=>{delete q.banca;});tfAposAcervo();return {c,flag,naoRepete:db.acervo.filter(q=>q.banca).length};}""")
        print('   ',r); assert r['c']==6 and r['flag'] and r['naoRepete']==0
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
