# -*- coding: utf-8 -*-
# Etapas 3 a 5: assistente com previa, importar/exportar (JSON, CSV, .ics) e ajuste do dia.
import asyncio,sys,json
sys.path.insert(0,'tests/e2e'); sys.path.insert(0,'.')
from playwright.async_api import async_playwright
from test_aba_dicas import abrir, graves
from _agenda_fix import seed_agenda, ATIVAR_JS

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(b,seed_agenda(),viewport={'width':1300,'height':900})
        await page.evaluate("()=>{window.todayStr=()=>'2026-11-04';window.confirm=()=>true;db.cronograma={ativo:true,inicio:'2026-11-05',v:2,feitos:{},lidos:{},rodizio:true,horaInicio:'06:00'};showScreen('agenda');}")

        print('=== A) assistente: escolher edital, ver previa, ajustar, aplicar ===')
        await page.evaluate("()=>agAbrirAssistente()")
        n=await page.evaluate("()=>document.querySelectorAll('#ag-assist input[type=checkbox]').length")
        assert n>=2
        await page.evaluate("()=>{const c=document.querySelector('#ag-assist input[type=checkbox]');c.checked=true;c.dispatchEvent(new Event('change'));}")
        r=await page.evaluate("()=>({txt:document.getElementById('ag-assist').innerText,eds:agR.editalIds})")
        print('  ',r['eds'])
        assert r['eds']==['e1'] and 'Conferência dos editais' in r['txt'] and '10 assuntos = 9 na fila + 1 sem vínculo + 0 excluídos' in r['txt']
        assert 'Primeira semana' in r['txt'] and 'término previsto' in r['txt'] and 'sem vínculo com o Mapa' in r['txt']
        # nada gravado ainda
        g=await page.evaluate("()=>({ap:!!(db.agendaPlanos&&db.agendaPlanos.ativoId),ebserh:crPlano().total})")
        assert not g['ap'],'a previa nao pode gravar nada'
        await page.evaluate("()=>{agSetEd('e2',true);agSetPct('e1',70);agSetPct('e2',30);agSetCfg('horasDia','5');agUsarMeusTempos();agSetDia(6,false);}")
        r=await page.evaluate("()=>({t:document.getElementById('ag-assist').innerText,pesos:agR.pesos,dias:agR.config.diasSemana,h:agR.config.horasDia})")
        print('  ',r['pesos'],r['dias'],r['h'])
        assert r['pesos'].get('enfermagem')==60 and r['pesos'].get('sus')==60 and 5==r['h'] and 6 not in r['dias']
        # ajuste fino: mover um assunto e travar; desfazer
        await page.evaluate("()=>{const l=document.querySelector('.ag-fino input[type=date]');const id=agPrevia(agR).linhas[0].id;agMover(id,'2026-11-09');agTravar(id,true);window.__id=id;}")
        r=await page.evaluate("()=>({pin:agR.pins[window.__id],hist:agHist.length})")
        assert r['pin']=={'ds':'2026-11-09','travado':True}
        await page.evaluate("()=>agDesfazerRasc()")
        assert (await page.evaluate("()=>agR.pins[window.__id].travado"))is not True
        await page.evaluate("()=>agTravar(window.__id,true)")
        await page.evaluate("()=>agAplicar()")
        r=await page.evaluate("()=>{const a=db.agendaPlanos,pl=agAtivo(),st=crEstado(),p=crPlano();return {at:a.ativoId===pl.id,eds:pl.editalIds,v:a.versoes.length,pins:st.pins,h:p.horas,total:p.total,dom:p.calendario.find(d=>crDow(d.ds)===6&&d.t==='est'),blocos:Object.values(CRON_BLOCOS)};}")
        print('  ',{k:r[k] for k in ('eds','v','total','h','pins','blocos')})
        assert r['at'] and r['eds']==['e1','e2'] and r['v']==1 and r['h']==5 and r['dom'] is None and r['pins'][ (await page.evaluate("()=>window.__id")) ]['travado']
        r=await page.evaluate("()=>{agVoltar();return {at:db.agendaPlanos.ativoId,v:db.agendaPlanos.versoes.length,total:crPlano().total,blocos:Object.keys(CRON_BLOCOS)};}")
        assert r['at'] is None and r['v']==0 and r['total']>400 and r['blocos'][0]=='esp'
        print('   OK\n')

        print('=== B) exportar e importar JSON: ida e volta sem perda ===')
        await page.evaluate(ATIVAR_JS.replace('(args)=>','(args)=>')+"")  if False else None
        await page.evaluate("(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-04',inicio:'2026-11-05'});const st=crEstado();const p=crPlano();const id=p.agenda.fila[0];st.pins={[id]:{ds:p.calendario.filter(d=>d.t==='est'&&d.atual.length).slice(-1)[0].ds,travado:true}};st.bloqueios=[{data:'2026-11-07',inicio:'14:00',min:90,titulo:'Plantao'}];}",ATIVAR_JS)
        r=await page.evaluate("""()=>{const A=agExportarObj();const j=JSON.stringify(A);
          const st=crEstado();st.pins={};st.bloqueios=[];
          const lida=agLer(j);const res=agAnalisar(lida,false);
          const cont={ap:res.filter(r=>r.status==='aplicar').length,ig:res.filter(r=>r.status==='ignorar').length,am:res.filter(r=>r.status==='ambiguo').length};
          agImp={txt:j,modo:'substituir',sobrepor:false,lida,res,esc:{}};agImportarAplicar();
          const B=agExportarObj();
          return {fmt:A.formato,eds:A.editalIds,cfg:A.config,n:A.itens.length,cont,ok:JSON.stringify(A.itens)===JSON.stringify(B.itens),
            tipos:[...new Set(A.itens.map(i=>i.tipo))],trav:A.itens.filter(i=>i.travado).length,bq:A.itens.filter(i=>i.tipo==='bloqueio').length,total:res.length};}""")
        print('  ',r)
        assert r['fmt']=='vale-agenda-v1' and r['eds']==['e1','e2'] and r['ok'] and r['trav']==1 and r['bq']==1
        assert r['cont']['ap']+r['cont']['ig']+r['cont']['am']==r['total']

        print('=== C) CSV colado (nome ambiguo, invalido, passado, sobreposicao) ===')
        await page.evaluate("(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-04',inicio:'2026-11-05'});}",ATIVAR_JS)
        r=await page.evaluate("""()=>{
          const csv='data,inicio,min,tipo,edital,disciplina,assunto\\n'+[
            '2026-11-09,06:00,30,estudo,Edital A,Enfermagem,Enf 3',
            '2026-11-09,06:15,30,estudo,Edital A,Enfermagem,Enf 4',
            '2026-11-30,06:00,30,estudo,,,Enf 5',
            '2026-02-30,06:00,30,estudo,,,Enf 6',
            '2026-11-10,25:00,30,estudo,,,Enf 6',
            '2026-11-10,06:00,abc,estudo,,,Enf 6',
            '2026-11-03,06:00,30,estudo,,,Enf 1',
            '2026-11-10,06:00,30,estudo,,,Nada disso',
            '2026-11-10,07:00,60,bloqueio,,,Plantao',
            '2026-11-10,07:30,30,estudo,,,Enf 6',
            '2026-11-10,09:00,45,revisao,,,Revisoes',
            '2026-11-08,06:00,30,estudo,,,Enf 2'].join('\\n');
          const lida=agLer(csv),res=agAnalisar(lida,false);
          const q=res.map(r=>[r.it.linha,r.status,r.motivo.slice(0,22)]);
          const lida2=agLer(csv),res2=agAnalisar(lida2,true);
          return {fmt:lida.formato,q,sob:res2.filter(r=>r.sobreposto).length,n:res.length};}""")
        print('  ',r['q'])
        st={x[0]:x[1] for x in r['q']}
        assert r['fmt']=='csv' and st[2]=='aplicar' and st[3]=='ignorar' and st[4]=='aplicar'   # sobreposicao em 11-09 06:15
        assert st[5]=='ignorar' and st[6]=='ignorar' and st[7]=='ignorar' and st[8]=='ignorar' and st[9]=='ignorar'
        assert st[10]=='aplicar' and st[11]=='ignorar' and st[12]=='ignorar' and st[13]=='ignorar'
        # Enf 1 e Enf 2 existem em dois editais mas sao o MESMO assunto (um subId): nao e ambiguo
        print('   OK\n')

        print('=== D) ambiguo: dois assuntos do Mapa com o mesmo nome ===')
        r=await page.evaluate("""()=>{
          const t=db.topics.kB.find(x=>x.id==='_scn56um');
          // duas disciplinas do plano com assuntos de mesmo nome, ids diferentes
          const e=edFind('e2');e.disciplinas[1].assuntos[0].nome='Repetido';
          db.topics.kB.find(x=>x.id==='_scn56um').subtopics[0].name='Repetido';
          const outro=db.topics.kB.find(x=>x.id==='_cc3d9an').subtopics[0];outro.name='Repetido';
          e.disciplinas[1].assuntos.push({id:'sx',nome:'Repetido',subId:outro.id});
          const p=crPlano();
          const lida=agLer('data,inicio,min,tipo,edital,disciplina,assunto\\n2026-11-10,06:00,30,estudo,,,Repetido');
          const res=agAnalisar(lida,false);
          return {st:res[0].status,cand:res[0].cand.length};}""")
        print('  ',r)
        assert r['st']=='ambiguo' and r['cand']==2

        print('=== E) .ics: evento vira bloqueio (so futuros), recorrencia avisada, dia inteiro vira indisponivel ===')
        r=await page.evaluate("""()=>{
          const ics=['BEGIN:VCALENDAR','VERSION:2.0',
            'BEGIN:VEVENT','DTSTART:20261110T070000','DTEND:20261110T080000','SUMMARY:Plantao\\, noite','END:VEVENT',
            'BEGIN:VEVENT','DTSTART:20261001T070000','DTEND:20261001T080000','SUMMARY:Passado','END:VEVENT',
            'BEGIN:VEVENT','DTSTART;VALUE=DATE:20261106','SUMMARY:Viagem','END:VEVENT',
            'BEGIN:VEVENT','DTSTART:20261111T090000','DURATION:PT1H30M','RRULE:FREQ=WEEKLY','SUMMARY:Aula','END:VEVENT','END:VCALENDAR'].join('\\r\\n');
          const lida=agLer(ics);const res=agAnalisar(lida,false);
          agImp={txt:ics,modo:'somar',sobrepor:false,lida,res,esc:{}};
          const antes=crPlano().calendario.find(d=>d.ds==='2026-11-06').t;
          agImportarAplicar();const st=crEstado(),p=crPlano();
          return {fmt:lida.formato,n:lida.itens.length,erros:lida.erros.map(e=>e.motivo.slice(0,30)),st:res.map(r=>r.status),bq:st.bloqueios,indisp:st.indisp,
            d12:[antes,p.calendario.find(d=>d.ds==='2026-11-06').t],h10:p.horasEm('2026-11-10'),h11:p.horasEm('2026-11-11')};}""")
        print('  ',r)
        assert r['fmt']=='ics' and r['n']==4 and r['st']==['aplicar','ignorar','aplicar','aplicar']
        assert r['indisp']==['2026-11-06'] and r['d12'][0]=='est' and r['d12'][1]=='fer' and len(r['bq'])==2 and r['h10']<4 and r['erros']

        print('=== F) arquivo invalido, grande demais e HTML malicioso ===')
        r=await page.evaluate("""()=>{
          const a=agLer('{"formato":"outro"}'),b=agLer('{quebrado'),c=agLer('<script>alert(1)</script>'),d=agLer('');
          const x=agLer(JSON.stringify({formato:'vale-agenda-v1',itens:[{data:'2026-11-10',inicio:'06:00',min:30,tipo:'bloqueio',assunto:'<img src=x onerror=alert(1)>'}]}));
          agImp={txt:'',modo:'somar',sobrepor:false,lida:x,res:agAnalisar(x,false),esc:{}};
          openModal('t','<div id="ag-imp"></div>');agImpRender();
          return {a:a.erros[0].motivo,b:b.erros[0].motivo,c:c.erros[0].motivo,d:d.erros[0].motivo,html:document.getElementById('ag-imp').innerHTML.includes('<img src=x')};}""")
        print('  ',r)
        assert 'formato' in r['a'] and 'inválido' in r['b'] and 'cabeçalho' in r['c'] and not r['html']

        print('=== G) exportar CSV e .ics validos; prompt para IA externa ===')
        await page.evaluate("(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-04',inicio:'2026-11-05'});}",ATIVAR_JS)
        r=await page.evaluate("""()=>{const csv=agExportarCSV(),ics=agExportarICS(),pr=agPromptIA();
          const L=csv.trim().split('\\r\\n');
          return {cab:L[0],n:L.length,ics:[ics.startsWith('BEGIN:VCALENDAR'),(ics.match(/BEGIN:VEVENT/g)||[]).length===(ics.match(/END:VEVENT/g)||[]).length,ics.includes('DTSTART:2026')],
            prompt:{formato:pr.includes('vale-agenda-v1'),sub:pr.includes('"subId": "s_loi52dk_1"'),sem:pr.includes('"subId": null'),q:pr.includes('"questoes": 30'),disp:pr.includes('Horas de estudo por dia'),
              pessoal:/XP|nivel|Leo/i.test(pr),amanha:pr.includes('2026-11-05')}};}""")
        print('  ',r)
        assert r['cab']=='data,inicio,min,tipo,edital,disciplina,assunto' and r['n']>10 and all(r['ics'])
        assert r['prompt']['formato'] and r['prompt']['sub'] and r['prompt']['sem'] and r['prompt']['q'] and r['prompt']['disp'] and not r['prompt']['pessoal']

        print('=== H) ajuste do dia: so X horas, nao vou estudar, trocar, adiantar — sem atraso falso ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-05',inicio:'2026-11-05'});
          const st=crEstado();let p=crPlano();const fim0=p.fimAtual,atr0=p.atrasados.length,n0=p.hojeAtual.length;
          agHojeHoras(1.5);p=crPlano();const a={n:p.hojeAtual.length,atr:p.atrasados.length,fim:p.fimAtual};
          agDesfazerAjusteHoje();p=crPlano();const b={n:p.hojeAtual.length,fim:p.fimAtual};
          agHojeHoras(0);p=crPlano();const c={n:p.hojeAtual.length,atr:p.atrasados.length,fim:p.fimAtual};
          agDesfazerAjusteHoje();
          const bloco=Object.keys(CRON_BLOCOS).find(k=>CRON_BLOCOS[k]==='SUS');
          agTrocarHoje(bloco);p=crPlano();const d={sus:p.hojeAtual.some(id=>p.meta.get(id).bloco===bloco),atr:p.atrasados.length};
          agDesfazerAjusteHoje();const n1=crPlano().hojeAtual.length;
          const h0=crPlano().hojeAtual.slice();agAdiantar();p=crPlano();const e={n:p.hojeAtual.length,atr:p.atrasados.length,novo:p.hojeAtual.filter(id=>!h0.includes(id)).length,pin:Object.keys(crEstado().pins||{}).length};
          agDesfazerAjusteHoje();
          return {fim0,atr0,n0,a,b,c,d,e,n1,fases:st.fases};}""",ATIVAR_JS)
        print('  ',r)
        assert r['a']['n']<r['n0'] and r['a']['atr']==r['atr0'] and r['b']['n']==r['n0'] and r['b']['fim']==r['fim0']
        assert r['c']['n']==0 and r['c']['atr']==r['atr0'] and r['c']['fim']>=r['fim0']
        assert r['d']['sus'] and r['d']['atr']==r['atr0'] and r['e']['novo']==1 and r['e']['pin']==1 and r['e']['atr']==r['atr0'] and r['n1']==r['n0']

        print('=== I) revisoes e simulado de domingo nao somem com o ajuste ===')
        r=await page.evaluate("""()=>{const p=crPlano();const dom=p.calendario.find(d=>d.t==='rev'&&d.ds>p.hoje);
          const antes=crBlocosDoDia(dom,p).map(b=>b.titulo);
          agHojeHoras(0);const p2=crPlano();const dom2=p2.calendario.find(d=>d.ds===dom.ds);const depois=crBlocosDoDia(dom2,p2).map(b=>b.titulo);
          agDesfazerAjusteHoje();return {antes,depois};}""")
        print('  ',r)
        assert r['antes']==r['depois'] and 'Simulado de 30' in r['antes']

        print('=== J) celular: assistente e importacao nao rolam de lado ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{agR=agRascunhoInicial();agR.editalIds=['e1','e2'];agHist=[];openModal('t','<div class="cron-modal ag-modal"><div id="ag-assist">'+agAssistInner()+'</div></div>');
          const w1=document.documentElement.scrollWidth;closeModal();agImportarAbrir();const w2=document.documentElement.scrollWidth;closeModal();agAbrirAjusteDia();const w3=document.documentElement.scrollWidth;
          return {w1,w2,w3,iw:innerWidth};}""")
        print('  ',r)
        assert max(r['w1'],r['w2'],r['w3'])<=r['iw']+1
        await page.screenshot(path='/tmp/claude-0/-home-user-valedosnomeados/971e8aeb-d183-53be-8eb3-e4c255841f26/scratchpad/ajuste.png')
        print('erros de JS:',graves(errs) or 'nenhum'); assert not graves(errs)
        print('OK')
asyncio.run(main())
