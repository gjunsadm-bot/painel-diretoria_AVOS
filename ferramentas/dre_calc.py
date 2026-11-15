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
