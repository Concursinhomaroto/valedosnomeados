# "Faco 100 questoes de Enfermagem, nao escolho assunto." Ratear as 100 entre os
# assuntos do reino inventaria desempenho por assunto que nunca foi medido. Entao o
# registro fica no nivel do reino e so age onde nao ha medida melhor.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

K1='k1'; K2='k2'; T1='t1'; T2='t2'

def seed():
    return make_seed({'studyNickname':'Leo',
        'kingdoms':[{'id':K1,'name':'Enfermagem','icon':'💉','color':'#e11d48'},
                    {'id':K2,'name':'Portugues','icon':'📖','color':'#3b82f6'}],
        'topics':{
          K1:[{'id':T1,'name':'Fundamentos','icon':'⚔️','subtopics':[
                {'id':'sem','name':'Sem simulado','priority':70,'studied':True,'studiedAt':'2026-01-01'},
                {'id':'com','name':'Com simulado','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}],
          K2:[{'id':T2,'name':'Sintaxe','icon':'⚔️','subtopics':[
                {'id':'pt','name':'Crase','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

ABRE = """()=>{openKingdom(db.kingdoms.find(k=>k.id==='%s'));return true;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        hoje=await page.evaluate("()=>todayStr()")
        await page.evaluate(ABRE%K1)

        print('=== A) a tela do reino oferece registrar ===')
        r=await page.evaluate("""()=>{const t=document.getElementById('kingdom-externos').textContent;
          return {secao:t.indexOf('Questões feitas fora daqui')>=0,btn:t.indexOf('Registrar')>=0};}""")
        print('   %s'%r); assert r['secao'] and r['btn']
        print('   OK\n')

        print('=== B) acertos acima da quantidade nao passa ===')
        r=await page.evaluate("""()=>{reinoAbrirExterno();
          document.getElementById('reino-ext-qtd').value=100;
          document.getElementById('reino-ext-ac').value=120;
          reinoExternoConfere();
          const aviso=document.getElementById('reino-ext-aviso').textContent;
          reinoRegistrarExterno();
          return {aviso,reg:((db.simExternosReino||{})['%s']||[]).length};}"""%K1)
        print('   aviso: %r · registros: %s'%(r['aviso'],r['reg']))
        assert 'passar da quantidade' in r['aviso'] and r['reg']==0
        print('   OK\n')

        print('=== C) 100 questoes a 55%, certo/errado: guarda e mostra corrigido ===')
        r=await page.evaluate("""(hoje)=>{
          document.getElementById('reino-ext-qtd').value=100;
          document.getElementById('reino-ext-ac').value=55;
          document.getElementById('reino-ext-fmt').value='certoerrado';
          document.getElementById('reino-ext-fonte').value='Qconcursos';
          reinoExternoConfere();
          const aviso=document.getElementById('reino-ext-aviso').textContent;
          reinoRegistrarExterno();
          const t=document.getElementById('kingdom-externos').textContent;
          return {aviso,reg:db.simExternosReino['%s'],
                  badge:t.replace(/\\s+/g,' '),
                  st:reinoExtStats('%s'),ef:simPctEfetivo(reinoExtStats('%s'))};}"""%(K1,K1,K1),hoje)
        print('   aviso ao vivo: %r'%r['aviso'])
        print('   registro: %s'%r['reg'][0])
        print('   bruto %s%% · corrigido %s%%'%(r['ef']['bruto'],r['ef']['corrigido']))
        assert r['reg'][0]['quantidade']==100 and r['reg'][0]['acertos']==55
        assert r['ef']['bruto']==55 and r['ef']['corrigido']==10
        assert '55/100' in r['badge'] and '10%' in r['badge']
        print('   OK\n')

        print('=== D) nao encostou no simStats de nenhum assunto ===')
        r=await page.evaluate("""()=>['sem','com','pt'].map(id=>[id,simFindSub(id).simStats||null])""")
        print('   %s'%r)
        assert all(v is None for _,v in r)
        print('   OK\n')

        print('=== E) pesa so em quem nao tem simulado proprio ===')
        r=await page.evaluate("""()=>{
          const antes={sem:revPeso(simFindSub('sem'),'%s'),
                       com:revPeso(simFindSub('com'),'%s'),
                       pt:revPeso(simFindSub('pt'),'%s')};
          // o assunto "com" passa a ter medida propria, e boa
          simFindSub('com').simStats={tentativas:1,questoesTotal:30,acertosTotal:27,
            porFormato:{multipla:{tentativas:1,questoes:30,acertos:27}}};
          return {antes,depois:{sem:revPeso(simFindSub('sem'),'%s'),
                                com:revPeso(simFindSub('com'),'%s')},
                  reino:revAcertoReino('%s'),
                  reinoDoTopico:revReinoDoTopico('%s')};}"""%(T1,T1,T2,T1,T1,K1,T1))
        print('   reino medido: %s'%r['reino'])
        print('   topico %s pertence ao reino %s'%(T1,r['reinoDoTopico']))
        print('   sem simulado proprio (Enfermagem): %.3f  ← puxado pelo reino'%r['antes']['sem'])
        print('   outro reino, sem registro (Portugues): %.3f  ← intocado'%r['antes']['pt'])
        print('   com simulado proprio bom: %.3f  ← o reino nao manda nele'%r['depois']['com'])
        assert r['reinoDoTopico']==K1
        assert r['antes']['sem']>r['antes']['pt']          # reino fraco empurra pra cima
        assert abs(r['antes']['pt']-1.0)<0.001             # reino sem registro nao mexe
        assert r['depois']['com']<r['antes']['sem']        # medida propria manda
        print('   OK\n')

        print('=== F) o sinal do reino vale metade do sinal do assunto ===')
        r=await page.evaluate("""()=>{
          const s=simFindSub('sem');
          const comReino=revPeso(s,'%s');
          // mesmo desempenho, mas medido NO ASSUNTO
          s.simStats={tentativas:1,questoesTotal:100,acertosTotal:10,
                      porFormato:{multipla:{tentativas:1,questoes:100,acertos:10}}};
          const comAssunto=revPeso(s,'%s');
          delete s.simStats;
          return {comReino,comAssunto};}"""%(T1,T1))
        print('   10%% medido no reino:   %.3f'%r['comReino'])
        print('   10%% medido no assunto: %.3f  ← mexe o dobro'%r['comAssunto'])
        assert r['comAssunto']>r['comReino']>1.0
        print('   OK\n')

        print('=== G) o aviso na tela explica que mede o reino, nao o assunto ===')
        r=await page.evaluate("""()=>document.getElementById('kingdom-externos').textContent
            .replace(/\\s+/g,' ')""")
        assert 'mede o reino, não cada assunto' in r and 'metade da força' in r
        print('   %s'%r[r.index('Isso mede'):][:150])
        print('   OK\n')

        print('=== H) apagar tira o efeito da fila ===')
        r=await page.evaluate("""()=>{window.confirm=()=>true;
          const id=db.simExternosReino['%s'][0].id;
          reinoRemoverExterno(id);
          return {reg:(db.simExternosReino['%s']||[]).length,
                  reino:revAcertoReino('%s'),
                  peso:revPeso(simFindSub('sem'),'%s')};}"""%(K1,K1,K1,T1))
        print('   registros: %s · reino: %s · peso de volta a %.3f'
              %(r['reg'],r['reino'],r['peso']))
        assert r['reg']==0 and r['reino'] is None and abs(r['peso']-1.0)<0.001
        print('   OK\n')

        print('=== I) cada reino tem o seu, e a troca de tela acompanha ===')
        r=await page.evaluate("""async(hoje)=>{
          reinoAbrirExterno();
          document.getElementById('reino-ext-qtd').value=40;
          document.getElementById('reino-ext-ac').value=38;
          reinoRegistrarExterno();
          const enf=document.getElementById('kingdom-externos').textContent.replace(/\\s+/g,' ');
          openKingdom(db.kingdoms.find(k=>k.id==='%s'));
          const pt=document.getElementById('kingdom-externos').textContent.replace(/\\s+/g,' ');
          return {enf:enf.indexOf('38/40')>=0, ptVazio:pt.indexOf('/')<0,
                  chaves:Object.keys(db.simExternosReino)};}"""%K2,hoje)
        print('   Enfermagem mostra 38/40: %s · Portugues vazio: %s · chaves: %s'
              %(r['enf'],r['ptVazio'],r['chaves']))
        assert r['enf'] and r['ptVazio'] and r['chaves']==[K1]
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
