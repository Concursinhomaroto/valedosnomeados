import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1';S='s1'

def c(i,q,cri,ac=0,er=0):
    return {'id':i,'mbId':T,'subId':S,'pergunta':q,'resposta':'r'+i,'tags':'','dificuldade':2,
            'acertos':ac,'erros':er,'lastConf':0,'criacao':cri,'ultimaRevisao':None}

FC={}
# 10 pares de texto IDENTICO (so muda pontuacao/caixa)
for i in range(10):
    FC['v%d'%i]=c('v%d'%i,'Qual a dose %d de adrenalina na parada?'%i,'2026-01-%02dT10:00:00Z'%(i+1),ac=3)
    FC['n%d'%i]=c('n%d'%i,'QUAL A DOSE %d DE ADRENALINA NA PARADA?'%i,'2026-02-%02dT10:00:00Z'%(i+1))
# 4 pares apenas PARECIDOS (irmaos legitimos, nao podem vir marcados)
irmaos=[('Qual a classificação de risco da dengue grupo A?','Qual a classificação de risco da dengue grupo B?'),
        ('Qual o esquema de tratamento da hanseníase multibacilar?','Qual o esquema de tratamento da hanseníase paucibacilar?'),
        ('Qual a periodicidade da consulta de pré-natal de baixo risco?','Qual a periodicidade da consulta de pré-natal de alto risco?'),
        ('Qual a meta de PAM no choque séptico grave?','Qual a meta de PAM no choque séptico leve?')]
for i,(x,y) in enumerate(irmaos):
    FC['ia%d'%i]=c('ia%d'%i,x,'2026-03-%02dT10:00:00Z'%(i+1))
    FC['ib%d'%i]=c('ib%d'%i,y,'2026-04-%02dT10:00:00Z'%(i+1))

seed=make_seed({'studyNickname':'Leo','flashcards':FC,
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'Urgência','subtopics':[{'id':S,'name':'PCR','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            r=await page.evaluate("""()=>{
              const pares=fcAcharPares(Object.values(db.flashcards));
              return {total:pares.length,
                      exatos:pares.filter(x=>x.exato).length,
                      marcadosParaApagar:pares.filter(x=>x.acao==='a'||x.acao==='b').length,
                      parecidosMarcados:pares.filter(x=>!x.exato&&(x.acao==='a'||x.acao==='b')).length,
                      primeirosSaoExatos:pares.slice(0,10).every(x=>x.exato)};}""")
            print('1) pares:',r['total'],'| idênticos:',r['exatos'],'| parecidos:',r['total']-r['exatos'])
            # Dos 4 pares de irmaos legitimos, so o "dengue grupo A/B" passa do limiar
            # (0.8): os outros tres ficam em 0.60-0.67 e nem sao apontados. O que importa
            # aqui e que o unico apontado venha DESMARCADO.
            assert r['exatos']==10, r
            assert r['total']-r['exatos']>=1, 'esperava ao menos um par so parecido no cenario'
            print('2) já marcados para apagar:',r['marcadosParaApagar'],'(só os idênticos)')
            assert r['marcadosParaApagar']==10
            print('3) IRMÃOS LEGÍTIMOS marcados por engano:',r['parecidosMarcados'])
            assert r['parecidosMarcados']==0, 'pergunta so parecida nao pode vir marcada pra apagar'
            print('4) idênticos aparecem primeiro na lista:',r['primeirosSaoExatos'])
            assert r['primeirosSaoExatos']

            await page.evaluate("()=>fcRevisarDupChefao()")
            await page.wait_for_timeout(400)
            h=await page.evaluate("()=>document.getElementById('modal-body').innerHTML")
            rot=await page.evaluate("()=>document.querySelector('.dup-rodape .btn-danger').innerText.trim()")
            print('5) resumo no topo:', '10' in h and 'texto idêntico' in h and 'desmarcadas' in h)
            assert 'desmarcadas' in h
            print('6) botão final:',repr(rot))
            assert 'Apagar 10' in rot

            await page.evaluate("()=>fcDupDesmarcarTodas()"); await page.wait_for_timeout(200)
            rot=await page.evaluate("()=>document.querySelector('.dup-rodape .btn-danger').innerText.trim()")
            desab=await page.evaluate("()=>document.querySelector('.dup-rodape .btn-danger').disabled")
            print('7) depois de "Não apagar nenhuma":',repr(rot),'| botão desabilitado:',desab)
            assert 'Apagar' not in rot and desab, 'sem nada selecionado o botao nao pode agir'
            # o ponto critico: isso NAO pode declarar os 11 pares como "sao diferentes"
            nen=await page.evaluate("()=>fcDupPares.filter(p=>p.acao==='nenhum').length")
            print('   pares declarados como "sao diferentes":',nen,'(tem que ser 0)')
            assert nen==0, 'o botao de massa silenciou pares que ninguem conferiu'
            await page.evaluate("()=>fcDupMarcarIdenticas()"); await page.wait_for_timeout(200)
            rot=await page.evaluate("()=>document.querySelector('.dup-rodape .btn-danger').innerText.trim()")
            print('8) depois de "Marcar as idênticas":',repr(rot))
            assert 'Apagar 10' in rot

            await page.evaluate("()=>fcDupAplicar()"); await page.wait_for_timeout(500)
            fim=await page.evaluate("""()=>({n:Object.keys(db.flashcards).length,
                 sobrouVelho:!!db.flashcards.v0, sobrouNovo:!!db.flashcards.n0,
                 irmaosIntactos:!!db.flashcards.ia0&&!!db.flashcards.ib0})""")
            print('9) depois de aplicar ->',fim)
            assert fim['n']==18 and fim['sobrouVelho'] and not fim['sobrouNovo']
            assert fim['irmaosIntactos'], 'apagou irmao legitimo'
            # o par so parecido, que ninguem decidiu, tem que continuar sendo apontado
            resta=await page.evaluate("()=>fcAcharPares(Object.values(db.flashcards)).length")
            print('10) pares que sobraram pra decidir depois:',resta,'(o parecido nao foi silenciado)')
            assert resta==1, resta
            print('   OK — apagou as 10 repetidas, manteve a que tem histórico, não tocou nos irmãos')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
