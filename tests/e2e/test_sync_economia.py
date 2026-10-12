# -*- coding: utf-8 -*-
# Economia de download do Firebase (o plano gratuito estourou: 73 GB em 30 dias, com o
# banco inteiro tendo 70 MB). Duas mudanças:
#  1) saveDB sobe só os caminhos que mudaram (update), não o registro inteiro (set) — os
#     outros aparelhos abertos baixam só esse pedaço;
#  2) banco de questões / histórico / arquivo de provas têm um irmão <nó>_ver: se a versão
#     da nuvem é a mesma da cópia local, a abertura do app não baixa o nó de novo.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

UID='TEST_UID_LEO'
def seed():
    subs=[{'id':'s0','name':'Assunto 0','priority':70,'studied':True,'studiedAt':'2026-01-01'},
          {'id':'s1','name':'Assunto 1','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
    return make_seed({'studyNickname':'Leo','xp':100,'campoVelho':'x',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]},
      'revisions':{'s0':[{'date':'2026-01-10','completed':False}],'s1':[{'date':'2026-01-12','completed':False}]}})

ULTIMA="""(path)=>{const c=window.__updateCalls.filter(x=>x.path===path);return c.length?c[c.length-1]:null;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        V1='users/%s/vdn_v1'%UID
        await page.wait_for_timeout(1500)

        print('=== A) mudar o XP sobe só xp (+ lastModified), não o registro inteiro ===')
        await page.evaluate("()=>{window.__updateCalls=[];db.xp=101;saveDB();}")
        await page.wait_for_timeout(1100)
        r=await page.evaluate(ULTIMA,V1)
        print('   %s'%{'op':r['op'],'chaves':sorted(r['val'].keys())})
        assert r['op']=='update' and sorted(r['val'].keys())==['lastModified','xp'] and r['val']['xp']==101
        print('   OK\n')

        print('=== B) mudar uma revisão sobe só revisions/<assunto> ===')
        await page.evaluate("()=>{window.__updateCalls=[];db.revisions.s0[0].completed=true;saveDB();}")
        await page.wait_for_timeout(1100)
        r=await page.evaluate(ULTIMA,V1)
        print('   %s'%sorted(r['val'].keys()))
        assert r['op']=='update' and sorted(r['val'].keys())==['lastModified','revisions/s0']
        print('   OK\n')

        print('=== C) campo apagado vira null no update ===')
        await page.evaluate("()=>{window.__updateCalls=[];delete db.campoVelho;saveDB();}")
        await page.wait_for_timeout(1100)
        r=await page.evaluate(ULTIMA,V1)
        print('   %s'%r['val'])
        assert r['op']=='update' and r['val'].get('campoVelho') is None and 'campoVelho' in r['val']
        srv=await page.evaluate("(p)=>{let n=window.__root;p.split('/').forEach(s=>{n=n&&n[s];});return n?('campoVelho' in n):null;}",V1)
        assert srv is False
        print('   OK\n')

        print('=== D) mudança feita em outro aparelho é preservada (não sobrescrita) ===')
        r=await page.evaluate("""(p)=>{firebase.database().ref(p+'/notaDeOutroAparelho').set('oi');
          window.__updateCalls=[];db.xp=102;saveDB();return true;}""",V1)
        await page.wait_for_timeout(1100)
        r=await page.evaluate("""(p)=>{const c=window.__updateCalls.filter(x=>x.path===p).pop();
          let n=window.__root;p.split('/').forEach(s=>{n=n&&n[s];});
          return {chaves:Object.keys(c.val).sort(),servidor:n.notaDeOutroAparelho,local:db.notaDeOutroAparelho,xp:n.xp};}""",V1)
        print('   %s'%r)
        assert r['chaves']==['lastModified','xp'] and r['servidor']=='oi' and r['local']=='oi' and r['xp']==102
        print('   OK\n')

        print('=== E) se a gravação falha, a próxima manda o registro inteiro (set), como antes ===')
        r=await page.evaluate("""async(p)=>{const real=DB_REF.update;DB_REF.update=()=>Promise.reject(new Error('rede'));
          db.xp=103;saveDB();await new Promise(r=>setTimeout(r,1100));DB_REF.update=real;
          window.__updateCalls=[];db.xp=104;saveDB();await new Promise(r=>setTimeout(r,1100));
          const c=window.__updateCalls.filter(x=>x.path===p).pop();return {op:c.op,xp:c.val.xp};}""",V1)
        print('   %s'%r)
        assert r=={'op':'set','xp':104}
        print('   OK\n')

        print('=== F) banco de questões: mesma versão na nuvem = não baixa; mudou = baixa ===')
        r=await page.evaluate("""async(uid)=>{
          const q={questao:'Q1: julgue.',correta:'C',formato:'certoerrado',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
            explicacao:'.',subId:'s0',subName:'Assunto 0',topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'};
          db.acervo=[{...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')}];
          acervoSalvar(true);await new Promise(r=>setTimeout(r,600));
          const verNuvem=(window.__root.users[uid]||{}).vdn_acervo_ver;
          const verLocal=await idbLer(acervoChaveCache()+'_ver');
          // espia as leituras
          const orig=firebaseDB.ref.bind(firebaseDB);window.__onces=[];
          firebaseDB.ref=(p)=>{const r=orig(p);const o=r.once.bind(r);r.once=(...a)=>{window.__onces.push(p);return o(...a);};return r;};
          await acervoCarregar();
          const leu1=window.__onces.slice();
          // outro aparelho gravou: a versão da nuvem muda
          window.__root.users[uid].vdn_acervo_ver={ts:Date.now()+5};
          window.__onces=[];await acervoCarregar();
          const leu2=window.__onces.slice();
          firebaseDB.ref=orig;
          return {verNuvem:!!(verNuvem&&verNuvem.ts),igual:!!(verLocal&&verNuvem&&verLocal.ts===verNuvem.ts),
            baixou1:leu1.includes('users/'+uid+'/vdn_acervo'),baixou2:leu2.includes('users/'+uid+'/vdn_acervo'),n:db.acervo.length};}""",UID)
        print('   %s'%r)
        assert r['verNuvem'] and r['igual'] and not r['baixou1'] and r['baixou2'] and r['n']==1
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
