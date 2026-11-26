import datetime
from pyxlsb import open_workbook

OPCOES = ['BELLEVIE','VILLA NOAH','Todos Bambuzal','VICTÓRIA GARDEN','AVOS','HIRAIWA','UNA','NELSON E MARCELO','Todos']
CATS = [('Receita','Receita bruta de vendas'),('Distrato','(−) Distratos'),('Comissão Avos','(−) Comissões de vendas'),('Impostos','(−) Impostos'),
        (None,'(=) Receita líquida'),('Obra','(−) Obras e infraestrutura'),('Terreno (compra)','(−) Terreno (compra)'),('Aprovação','(−) Aprovação de projetos'),
        ('Marketing + Plantão Vendas','(−) Marketing e plantão de vendas'),('Administrativo','(−) Administrativo'),('Taxa administrativa','(±) Taxa de administração'),
        (None,'(=) Resultado operacional'),(None,'Margem operacional'),('Financeiro','(±) Resultado financeiro'),(None,'(=) Fluxo antes dos sócios'),
        ('Aporte de*','(+) Aportes de terceiro'),('Retirada Sócios','(−) Retirada de sócios'),('Lucro a Terceiros','(−) Lucro distribuído a terceiros'),
        ('Lucro grupo','(±) Lucro grupo (intercompany)'),(None,'(=) Geração de caixa líquida'),(None,'Saldo de caixa inicial'),(None,'Saldo de caixa final')]
ANOS = list(range(2019,2027))
OPER = ['Receita','Distrato','Comissão Avos','Impostos','Obra','Terreno (compra)','Aprovação','Marketing + Plantão Vendas','Administrativo','Taxa administrativa','Financeiro']
low = lambda s: str(s or '').strip().lower()

def xdate(v):
    if isinstance(v,(int,float)): return datetime.date(1899,12,30)+datetime.timedelta(days=int(v))
    return None

def ler(path):
    base=[]; lista=[]; ind=[]
    with open_workbook(path) as wb:
        with wb.get_sheet('BASE PASSADO') as sh:
            for i,row in enumerate(sh.rows()):
                if i==0: continue
                v=[c.v for c in row]+[None]*22
                d=xdate(v[2]); val=v[8]
                if d is None or not isinstance(val,(int,float)): continue
                base.append((d,float(val),low(v[19]),low(v[16]),low(v[20])))
        with wb.get_sheet('lista depara') as sh:
            for i,row in enumerate(sh.rows()):
                if i==0: continue
                v=[c.v for c in row]+[None]*8
                if 1<=i<=13 and v[0]: lista.append((v[0],v[1]))
                if v[4] and v[5]: ind.append((low(v[4]),low(v[5]),v[6] if isinstance(v[6],(int,float)) else 0.0))
    return base,lista,ind

def irr(fl):
    def npv(r): return sum(f/(1+r)**i for i,f in enumerate(fl))
    lo,hi=-0.99,1.0
    try:
        if npv(lo)*npv(hi)>0: return None
    except ZeroDivisionError: return None
    for _ in range(200):
        m=(lo+hi)/2
        if npv(lo)*npv(m)<=0: hi=m
        else: lo=m
    return m

def calcular(base,lista,ind,sel):
    nomes_ind=[low(a) for a,_ in lista]
    if sel=='Todos': f=lambda r: True
    elif low(sel) in nomes_ind[:12]: f=lambda r: r[3]==low(sel)
    else: f=lambda r: r[4]==low(sel)
    rows=[r for r in base if f(r)]
    def cat_ok(c,pat): return c.startswith(pat[:-1].lower()) if pat.endswith('*') else c==pat.lower()
    # anual
    tab={}
    for pat,_ in CATS:
        if pat: tab[pat]=[sum(r[1] for r in rows if r[0].year==y and cat_ok(r[2],pat))/1000 for y in ANOS]
    L={}
    def setl(n,arr): L[n]=arr
    k=lambda p: tab[p]
    add=lambda *a: [sum(x) for x in zip(*a)]
    rl=add(k('Receita'),k('Distrato'),k('Comissão Avos'),k('Impostos'))
    ro=add(rl,k('Obra'),k('Terreno (compra)'),k('Aprovação'),k('Marketing + Plantão Vendas'),k('Administrativo'),k('Taxa administrativa'))
    mg=[(o/r if r else 0) for o,r in zip(ro,k('Receita'))]
    fas=add(ro,k('Financeiro'))
    gl=add(fas,k('Aporte de*'),k('Retirada Sócios'),k('Lucro a Terceiros'),k('Lucro grupo'))
    ini=[];fin=[];s=0
    for g in gl: ini.append(s); s+=g; fin.append(s)
    seq={'(=) Receita líquida':rl,'(=) Resultado operacional':ro,'Margem operacional':mg,'(=) Fluxo antes dos sócios':fas,'(=) Geração de caixa líquida':gl,'Saldo de caixa inicial':ini,'Saldo de caixa final':fin}
    T=lambda a: sum(a)
    linhas=[]
    for pat,lab in CATS:
        arr=tab[pat] if pat else seq[lab]
        tot=T(arr)
        if lab=='Margem operacional': tot=(T(ro)/T(k('Receita')) if T(k('Receita')) else 0)
        if lab=='Saldo de caixa inicial': tot=0
        if lab=='Saldo de caixa final': tot=fin[-1]
        linhas.append(dict(lin=lab,tot=tot,pct=(tot/T(k('Receita')) if T(k('Receita')) and lab not in ('Margem operacional','Saldo de caixa inicial') else None),anos=arr))
    C=lambda lab: next(l['tot'] for l in linhas if l['lin']==lab)
    # mensal antes dos sócios
    meses=[]; d=datetime.date(2019,1,1)
    for _ in range(96):
        meses.append(d); d=datetime.date(d.year+(d.month==12),d.month%12+1,1)
    ms=[sum(r[1] for r in rows if r[0].year==m.year and r[0].month==m.month and any(cat_ok(r[2],p) for p in OPER)) for m in meses]
    acc=[];s=0
    for v in ms: s+=v; acc.append(s)
    # indicadores
    grp=[low(a) for a,b in lista if low(b)==low(sel)]
    alvo=grp if grp else [low(sel)]
    if low(sel) not in alvo: alvo.append(low(sel))
    gi=lambda pat: sum(v for g,i,v in ind if g in alvo and i.startswith(pat.lower()))
    O10=gi('Área líquida vendável Empreendimento'); O11=gi('Área líquida vendável AVOS'); O12=gi('Qdade de lotes Empreendimento'); O13=gi('Qdade de lotes AVOS')
    O14=O10/O12 if O12 else 0
    sp=sum(v*gi_l for (g,i,v) in ind if g in alvo and i.startswith('preço do lote médio avos') for gi_l in [sum(v2 for g2,i2,v2 in ind if g2==g and i2.startswith('qdade de lotes avos'))])
    O15=sp/O13 if O13 else 0
    O16=O15*O13/O11 if O11 else 0
    O18=-C('(−) Obras e infraestrutura')*1000
    O19=O18/O10 if O10 else 0; O20=O18/O13 if O13 else 0
    rb=C('Receita bruta de vendas')
    O21=O18/(rb*1000) if rb else 0; O22=1/O21 if O21 else 0
    O24=(C('(=) Receita líquida')+C('(−) Obras e infraestrutura'))/rb if rb else 0
    O25=C('(=) Resultado operacional')/rb if rb else 0
    O26=C('(=) Fluxo antes dos sócios')/rb if rb else 0
    fa=C('(=) Fluxo antes dos sócios')*1000
    O27=fa/O13 if O13 else 0; O28=fa/O11 if O11 else 0
    O30=sum(1 for a in acc if a<0); O31=min(0,min(acc)); O32=fa/-O31 if O31 else 0
    r=irr(ms); O33=((1+r)**12-1) if r is not None else 'n/a'
    O34=sum(v/(1.01)**(i+1) for i,v in enumerate(ms))
    indic=[('PRODUTO',None),('Área líquida vendável – empreendimento (m²)',('n',O10)),('Área líquida vendável – AVOS (m²)',('n',O11)),('Lotes – empreendimento',('n',O12)),('Lotes – AVOS',('n',O13)),
      ('Tamanho médio do lote (m²)',('n',O14)),('Preço médio do lote – AVOS',('r',O15)),('Preço médio do m² – AVOS',('r',O16)),
      ('CUSTO DE OBRA',None),('Custo de obra – empreendimento (100%)',('r',O18)),('Custo de obra por m² vendável',('r',O19)),('Custo de obra por lote – AVOS',('r',O20)),('Custo de obra / VGV',('p',O21)),('VGV / custo de obra',('x',O22)),
      ('RENTABILIDADE',None),('Margem bruta (receita líq. − obra) / receita',('p',O24)),('Margem operacional (EBITDA caixa)',('p',O25)),('Margem antes dos sócios',('p',O26)),('Lucro por lote – AVOS',('r',O27)),('Lucro por m² vendável – AVOS',('r',O28)),
      ('EXPOSIÇÃO E RETORNO',None),('Meses com saldo acumulado negativo',('i',O30)),('Exposição máxima de caixa',('r',O31)),('Lucro sobre exposição máxima',('p',O32)),('TIR anualizada (fluxo antes dos sócios)',('p',O33) if O33!='n/a' else ('t','n/a')),('VPL a 1% a.m.',('r',O34))]
    return dict(linhas=linhas,ind=[[a,b] for a,b in indic],saldo=[[m.strftime('%Y-%m'),v] for m,v in zip(meses,acc)])

def todas(path):
    base,lista,ind=ler(path)
    return {'opcoes':OPCOES,'anos':ANOS,'dados':{o:calcular(base,lista,ind,o) for o in OPCOES}}

if __name__=='__main__':
    import sys,json
    R=todas(sys.argv[1])
    tb=R['dados']['Todos Bambuzal']
    for l in tb['linhas']: print(f"{l['lin'][:34]:34} {l['tot']:12.2f}", [round(x,1) for x in l['anos'][3:]])
    for a,b in tb['ind']: print(a,b)
    for o in R['opcoes']: print(o, round(R['dados'][o]['linhas'][0]['tot'],1), round(R['dados'][o]['linhas'][19]['tot'],1))

# ======================= FLUXO DO GRUPO (Todos) =======================
FCOLS = [('receita','Receita'),('distrato','Distrato'),('impostos','Impostos'),('terreno','Terreno (compra)'),('aprovacao','Aprovação'),('obra','Obra'),
         ('comissao','Comissão Avos'),('marketing','Marketing + Plantão Vendas'),('adm','Administrativo'),('taxa','Taxa administrativa'),('fin','Financeiro'),
         ('aporte_cap','Aporte de capital'),('aporte','Aporte de Sócio'),('retirada','Retirada Sócios'),('lucro_grupo','Lucro grupo'),('lucro_terc','Lucro a Terceiros')]

def fluxo_todos(path):
    base,lista,ind=ler(path)
    areceber=[]; prev=[]; part={}
    with open_workbook(path) as wb:
        with wb.get_sheet('basecontasareceber') as sh:
            for i,row in enumerate(sh.rows()):
                if i==0: continue
                v=[c.v for c in row]+[None]*25
                d=xdate(v[11])
                if d and low(v[20])=='a vencer' and isinstance(v[19],(int,float)): areceber.append((d,float(v[19])))
        with wb.get_sheet('previsão obra bambuzal') as sh:
            for i,row in enumerate(sh.rows()):
                v=[c.v for c in row]+[None]*5
                d=xdate(v[0])
                if d and isinstance(v[1],(int,float)) and low(v[2])=='todos bambuzal': prev.append((d,low(v[3]),float(v[1])))
        with wb.get_sheet('lista depara') as sh:
            for i,row in enumerate(sh.rows()):
                v=[c.v for c in row]+[None]*14
                if i>0 and v[9] and isinstance(v[10],(int,float)): part[str(v[9]).strip().upper()]=float(v[10])
    agg={}
    for d,val,cat,_,_ in base:
        agg[(d.year,d.month,cat)]=agg.get((d.year,d.month,cat),0)+val
    out=[]; d=datetime.date(2019,1,1); saldo=0
    proj_ini=datetime.date(2026,11,1)
    while d<=datetime.date(2042,2,1):
        m={'m':d.strftime('%Y-%m')}
        for k,cat in FCOLS: m[k]=agg.get((d.year,d.month,low(cat)),0.0)
        m['avencer']=sum(v for dd,v in areceber if dd.year==d.year and dd.month==d.month)
        if d>=proj_ini: m['impostos']=-m['avencer']*0.04
        m['obra']+=-sum(v for dd,c,v in prev if dd.year==d.year and dd.month==d.month and c=='obra')
        m['aporte']+=m.pop('aporte_cap')
        rec=m['receita']+m['distrato']+m['avencer']
        cus=sum(m[k] for k in ('impostos','terreno','aprovacao','obra','comissao','marketing','adm','taxa'))
        soc=m['aporte']+m['retirada']+m['lucro_grupo']+m['lucro_terc']
        m['geracao']=rec+cus+m['fin']+soc; saldo+=m['geracao']; m['saldo']=saldo
        out.append(m); d=datetime.date(d.year+(d.month==12),d.month%12+1,1)
    return out, part

# ======================= VGV (Todos) e SÓCIOS (Todos) =======================
import re as _re
def vgv_top_todos(vgv_path, n=10):
    import openpyxl
    wb=openpyxl.load_workbook(vgv_path,data_only=True,read_only=True)
    ws=wb['vendidos']; it=ws.iter_rows(values_only=True); h=list(next(it))
    ip,iv,ic,ik=h.index('Parceiro'),h.index('Valor Negociado'),h.index('Comissão'),h.index('Considerar')
    g={}
    for r in it:
        if not r or r[ip] in (None,'') or r[ik]!=1: continue
        a=g.setdefault(r[ip],[0,0.0,0.0]); a[0]+=1; a[1]+=float(r[iv] or 0); a[2]+=float(r[ic] or 0)
    tot=sum(v[1] for v in g.values())
    top=sorted(g.items(),key=lambda x:-x[1][1])[:n]
    return [[i+1,k,float(v[0]),v[1],v[1]/tot if tot else 0,v[2]/v[1] if v[1] else 0] for i,(k,v) in enumerate(top)]

def vgv_kpi_todos(emp):
    t=next(e for e in emp if e['nome']=='Total')
    return dict(vgv=t['vgv_total'],vendido=t['vgv_vendido'],estoque=t['estoque'],vso=t['vso'],lotes=t['lotes'],pct=t['vgv_vendido']/t['vgv_total'] if t['vgv_total'] else 0,
                disp=t['disp'],vendas90=t['v90'],meses=t['meses'],desc=t['desconto'],inad=t['inad'],areceber=t['areceber'],vendasmes=t['vmes'],comissao=t['com_pct'],
                vencido=t['vencido'],recebido=t['recebido'])

SOC_CATS=['aporte de sócio','retirada sócios','lucro a terceiros']
def socios_todos(path):
    rows=[]; keys=[]
    with open_workbook(path) as wb:
        with wb.get_sheet('BASE PASSADO') as sh:
            for i,row in enumerate(sh.rows()):
                if i==0: continue
                v=[c.v for c in row]+[None]*22
                d=xdate(v[2]); c=low(v[19])
                if d and c in SOC_CATS and isinstance(v[8],(int,float)): rows.append((d.year,c,float(v[8]),str(v[4] or '')))
        with wb.get_sheet('Sócios e Terceiros') as sh:
            for i,row in enumerate(sh.rows()):
                if 9<=i<=25:
                    v={c.c:c.v for c in row}
                    if v.get(1) and v.get(8): keys.append((v[1],v[8]))
    rx=lambda k: _re.compile('^'+'.*'.join(_re.escape(p) for p in str(k).split('*'))+'$' if False else '.*'+'.*'.join(_re.escape(p) for p in str(k).split('*'))+'.*',_re.I|_re.S)
    out=[]; acc=[0,0,0,0]
    for nome,k in keys:
        r=rx(k); s=[0.0,0.0,0.0]; n=0
        for y,c,val,desc in rows:
            if r.match(desc): s[SOC_CATS.index(c)]+=val; n+=1
        out.append([nome,s[0],s[1],s[2],sum(s),n])
    tot=[sum(v for y,c,v,_ in rows if c==cc) for cc in SOC_CATS]
    outros=[tot[i]-sum(o[i+1] for o in out) for i in range(3)]
    out.append(['Outros (fornecedores / demais)',outros[0],outros[1],outros[2],sum(outros),len(rows)-sum(o[5] for o in out)])
    T=sum(tot)
    for o in out: o.insert(5, o[4]/T if T else 0)   # keep shape: nome,ap,ret,luc,liq,%,lanc  -> we only use idx0..4 and 6? adjust below
    out=[[o[0],o[1],o[2],o[3],o[4],o[6]] for o in out]
    anos=sorted({y for y,_,_,_ in rows if y>=2022})
    anual=[sum(v for y,_,v,_ in rows if y==a) for a in anos]
    return out,[tot[0],tot[1],tot[2],T,len(rows)],anos,anual
