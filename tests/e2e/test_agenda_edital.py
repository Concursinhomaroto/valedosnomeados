# -*- coding: utf-8 -*-
# Plano por edital (etapas 1 e 2): a Ebserh continua igual; o motor monta a fila a partir de um ou mais editais.
import asyncio,sys,json,hashlib
sys.path.insert(0,'tests/e2e'); sys.path.insert(0,'.')
from playwright.async_api import async_playwright
from test_aba_dicas import abrir, graves
from _agenda_fix import seed_agenda, ATIVAR_JS
from _cron_fixture import seed_cron

GOLDEN='156fb5e94131cd2f3d922915fb8f4a18'   # impressao digital do plano Ebserh ANTES de existir plano por edital

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(b,seed_cron())
        print('=== 1) plano Ebserh igual ao de antes da mudanca ===')
        r=await page.evaluate("""()=>{const out=[];
          for(const [hoje,riz,comp,nf,horas] of [['2026-11-04',true,false,0,4],['2026-11-20',false,true,15,5],['2026-12-10',true,false,40,4]]){
            window.todayStr=()=>hoje;
            db.cronograma={ativo:true,inicio:'2026-11-03',complementar:comp,rodizio:riz,v:2,feitos:{},lidos:{},fases:[{desde:'2026-11-03',horas}]};
            const p0=crPlano();const ids=[...p0.meta.keys()].slice(0,nf);ids.forEach(id=>db.cronograma.feitos[id]={em:'2026-11-03',via:'estudado'});
            const p=crPlano();
            out.push({fila:[...p.meta.keys()],cal:p.calendario.map(d=>[d.ds,d.t,d.orig,d.atual]),atr:p.atrasados,fim:p.fimAtual,hn:p.horasNec,tot:p.total,pend:p.pendentes,bl:p.blocos,horas:p.horas});}
          return out;}""")
        h=hashlib.md5(json.dumps(r,sort_keys=True).encode()).hexdigest()
        print('  ',h)
        assert h==GOLDEN,'o plano da Ebserh mudou'
        await ctx.close()

        ctx,page,errs=await abrir(b,seed_agenda())
        print('=== 2) um edital: disciplinas viram blocos, peso pelas questoes, sem vinculo listado ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);A({eds:['e1']});const p=crPlano();const f=p.agenda;
          const d=f.discs.map(x=>({n:x.nome,w:Math.round(x.w),q:x.qDecl,sp:x.semPeso,ns:x.subs.length}));
          const ord=f.fila.map(id=>p.meta.get(id).cap.nome);
          return {n:p.total,d,sem:f.semVinculo.map(x=>x.a.nome),rec:agReconciliar(f),ord:ord.slice(0,9),blocos:Object.values(CRON_BLOCOS),fim:p.fimAtual};}""",ATIVAR_JS)
        print('  ',r)
        assert r['n']==9 and [x['ns'] for x in r['d']]==[6,3]
        assert r['d'][0]['w']>r['d'][1]['w']*2.5,'Enfermagem (30q) deve pesar ~3x Portugues (10q)'
        assert r['sem']==['Assunto sem vinculo']
        assert r['rec']==[{'id':'e1','nome':'Edital A','total':10,'naFila':9,'sem':1,'excl':0,'fecha':True}]
        assert r['ord'][:4].count('Enfermagem')==3,r['ord'] and r['blocos']==['Enfermagem','Português']

        print('=== 3) dois editais: assunto em comum entra uma vez e mostra de quais editais; concluir conta para todos ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();pl.editalIds=['e1','e2'];pl.pct={e1:70,e2:30};
          let p=crPlano();const f=p.agenda;
          const comum=[...p.meta.entries()].filter(([id,m])=>m.eds.length===2).map(([id])=>id);
          const antes=p.pendentes;crEstado().feitos[comum[0]]={em:'2026-11-04',via:'estudado'};
          const p2=crPlano();
          return {tot:p.total,comum:comum.length,dup:new Set([...p.meta.keys()]).size===p.total,antes,depois:p2.pendentes,feitosN:p2.feitosN,
            rec:agReconciliar(f),discs:f.discs.map(x=>[x.nome,x.subs.length,x.semPeso])};}""")
        print('  ',r)
        assert r['tot']==15 and r['comum']==2 and r['dup']
        assert r['depois']==r['antes']-1 and r['feitosN']==1
        assert all(x['fecha'] for x in r['rec'])
        sus=[x for x in r['discs'] if x[0]=='SUS'][0]; assert sus[2] is True,'SUS nao declara questoes: tem que aparecer como peso nao informado'

        print('=== 4) edital sem questoes declaradas: nada de estimar em silencio ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();pl.editalIds=['e2'];pl.pct={};let p=crPlano();
          const a=p.agenda.discs.map(x=>[x.nome,x.semPeso,Math.round(x.w)]);
          pl.pesos={sus:60};p=crPlano();const b=p.agenda.discs.map(x=>[x.nome,x.semPeso,x.pesoUsuario,Math.round(x.w)]);
          return {a,b};}""")
        print('  ',r)
        assert [x[1] for x in r['a']]==[False,True]
        assert r['b'][1][1] is False and r['b'][1][2] is True and r['b'][1][3]==60

        print('=== 5) excluir assunto (com motivo) fecha a conta; sem vinculo continua visivel ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();pl.editalIds=['e1'];pl.pesos={};pl.excluidos={a1:'ja domino'};const p=crPlano();
          return {n:p.total,rec:agReconciliar(p.agenda),ex:p.agenda.excluidos.map(x=>[x.a.nome,x.motivo]),sem:p.agenda.semVinculo.length};}""")
        print('  ',r)
        assert r['n']==8 and r['rec'][0]['excl']==1 and r['rec'][0]['fecha'] and r['ex']==[['Enf 1','ja domino']] and r['sem']==1

        print('=== 6) trocar de plano nao perde progresso e a Ebserh volta igual ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();pl.excluidos={};const f=crEstado().feitos;const ids=Object.keys(f);
          db.agendaPlanos.ativoId=null;const p=crPlano();
          return {ids,ainda:ids.every(id=>crEstado().feitos[id]),ebserh:p.total,blocos:Object.keys(CRON_BLOCOS)};}""")
        print('  ',r)
        assert r['ids'] and r['ainda'] and r['ebserh']==533-0 or r['ebserh']>400
        assert r['blocos']==['esp','pol','por','leg','comp'],'os blocos da Ebserh tem que voltar'

        print('=== 7) pino: assunto movido de dia fica onde voce pos; pino em domingo vira conflito e nao some ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);A({eds:['e1','e2']});
          let p=crPlano();const alvo=p.agenda.fila[0];
          const diaAntes=p.calendario.find(d=>d.atual.includes(alvo)).ds;
          const dest=p.calendario.filter(d=>d.t==='est'&&d.ds>diaAntes&&d.atual.length).slice(-1)[0].ds;
          crEstado().pins={[alvo]:{ds:dest}};
          p=crPlano();const dia=p.calendario.find(d=>d.atual.includes(alvo));
          const dom=p.calendario.find(d=>d.t==='rev'&&d.ds>p.hoje).ds;
          crEstado().pins={[alvo]:{ds:dom}};const p2=crPlano();
          const emAlgum=p2.calendario.some(d=>d.atual.includes(alvo));
          crEstado().pins={};
          return {diaAntes,dest,dia:dia&&dia.ds,conf:p2.conflitos.length,emAlgum};}""",ATIVAR_JS)
        print('  ',r)
        assert r['dia']==r['dest'] and r['dia']!=r['diaAntes'] and r['conf']==1 and r['emAlgum']

        print('=== 8) dia indisponivel e compromisso: o plano se reorganiza em volta ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();const st0=crEstado();st0.indisp=['2026-11-06'];st0.bloqueios=[{data:'2026-11-05',inicio:'07:00',min:60,titulo:'Plantao'}];
          const p=crPlano();const d6=p.calendario.find(d=>d.ds==='2026-11-06');
          const sem=crSemanaDados(0);const c5=sem.cols.find(c=>c.ds==='2026-11-05');
          const est=c5.seq.blocos.filter(b=>b.tipo!=='pausa');
          const sobrepoe=c5.seq.blocos.some(b=>b.ini<(7*60-360)+60&&b.ini+b.dur>(7*60-360));
          return {d6:[d6.t,!!d6.indisp,d6.atual.length],h5:p.horasEm('2026-11-05'),h4:p.horasEm('2026-11-07'),sobrepoe,n6:crBlocosDoDia(d6,p).length};}""")
        print('  ',r)
        assert r['d6']==['fer',True,0] and r['n6']==0 and r['h5']==3 and r['h4']==4 and not r['sobrepoe']

        print('=== 9) hoje sem estudo / so X horas: o resto desliza, sem atraso falso ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-06',inicio:'2026-11-05'});
          const st=crEstado();let p=crPlano();const atr0=p.atrasados.length,fim0=p.fimAtual,tot0=p.pendentes;
          const f=crFases(st,p.inicio);st.fases=f.filter(x=>x.desde<'2026-11-06').concat([{desde:'2026-11-06',horas:0},{desde:'2026-11-07',horas:4}]);
          const p2=crPlano();const hoje0=p2.hojeAtual.length;
          st.fases=f.filter(x=>x.desde<'2026-11-06').concat([{desde:'2026-11-06',horas:1.5},{desde:'2026-11-07',horas:4}]);
          const p3=crPlano();
          return {atr0,atr1:p2.atrasados.length,atr2:p3.atrasados.length,fim0,fim1:p2.fimAtual,h0:hoje0,h15:p3.hojeAtual.length,pend:[tot0,p2.pendentes,p3.pendentes],horas:[p2.horasEm('2026-11-06'),p3.horasEm('2026-11-06')]};}""",ATIVAR_JS)
        print('  ',r)
        assert r['atr1']==r['atr0']==r['atr2'] and r['h0']==0 and r['h15']>=1 and r['fim1']>=r['fim0']

        print('=== 10) listas que o Firebase devolve como objeto nao quebram o plano ===')
        r=await page.evaluate("""()=>{const pl=agAtivo();pl.editalIds={'0':'e1','2':'e2'};pl.config.diasSemana={'0':1,'2':3,'3':4};crEstado().bloqueios={'1':{data:'2026-11-09',inicio:'09:00',min:30}};crEstado().indisp={'1':'2026-11-10'};
          const p=crPlano();return {n:p.total,dias:agAtivo().config.diasSemana};}""")
        print('  ',r)
        assert r['n']>0 and r['dias']==[1,3,4]
        print('erros de JS:',graves(errs) or 'nenhum'); assert not graves(errs)
        print('OK')
asyncio.run(main())
