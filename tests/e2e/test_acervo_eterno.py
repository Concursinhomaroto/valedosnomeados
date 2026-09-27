# -*- coding: utf-8 -*-
# "Meu banco de questoes precisa ser eterno." O que impedia nao era o teto: era o lugar.
# Dentro do registro principal, o banco subia INTEIRO a cada saveDB — ou seja, a cada
# resposta marcada. O app ficaria lento na razao direta do tamanho do banco, que e o
# contrario de eterno. Aqui ele tem no proprio no, gravado so quando muda.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed(extra=None):
    d={'studyNickname':'Leo',
       'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
       'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
           {'id':'s1','name':'Choque septico','priority':70,'studied':True}]}]}}
    d.update(extra or {})
    return make_seed(d)

def qs(tag,n):
    return [{'questao':'%s item %d sobre choque septico'%(tag,i),'correta':'C' if i%2 else 'E',
             'formato':'certoerrado','explicacao':'x','subId':'s1','subName':'Choque septico',
             'kingdomId':'k1','kingdomName':'Enfermagem','kingdomIcon':'💉'} for i in range(n)]

async def main():
    async with async_playwright() as p:
        print('=== A) o banco NAO entra no registro principal ===')
        b,page,errs=await setup_page(p,seed())
        r=await page.evaluate("""(lista)=>{
          db.acervo=lista;
          const payload=payloadParaFirebase();
          const {acervo,...semAcervo}=db;
          return {noPayload:payload.acervo,
                  emMemoria:(db.acervo||[]).length,
                  payloadTemOResto:!!payload.kingdoms&&!!payload.studyNickname,
                  tamComBanco:JSON.stringify(db).length,
                  tamDoPayload:JSON.stringify(payload).length};}""", qs('A',400))
        print('   400 questões em memória: %s · dentro do payload: %s'
              %(r['emMemoria'],r['noPayload']))
        print('   db inteiro: %s bytes · payload que sobe a cada saveDB: %s bytes'
              %(r['tamComBanco'],r['tamDoPayload']))
        assert r['noPayload'] is None and r['emMemoria']==400 and r['payloadTemOResto']
        assert r['tamDoPayload']<r['tamComBanco']/3
        print('   o registro que sobe a cada resposta não carrega mais o banco')
        print('   OK\n')

        print('=== B) saveDB nao reescreve o banco ===')
        r=await page.evaluate("""async()=>{
          window.__updateCalls=[];
          for(let i=0;i<5;i++)saveDB();
          await new Promise(r=>setTimeout(r,1200));
          const caminhos=window.__updateCalls.map(c=>c.path);
          return {saves:caminhos.length,
                  noAcervo:caminhos.filter(c=>/vdn_acervo/.test(c)).length,
                  noRegistro:caminhos.filter(c=>/vdn_v1/.test(c)).length};}""")
        print('   5 saveDB → %s gravações no registro, %s no nó do banco'
              %(r['noRegistro'],r['noAcervo']))
        assert r['noAcervo']==0 and r['noRegistro']>=1
        print('   o banco só é gravado quando o banco muda — é isso que deixa ele crescer')
        print('   OK\n')

        print('=== C) e gravado no no proprio quando muda ===')
        r=await page.evaluate("""async()=>{
          window.__updateCalls=[];
          const prova={questoes:[{questao:'nova do banco',correta:'C',subId:'s1',
            subName:'Choque septico',kingdomId:'k1',kingdomName:'Enfermagem'}],tentativas:[]};
          const novas=acervoGuardarProva(prova);
          await new Promise(r=>setTimeout(r,ACERVO_SALVA_MS+400));
          const c=window.__updateCalls.filter(x=>/vdn_acervo/.test(x.path));
          const noServidor=window.__root.users.TEST_UID_LEO.vdn_acervo||[];
          return {novas,gravacoes:c.length,caminho:c[0]&&c[0].path,
                  noServidor:noServidor.length,
                  temANova:noServidor.some(q=>q.questao==='nova do banco')};}""")
        print('   1 questão nova → %s gravação em "%s"'%(r['gravacoes'],r['caminho']))
        print('   no servidor: %s questões, com a nova: %s'%(r['noServidor'],r['temANova']))
        assert r['novas']==1 and r['gravacoes']==1 and r['temANova']
        assert r['caminho']=='users/TEST_UID_LEO/vdn_acervo'
        print('   OK\n')

        print('=== D) uniao das tres origens, sem duplicar ===')
        r=await page.evaluate("""(args)=>{
          const [nuvem,local,registro]=args;
          const u=acervoUnir(nuvem,local,registro);
          const repetida=acervoUnir(nuvem,nuvem,nuvem);
          return {nuvem:nuvem.length,local:local.length,registro:registro.length,
                  juntos:u.length, soUma:repetida.length,
                  ignoraLixo:acervoUnir([null,{},{questao:''},undefined]).length};}""",
          [qs('N',10), qs('N',6)+qs('L',4), qs('R',3)])
        print('   nuvem %s + local %s (6 repetidas) + registro %s → %s'
              %(r['nuvem'],r['local'],r['registro'],r['juntos']))
        assert r['juntos']==17, r['juntos']
        assert r['soUma']==10 and r['ignoraLixo']==0
        print('   o banco só cresce, então juntar é a resposta certa — não há conflito')
        print('   OK\n')

        print('=== E) o teto virou rede de seguranca, e nao e silencioso ===')
        r=await page.evaluate("""()=>{
          const antes=ACERVO_MAX;
          db.acervo=Array.from({length:ACERVO_MAX+3},(_,i)=>
            ({questao:'enche '+i,correta:'C',subId:'s1',kingdomId:'k1'}));
          let aviso='';
          const t=window.toast; window.toast=(m)=>{aviso=m;};
          acervoAvisou=true;              // o aviso de 80% tem teste proprio em test_hist_longo
          const cortou=acervoAparar();
          window.toast=t;
          // e nao existe mais teto por bytes
          db.acervo=Array.from({length:50},(_,i)=>
            ({questao:'x'.repeat(5000)+i,correta:'C',subId:'s1',kingdomId:'k1'}));
          const bytes=JSON.stringify(db.acervo).length;
          const semCorte=acervoAparar();
          return {teto:antes,cortou,aviso,bytes,semCorte,
                  temTetoBytes:typeof window.ACERVO_BYTES_MAX!=='undefined'};}""")
        print('   teto de segurança: %s · cortou %s e avisou: "%s"'
              %(r['teto'],r['cortou'],r['aviso'][:70]))
        print('   250 KB em 50 questões → cortou %s (teto por bytes existe? %s)'
              %(r['semCorte'],r['temTetoBytes']))
        assert r['teto']==50000 and r['cortou']==3 and 'limite' in r['aviso']
        assert r['semCorte']==0 and not r['temTetoBytes']
        print('   tamanho não derruba mais nada; só a contagem, e avisando')
        print('   OK\n')

        # o que ficou guardado vira a semente da proxima sessao
        salvo=await page.evaluate("()=>window.__root.users.TEST_UID_LEO.vdn_v1")
        graves=[e for e in errs if 'selectedPixTier' not in e]
        assert not graves,graves
        await b.close()

        print('=== F) migracao: quem tinha o banco DENTRO do registro ===')
        antigo=seed({'acervo':qs('VELHA',25)})
        b,page,errs=await setup_page(p,antigo)
        r=await page.evaluate("""async()=>{
          await new Promise(r=>setTimeout(r,600));
          const raiz=window.__root.users.TEST_UID_LEO;
          return {emMemoria:(db.acervo||[]).length,
                  noNoProprio:(raiz.vdn_acervo||[]).length,
                  aindaNoRegistro:raiz.vdn_v1.acervo===undefined?'não':(raiz.vdn_v1.acervo||[]).length,
                  aVelhaSobreviveu:(db.acervo||[]).some(q=>q.questao.startsWith('VELHA'))};}""")
        print('   em memória: %s · no nó próprio: %s · ainda dentro do registro: %s'
              %(r['emMemoria'],r['noNoProprio'],r['aindaNoRegistro']))
        assert r['emMemoria']==25 and r['noNoProprio']==25
        assert r['aindaNoRegistro']=='não' and r['aVelhaSobreviveu']
        print('   as 25 mudaram de lugar sozinhas, e o registro principal encolheu')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        assert not graves,graves
        await b.close()
        print('   OK\n')

        print('=== G) fecha o app e abre de novo: o banco continua la ===')
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("""(lista)=>{
          window.__root.users.TEST_UID_LEO.vdn_acervo=lista;   // o que ficou de ontem
          return true;}""", qs('ONTEM',120))
        r=await page.evaluate("""async()=>{
          const n=await acervoCarregar();
          return {carregou:n, emMemoria:db.acervo.length,
                  deOntem:db.acervo.filter(q=>q.questao.startsWith('ONTEM')).length,
                  naTela:montarAcervo().length};}""")
        print('   abriu o app: %s questões vieram do nó (%s de ontem)'
              %(r['carregou'],r['deOntem']))
        print('   disponíveis pra montar prova: %s'%r['naTela'])
        assert r['carregou']==120 and r['deOntem']==120 and r['naTela']==120
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('   erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('   OK\n')
        print('OK')

asyncio.run(main())
