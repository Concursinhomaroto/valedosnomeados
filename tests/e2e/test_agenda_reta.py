# -*- coding: utf-8 -*-
# Montar 28 cartoes na mao toda segunda e atrito, e planejamento e a primeira coisa
# que cai quando o dia aperta. O botao escreve a semana padrao da reta final sem
# encostar no que o usuario marcou.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True}]}]}})

LER = """()=>{
  const hoje=todayStr();const out=[];
  for(let i=0;i<7;i++){
    const ds=addDays(hoje,i);
    const dow=new Date(ds+'T00:00:00').getDay();
    const l=db.weeklyPlan[ds]||[];
    out.push({ds,dow,n:l.length,reta:l.filter(x=>x.reta).length,
              nomes:l.map(x=>x.name),cores:l.filter(x=>x.reta).map(x=>x.kColor)});
  }
  return out;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")

        print('=== A) o botao existe no cabecalho da agenda ===')
        txt=await page.evaluate("""()=>{
          const h=document.querySelectorAll('.dash-head');
          for(const el of h){if(/agenda semanal/i.test(el.innerText)){
            const b=el.querySelector('button[onclick*="planoRetaFinal"]');
            return b?b.innerText.trim():'SEM BOTAO';}}
          return 'SEM CABECALHO';}""")
        print('   botao: %r'%txt)
        assert 'Reta final' in txt, txt
        print('   OK\n')

        print('=== B) um item seu, escrito antes, sobrevive ===')
        await page.evaluate("""()=>{const hoje=todayStr();
          db.weeklyPlan={};db.weeklyPlan[hoje]=[{name:'Academia 18h',livre:true}];
          renderWeeklyPlan();return true;}""")
        await page.evaluate("()=>{planoRetaFinal();return true;}")
        dias=await page.evaluate(LER)
        d0=dias[0]
        print('   hoje (dow %s): %s itens, %s vindos do botao'%(d0['dow'],d0['n'],d0['reta']))
        assert 'Academia 18h' in d0['nomes']
        assert d0['nomes'][0]=='Academia 18h', 'o item do usuario tem que continuar em primeiro'
        print('   OK\n')

        print('=== C) cada dia da semana recebe o bloco certo ===')
        ESPERADO={0:3,1:4,2:4,3:4,4:4,5:4,6:3}   # dom=3, seg-sex=4, sab=3
        for d in dias:
            nome=['dom','seg','ter','qua','qui','sex','sab'][d['dow']]
            print('   %s %s · %s blocos'%(nome,d['ds'][5:],d['reta']))
            assert d['reta']==ESPERADO[d['dow']], (nome,d['reta'])
        # terca e quinta sao os dias dos conhecimentos gerais (42% da prova)
        ger=[d for d in dias if d['dow'] in (2,4)]
        for d in ger:
            assert any('GERAIS' in n for n in d['nomes']), d['nomes']
        esp=[d for d in dias if d['dow'] in (1,3,5)]
        for d in esp:
            assert any('específica' in n for n in d['nomes']), d['nomes']
            assert not any('GERAIS' in n for n in d['nomes'])
        print('   ter/qui vao pros GERAIS (%s dias), seg/qua/sex pra específica (%s dias)'
              %(len(ger),len(esp)))
        # sabado tem a prova, domingo tem a autopsia
        sab=[d for d in dias if d['dow']==6]
        dom=[d for d in dias if d['dow']==0]
        if sab: assert any('120 itens' in n for n in sab[0]['nomes']), sab[0]['nomes']
        if dom: assert any('Autópsia da prova' in n for n in dom[0]['nomes']), dom[0]['nomes']
        print('   sábado: prova de 120 · domingo: autópsia + refazer prova guardada')
        print('   OK\n')

        print('=== D) clicar duas vezes nao duplica nada ===')
        antes=[d['n'] for d in dias]
        await page.evaluate("()=>{planoRetaFinal();planoRetaFinal();return true;}")
        dias2=await page.evaluate(LER)
        print('   itens por dia: %s -> %s'%(antes,[d['n'] for d in dias2]))
        assert [d['n'] for d in dias2]==antes
        for d in dias2:
            assert len(set(d['nomes']))==len(d['nomes']), d['nomes']
        print('   OK\n')

        print('=== E) bloco que voce apagou volta se pedir de novo ===')
        r=await page.evaluate("""()=>{const hoje=todayStr();
          const ds=addDays(hoje,1);
          const i=db.weeklyPlan[ds].findIndex(x=>x.reta);
          const nome=db.weeklyPlan[ds][i].name;
          removePlanItem(ds,i);
          const depoisDeApagar=db.weeklyPlan[ds].length;
          planoRetaFinal();
          return {nome,depoisDeApagar,agora:db.weeklyPlan[ds].length,
                  voltou:db.weeklyPlan[ds].some(x=>x.name===nome)};}""")
        print('   apaguei %r -> %s itens · depois do botao: %s (voltou: %s)'
              %(r['nome'],r['depoisDeApagar'],r['agora'],r['voltou']))
        assert r['voltou'] and r['agora']==r['depoisDeApagar']+1
        print('   OK\n')

        print('=== F) se voce ja tinha escrito o mesmo na mao, nao entra de novo ===')
        # o dia da semana decide o bloco, e domingo TAMBEM tem um item de fila. Contar
        # "cartoes que falam em fila" dava 2 no domingo e 1 no sabado — flaky. O que
        # importa e que nenhum nome se repita no dia.
        r=await page.evaluate("""()=>{const hoje=todayStr();
          db.weeklyPlan={};
          const meu='1️⃣ 50min · fila de revisao (sem tentar zerar)';
          db.weeklyPlan[hoje]=[{name:meu,livre:true}];
          planoRetaFinal();
          const l=db.weeklyPlan[hoje];
          const norm=l.map(x=>normalizeForDedup(x.name));
          return {n:l.length,nomes:l.map(x=>x.name),
                  meuSobreviveu:l.some(x=>x.name===meu),
                  duplicados:norm.length-new Set(norm).size,
                  dow:new Date(hoje+'T00:00:00').getDay()};}""")
        nome_dia=['dom','seg','ter','qua','qui','sex','sab'][r['dow']]
        print('   hoje é %s · %s itens no dia'%(nome_dia,r['n']))
        print('   o item que eu escrevi continua: %s · nomes repetidos: %s'
              %(r['meuSobreviveu'],r['duplicados']))
        assert r['meuSobreviveu'], r['nomes']
        assert r['duplicados']==0, r['nomes']
        print('   OK\n')

        print('=== G) os blocos aparecem na grade, com cor e sem quebrar o HTML ===')
        r=await page.evaluate("""()=>{
          const g=document.getElementById('weekly-plan');
          const itens=g.querySelectorAll('.plan-item');
          const cores=new Set([...itens].map(el=>el.style.borderLeftColor).filter(Boolean));
          return {itens:itens.length,cores:cores.size,
                  texto:(itens[0]||{}).innerText||''};}""")
        print('   cartões na grade: %s · cores distintas: %s'%(r['itens'],r['cores']))
        print('   primeiro: %r'%r['texto'].replace('\n',' | ')[:70])
        assert r['itens']>=20 and r['cores']>=3
        print('   OK\n')

        await page.screenshot(path='agenda_reta.png')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
