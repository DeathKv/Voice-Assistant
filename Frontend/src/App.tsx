import { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';

const NOME_INICIAL = import.meta.env.VITE_NOME || 'Aria';

const CORES: Record<string, number> = {
  ouvindo: 0xff3333, pensando: 0xffcc00, falando: 0x00ff99,
  ocioso: 0x3399ff, desconectado: 0x223344, comando: 0xff6600,
};
const CORES_CSS: Record<string, string> = {
  ouvindo: '#ff3333', pensando: '#ffcc00', falando: '#00ff99',
  ocioso: '#3399ff', desconectado: '#223344', comando: '#ff6600',
};
const LABELS: Record<string, string> = {
  ouvindo: 'OUVINDO', pensando: 'PROCESSANDO', falando: 'RESPONDENDO',
  ocioso: 'AGUARDANDO', desconectado: 'DESCONECTADO', comando: 'MODO COMANDO',
};

interface Dados { state: string; usuario: string; aria: string; }

interface CampoConfig {
  label:   string;
  valor:   string;
  tipo:    'text' | 'password' | 'select' | 'range';
  opcoes?: string[];
  min?:    number;
  max?:    number;
}

interface SecaoConfig {
  label:  string;
  campos: Record<string, CampoConfig>;
}

const rand = (a: number, b: number) => Math.random() * (b - a) + a;

function App() {
  const mountRef      = useRef<HTMLDivElement>(null);
  const stateRef      = useRef('desconectado');
  const socketRef     = useRef<WebSocket | null>(null);

  const matsEsfera    = useRef<THREE.MeshStandardMaterial[]>([]);
  const matNucleo     = useRef<THREE.MeshBasicMaterial | null>(null);
  const matsGlow      = useRef<THREE.MeshBasicMaterial[]>([]);
  const matParticulas = useRef<THREE.PointsMaterial | null>(null);
  const matsArcos     = useRef<THREE.MeshBasicMaterial[]>([]);
  const matsRings     = useRef<THREE.MeshBasicMaterial[]>([]);

  const [status,       setStatus]       = useState('desconectado');
  const [dados,        setDados]        = useState<Dados>({ state: 'desconectado', usuario: '', aria: '' });
  const [transcricao,  setTranscricao]  = useState(true);
  const [uptime,       setUptime]       = useState('00:00:00');
  const [hora,         setHora]         = useState('');
  const [nomeExibido,  setNomeExibido]  = useState(NOME_INICIAL);
  const [painelAberto, setPainelAberto] = useState(false);
  const [abaAtiva,     setAbaAtiva]     = useState('assistente');
  const [config,       setConfig]       = useState<Record<string, SecaoConfig>>({});
  const [editando,     setEditando]     = useState<Record<string, string>>({});
  const editandoRef = useRef<Record<string, string>>({});
  const [salvando,     setSalvando]     = useState(false);
  const [mensagemSalvo, setMensagemSalvo] = useState('');

  useEffect(() => {
    editandoRef.current = editando;
  }, [editando]);

  // ── Uptime + Hora ─────────────────────────────────────────────
  useEffect(() => {
    const inicio = Date.now();
    const tick = () => {
      const seg = Math.floor((Date.now() - inicio) / 1000);
      setUptime(`${String(Math.floor(seg/3600)).padStart(2,'0')}:${String(Math.floor((seg%3600)/60)).padStart(2,'0')}:${String(seg%60).padStart(2,'0')}`);
      setHora(new Date().toLocaleTimeString('pt-BR'));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // ── Atualizar cores Three.js ──────────────────────────────────
  const atualizarCores = useCallback((estado: string) => {
    const cor = CORES[estado] ?? CORES['desconectado'];
    matsEsfera.current.forEach(m => { m.color.set(cor); m.emissive.set(cor); });
    matNucleo.current?.color.set(cor);
    matsGlow.current.forEach(m => m.color.set(cor));
    matParticulas.current?.color.set(cor);
    matsArcos.current.forEach(m => m.color.set(cor));
    matsRings.current.forEach(m => m.color.set(cor));
  }, []);

  // ── WebSocket ─────────────────────────────────────────────────
  useEffect(() => {
    let vivo = true;

    const conectar = () => {
      const socket = new WebSocket('ws://localhost:8765');
      socketRef.current = socket;

      socket.onopen = () => {
        setStatus('ocioso'); stateRef.current = 'ocioso'; atualizarCores('ocioso');
      };

      socket.onmessage = (e) => {
        const d = JSON.parse(e.data);

        // Estado da Aria
        if (d.tipo === 'estado') {
          setStatus(d.state); setDados(d);
          stateRef.current = d.state; atualizarCores(d.state);
        }

        // Configurações recebidas do backend
        if (d.tipo === 'config_dados') {
          setConfig(d.config);
          // Popula os campos de edição com os valores atuais
          const vals: Record<string, string> = {};
          Object.values(d.config as Record<string, SecaoConfig>).forEach(secao => {
            Object.entries(secao.campos).forEach(([k, campo]) => {
              vals[k] = (campo as CampoConfig).valor;
            });
          });
          setEditando(vals);
        }

        // Resposta ao salvar
        if (d.tipo === 'config_salva') {
          setSalvando(false);
          setMensagemSalvo(d.sucesso ? '✅ Salvo! Reinicie o backend para aplicar.' : '❌ Erro ao salvar.');
          const nomeAtual = editandoRef.current['NOME_ASSISTENTE'];
          if (d.sucesso && nomeAtual) {
            setNomeExibido(nomeAtual);
          }
          setTimeout(() => setMensagemSalvo(''), 4000);
        }
      };

      socket.onclose = () => {
        setStatus('desconectado'); stateRef.current = 'desconectado'; atualizarCores('desconectado');
        if (vivo) setTimeout(conectar, 2000);
      };
      socket.onerror = () => socket.close();
    };

    conectar();
    return () => { vivo = false; socketRef.current?.close(); };
  }, [atualizarCores]);

  // ── Abrir painel: pede config ao backend ─────────────────────
  const abrirPainel = () => {
    setPainelAberto(true);
    socketRef.current?.send(JSON.stringify({ tipo: 'get_config' }));
  };

  // ── Salvar configurações ──────────────────────────────────────
  const salvarConfig = () => {
    setSalvando(true);
    socketRef.current?.send(JSON.stringify({ tipo: 'save_config', campos: editando }));
  };

  // ── Three.js ──────────────────────────────────────────────────
  useEffect(() => {
    const W = window.innerWidth, H = window.innerHeight;
    const clock = new THREE.Clock();
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, W/H, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    mountRef.current?.appendChild(renderer.domElement);
    camera.position.z = 4.5;

    scene.add(new THREE.AmbientLight(0x0a0a1a, 2));
    const l1 = new THREE.PointLight(0xffffff, 3, 15); l1.position.set(4,4,4); scene.add(l1);
    const l2 = new THREE.PointLight(0x3399ff, 2, 10); l2.position.set(-4,-2,2); scene.add(l2);

    // Estrelas
    const nE = 700, pE = new Float32Array(nE*3);
    for (let i = 0; i < nE*3; i++) pE[i] = rand(-40,40);
    const gE = new THREE.BufferGeometry();
    gE.setAttribute('position', new THREE.BufferAttribute(pE, 3));
    scene.add(new THREE.Points(gE, new THREE.PointsMaterial({
      color:0x446688, size:0.05, transparent:true, opacity:0.5,
      blending:THREE.AdditiveBlending, depthWrite:false,
    })));

    // Grupo esfera
    const grupoEsfera = new THREE.Group();
    scene.add(grupoEsfera);
    matsEsfera.current = [];
    const esferaMeshes: THREE.Mesh[] = [];
    [
      {det:5, esc:1.00, vx: 0.002, vy: 0.004},
      {det:3, esc:0.78, vx:-0.004, vy: 0.002},
      {det:2, esc:0.56, vx: 0.005, vy:-0.003},
    ].forEach(c => {
      const mat = new THREE.MeshStandardMaterial({
        color:CORES['desconectado'], wireframe:true,
        emissive:CORES['desconectado'], emissiveIntensity:0.8,
        transparent:true, opacity:0.9,
      });
      matsEsfera.current.push(mat);
      const m = new THREE.Mesh(new THREE.IcosahedronGeometry(1,c.det), mat);
      m.scale.setScalar(c.esc); m.userData={vx:c.vx, vy:c.vy};
      grupoEsfera.add(m); esferaMeshes.push(m);
    });

    const matCore = new THREE.MeshBasicMaterial({color:CORES['desconectado'],transparent:true,opacity:0.10});
    matNucleo.current = matCore;
    grupoEsfera.add(new THREE.Mesh(new THREE.SphereGeometry(0.42,32,32), matCore));

    matsGlow.current = [];
    [1.22,1.50,1.85].forEach((s,i) => {
      const mat = new THREE.MeshBasicMaterial({
        color:CORES['desconectado'], transparent:true, opacity:0.035-i*0.008,
        side:THREE.BackSide, blending:THREE.AdditiveBlending, depthWrite:false,
      });
      matsGlow.current.push(mat);
      grupoEsfera.add(new THREE.Mesh(new THREE.SphereGeometry(s,16,16), mat));
    });

    // Partículas orbitando
    const nP=500, pP=new Float32Array(nP*3);
    for (let i=0;i<nP;i++){
      const t=rand(0,Math.PI*2), p=Math.acos(2*Math.random()-1), r=rand(2.0,3.5);
      pP[i*3]=r*Math.sin(p)*Math.cos(t); pP[i*3+1]=r*Math.sin(p)*Math.sin(t); pP[i*3+2]=r*Math.cos(p);
    }
    const gP=new THREE.BufferGeometry();
    gP.setAttribute('position',new THREE.BufferAttribute(pP,3));
    const matP=new THREE.PointsMaterial({
      color:CORES['desconectado'],size:0.022,transparent:true,opacity:0.6,
      blending:THREE.AdditiveBlending,depthWrite:false,
    });
    matParticulas.current=matP;
    const particulas=new THREE.Points(gP,matP);
    scene.add(particulas);

    // Arcos HUD
    matsArcos.current=[];
    const grupoArcos=new THREE.Group(); scene.add(grupoArcos);
    [{raio:2.8,tubo:0.005,arco:Math.PI*1.3,vz: 0.006,ix:0.3},
     {raio:3.2,tubo:0.004,arco:Math.PI*0.7,vz:-0.005,ix:1.1},
     {raio:3.6,tubo:0.003,arco:Math.PI*1.6,vz: 0.003,ix:0.7},
    ].forEach(c=>{
      const mat=new THREE.MeshBasicMaterial({
        color:CORES['desconectado'],transparent:true,opacity:0.55,
        blending:THREE.AdditiveBlending,depthWrite:false,
      });
      matsArcos.current.push(mat);
      const m=new THREE.Mesh(new THREE.TorusGeometry(c.raio,c.tubo,8,80,c.arco),mat);
      m.rotation.x=c.ix; m.userData={vz:c.vz}; grupoArcos.add(m);
    });

    // Anéis de onda
    const rings: THREE.Mesh[]=[];
    matsRings.current=[];
    for(let i=0;i<3;i++){
      const mat=new THREE.MeshBasicMaterial({
        color:CORES['desconectado'],transparent:true,opacity:0,
        side:THREE.DoubleSide,blending:THREE.AdditiveBlending,depthWrite:false,
      });
      matsRings.current.push(mat);
      const r=new THREE.Mesh(new THREE.RingGeometry(1.05,1.12,80),mat);
      r.rotation.x=Math.PI/2; scene.add(r); rings.push(r);
    }

    const ringOffsets=[0,0.33,0.66], ringScales=[1,1,1];
    let animId: number;

    const animate=()=>{
      animId=requestAnimationFrame(animate);
      const elapsed=clock.getElapsedTime(), state=stateRef.current;

      const alvo = state==='falando' ? 1+Math.sin(elapsed*8)*0.07 :
        state==='ouvindo' ? 1+Math.sin(elapsed*4)*0.045 :
        state==='pensando' ? 1+Math.sin(elapsed*12)*0.025 :
        state==='comando' ? 1+Math.sin(elapsed*6)*0.055 :
        1+Math.sin(elapsed*1.5)*0.012;
      grupoEsfera.scale.lerp(new THREE.Vector3(alvo,alvo,alvo),0.08);

      esferaMeshes.forEach(m=>{m.rotation.x+=m.userData.vx; m.rotation.y+=m.userData.vy;});
      const ei=state==='falando'?1.4+Math.sin(elapsed*10)*0.4:state==='ouvindo'?1.0+Math.sin(elapsed*3)*0.25:0.7;
      matsEsfera.current.forEach(m=>m.emissiveIntensity=ei);

      particulas.rotation.y+=state==='falando'?0.0025:0.0008;
      particulas.rotation.x+=0.0002;
      grupoArcos.children.forEach(c=>{(c as THREE.Mesh).rotation.z+=(c as THREE.Mesh).userData.vz*(state==='falando'?2.2:1);});

      for(let i=0;i<3;i++){
        if(state==='falando'||state==='ouvindo'){
          const vel=state==='falando'?0.45:0.22;
          const t=((elapsed*vel+ringOffsets[i])%1);
          ringScales[i]=1+t*5; matsRings.current[i].opacity=(1-t)*0.45;
        } else matsRings.current[i].opacity=Math.max(0,matsRings.current[i].opacity-0.015);
        rings[i].scale.setScalar(ringScales[i]);
      }

      camera.position.x=Math.sin(elapsed*0.08)*0.12;
      camera.position.y=Math.cos(elapsed*0.06)*0.08;
      camera.lookAt(0,0,0);
      renderer.render(scene,camera);
    };
    animate();

    const onResize=()=>{
      camera.aspect=window.innerWidth/window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth,window.innerHeight);
    };
    const mountNode = mountRef.current;
    window.addEventListener('resize',onResize);
    return ()=>{
      cancelAnimationFrame(animId);
      window.removeEventListener('resize',onResize);
      if(mountNode?.contains(renderer.domElement)) mountNode.removeChild(renderer.domElement);
      renderer.dispose();
    };
  },[]);

  const cor   = CORES_CSS[status] ?? CORES_CSS['desconectado'];
  const label = LABELS[status]    ?? status.toUpperCase();
  const online = status !== 'desconectado';

  return (
    <div style={{background:'#03050f',width:'100vw',height:'100vh',overflow:'hidden',position:'relative',fontFamily:"'Courier New',monospace"}}>

      {/* Canvas */}
      <div ref={mountRef} style={{position:'absolute',inset:0}} />

      {/* Vignette */}
      <div style={{position:'absolute',inset:0,pointerEvents:'none',
        background:'radial-gradient(ellipse at center,transparent 45%,rgba(0,0,0,0.82) 100%)'}} />

      {/* Scanlines */}
      <div style={{position:'absolute',inset:0,pointerEvents:'none',
        backgroundImage:'repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.06) 2px,rgba(0,0,0,0.06) 4px)'}} />

      {/* Nome + Status (topo centro) */}
      <div style={{position:'absolute',top:36,left:0,right:0,textAlign:'center',pointerEvents:'none'}}>
        <div style={{color:cor,fontSize:28,fontWeight:'bold',letterSpacing:14,
          textShadow:`0 0 24px ${cor}, 0 0 48px ${cor}55`,animation:'pulso 2.5s ease-in-out infinite'}}>
          {nomeExibido.toUpperCase()}
        </div>
        <div style={{color:cor,fontSize:9,letterSpacing:6,opacity:0.65,marginTop:8}}>
          ◈ &nbsp; {label} &nbsp; ◈
        </div>
      </div>

      {/* Canto superior esquerdo */}
      <div style={{position:'absolute',top:24,left:28,pointerEvents:'none',color:'#fff'}}>
        <Bracket cor={cor} pos="top-left" />
        <Row label="HORA"   value={hora}   cor={cor} />
        <Row label="UPTIME" value={uptime} cor={cor} />
        <Row label="STATUS" value={online?'ONLINE':'OFFLINE'} cor={online?'#00ff99':'#ff3333'} />
      </div>

      {/* Canto superior direito */}
      <div style={{position:'absolute',top:24,right:28,textAlign:'right',pointerEvents:'none',color:'#fff'}}>
        <Bracket cor={cor} pos="top-right" />
        <Row label="MODEL"  value="GEMINI-3.8-LIVE" cor={cor} right />
        <Row label="AUDIO"  value="PCM 16/24 KHZ"   cor={cor} right />
        <Row label="MODO"   value={label}            cor={cor} right />
      </div>

      {/* Canto inferior esquerdo */}
      <div style={{position:'absolute',bottom:28,left:28,pointerEvents:'none',color:'#fff'}}>
        <Row label="INPUT"  value="MICROFONE ATIVO" cor={cor} />
        <Row label="OUTPUT" value="ALTO-FALANTE"    cor={cor} />
        <Bracket cor={cor} pos="bottom-left" />
      </div>

      {/* Canto inferior direito */}
      <div style={{position:'absolute',bottom:28,right:28,textAlign:'right'}}>
        {/* Botão transcrição */}
        <BotaoHUD
          ativo={transcricao}
          cor={cor}
          onClick={() => setTranscricao(p=>!p)}
          label={transcricao ? '◉ TRANSCRIÇÃO' : '○ TRANSCRIÇÃO'}
        />
        {/* Botão configurações */}
        <BotaoHUD
          ativo={painelAberto}
          cor={cor}
          onClick={abrirPainel}
          label="⚙ CONFIGURAÇÕES"
        />
        <Bracket cor={cor} pos="bottom-right" />
      </div>

      {/* Barras laterais */}
      {(['left','right'] as const).map(lado=>(
        <div key={lado} style={{
          position:'absolute',[lado]:16,top:'28%',bottom:'28%',
          width:2,background:'#ffffff0a',borderRadius:2,pointerEvents:'none',
        }}>
          <div style={{
            position:'absolute',bottom:0,left:0,right:0,borderRadius:2,
            background:cor,boxShadow:`0 0 8px ${cor}`,transition:'height 0.6s ease',
            height:status==='falando'?'90%':status==='ouvindo'?'60%':status==='pensando'?'35%':status==='comando'?'50%':status==='ocioso'?'15%':'4%',
          }}/>
        </div>
      ))}

      {/* Transcrição */}
      {transcricao&&(dados.usuario||dados.aria)&&(
        <div style={{
          position:'absolute',bottom:72,left:'50%',transform:'translateX(-50%)',
          width:'50%',maxWidth:640,background:'rgba(3,5,18,0.88)',
          border:`1px solid ${cor}28`,borderRadius:10,padding:'14px 22px',
          backdropFilter:'blur(18px)',boxShadow:`0 0 40px ${cor}0e`,animation:'fadeUp 0.3s ease',
        }}>
          <div style={{height:1,marginBottom:12,background:`linear-gradient(90deg,transparent,${cor}66,transparent)`}}/>
          {dados.usuario&&(
            <div style={{marginBottom:dados.aria?10:0}}>
              <span style={{color:cor,fontSize:8,letterSpacing:3,opacity:0.7}}>▶ VOCÊ</span>
              <p style={{color:'#ffffffbb',margin:'4px 0 0',fontSize:13,lineHeight:1.7}}>{dados.usuario}</p>
            </div>
          )}
          {dados.aria&&(
            <div>
              <span style={{color:cor,fontSize:8,letterSpacing:3,opacity:0.7}}>▶ {nomeExibido.toUpperCase()}</span>
              <p style={{color:'#8899aa',margin:'4px 0 0',fontSize:13,lineHeight:1.7}}>{dados.aria}</p>
            </div>
          )}
          <div style={{height:1,marginTop:12,background:`linear-gradient(90deg,transparent,${cor}66,transparent)`}}/>
        </div>
      )}

      {/* ── PAINEL DE CONFIGURAÇÕES ── */}
      {painelAberto&&(
        <div style={{
          position:'absolute',inset:0,
          background:'rgba(0,0,0,0.6)',
          backdropFilter:'blur(8px)',
          display:'flex',alignItems:'center',justifyContent:'center',
          zIndex:100,animation:'fadeIn 0.2s ease',
        }} onClick={()=>setPainelAberto(false)}>
          <div style={{
            background:'rgba(3,6,20,0.97)',
            border:`1px solid ${cor}44`,
            borderRadius:14,
            width:'min(820px,90vw)',
            maxHeight:'80vh',
            overflow:'hidden',
            display:'flex',
            flexDirection:'column',
            boxShadow:`0 0 60px ${cor}22`,
          }} onClick={e=>e.stopPropagation()}>

            {/* Header do painel */}
            <div style={{
              padding:'18px 24px',
              borderBottom:`1px solid ${cor}22`,
              display:'flex',alignItems:'center',justifyContent:'space-between',
            }}>
              <div>
                <div style={{color:cor,fontSize:11,letterSpacing:4}}>⚙ CONFIGURAÇÕES DO SISTEMA</div>
                <div style={{color:'#ffffff44',fontSize:9,letterSpacing:2,marginTop:4}}>
                  Alterações são salvas no .env — reinicie o backend para aplicar
                </div>
              </div>
              <button onClick={()=>setPainelAberto(false)} style={{
                background:'transparent',border:`1px solid ${cor}44`,
                color:cor,fontSize:14,cursor:'pointer',
                borderRadius:6,width:32,height:32,
              }}>✕</button>
            </div>

            <div style={{display:'flex',flex:1,overflow:'hidden'}}>

              {/* Abas laterais */}
              <div style={{
                width:160,borderRight:`1px solid ${cor}22`,
                padding:'12px 0',flexShrink:0,
              }}>
                {Object.entries(config).map(([key, secao])=>(
                  <button key={key} onClick={()=>setAbaAtiva(key)} style={{
                    display:'block',width:'100%',textAlign:'left',
                    padding:'10px 18px',border:'none',cursor:'pointer',
                    fontFamily:'monospace',fontSize:9,letterSpacing:2,
                    background:abaAtiva===key?`${cor}18`:'transparent',
                    color:abaAtiva===key?cor:'#556677',
                    borderLeft:abaAtiva===key?`2px solid ${cor}`:'2px solid transparent',
                    transition:'all 0.2s',
                  }}>
                    {secao.label.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Conteúdo da aba */}
              <div style={{flex:1,overflowY:'auto',padding:'20px 24px'}}>
                {config[abaAtiva]&&(
                  <>
                    <div style={{color:cor,fontSize:10,letterSpacing:3,marginBottom:20}}>
                      {config[abaAtiva].label.toUpperCase()}
                    </div>
                    {Object.entries(config[abaAtiva].campos).map(([chave, campo])=>(
                      <CampoForm
                        key={chave}
                        chave={chave}
                        campo={campo as CampoConfig}
                        valor={editando[chave] ?? (campo as CampoConfig).valor}
                        cor={cor}
                        onChange={(v)=>setEditando(prev=>({...prev,[chave]:v}))}
                      />
                    ))}
                  </>
                )}
              </div>
            </div>

            {/* Footer com botão salvar */}
            <div style={{
              padding:'14px 24px',
              borderTop:`1px solid ${cor}22`,
              display:'flex',alignItems:'center',justifyContent:'space-between',
            }}>
              <div style={{color:mensagemSalvo.includes('✅')?'#00ff99':'#ff4444',fontSize:10,letterSpacing:2}}>
                {mensagemSalvo}
              </div>
              <button onClick={salvarConfig} disabled={salvando} style={{
                background:`${cor}22`,border:`1px solid ${cor}`,
                color:cor,fontFamily:'monospace',fontSize:10,
                letterSpacing:3,padding:'10px 24px',
                cursor:salvando?'wait':'pointer',borderRadius:6,
                opacity:salvando?0.6:1,transition:'all 0.2s',
              }}>
                {salvando?'SALVANDO...':'💾 SALVAR TUDO'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulso { 0%,100%{opacity:1} 50%{opacity:0.72} }
        @keyframes fadeUp { from{opacity:0;transform:translateX(-50%) translateY(10px)} to{opacity:1;transform:translateX(-50%) translateY(0)} }
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        *{box-sizing:border-box;margin:0;padding:0}
        button:hover{filter:brightness(1.3)}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#334;border-radius:2px}
      `}</style>
    </div>
  );
}

// ── Componentes auxiliares ────────────────────────────────────────

function Row({label,value,cor,right}:{label:string;value:string;cor:string;right?:boolean}){
  return(
    <div style={{fontSize:10,letterSpacing:2,marginBottom:4,textAlign:right?'right':'left'}}>
      <span style={{color:'#ffffff44'}}>{label}: </span>
      <span style={{color:cor}}>{value}</span>
    </div>
  );
}

function Bracket({cor,pos}:{cor:string;pos:'top-left'|'top-right'|'bottom-left'|'bottom-right'}){
  const isTop    = pos.includes('top');
  const isLeft   = pos.includes('left');
  return(
    <div style={{
      width:14,height:14,opacity:0.7,
      marginBottom:isTop?10:0,
      marginTop:isTop?0:10,
      marginLeft:isLeft?0:'auto',
      borderTop:   isTop?`2px solid ${cor}`:undefined,
      borderBottom:isTop?undefined:`2px solid ${cor}`,
      borderLeft:  isLeft?`2px solid ${cor}`:undefined,
      borderRight: isLeft?undefined:`2px solid ${cor}`,
    }}/>
  );
}

function BotaoHUD({ativo,cor,onClick,label}:{ativo:boolean;cor:string;onClick:()=>void;label:string}){
  return(
    <button onClick={onClick} style={{
      display:'block',marginBottom:8,marginLeft:'auto',
      background:ativo?`${cor}18`:'rgba(255,255,255,0.03)',
      border:`1px solid ${ativo?cor:'#334'}`,
      borderRadius:6,color:ativo?cor:'#445',
      fontFamily:'monospace',fontSize:9,letterSpacing:2,
      padding:'6px 12px',cursor:'pointer',transition:'all 0.3s',
    }}>
      {label}
    </button>
  );
}

function CampoForm({chave,campo,valor,cor,onChange}:{
  chave:string; campo:CampoConfig; valor:string; cor:string; onChange:(v:string)=>void;
}){
  const baseInput: React.CSSProperties = {
    width:'100%',background:'rgba(255,255,255,0.04)',
    border:`1px solid ${cor}33`,borderRadius:6,
    color:'#ccddee',fontFamily:'monospace',fontSize:11,
    padding:'8px 12px',outline:'none',marginTop:6,
    transition:'border 0.2s',
  };

  return(
    <div style={{marginBottom:20}}>
      <label style={{color:'#8899aa',fontSize:9,letterSpacing:3}}>{campo.label.toUpperCase()}</label>
      <div style={{color:'#ffffff22',fontSize:8,letterSpacing:1,marginTop:2}}>{chave}</div>

      {campo.tipo==='select'&&(
        <select value={valor} onChange={e=>onChange(e.target.value)} style={{...baseInput}}>
          {campo.opcoes?.map(op=><option key={op} value={op} style={{background:'#0a0f1e'}}>{op}</option>)}
        </select>
      )}

      {campo.tipo==='range'&&(
        <div style={{display:'flex',alignItems:'center',gap:12,marginTop:6}}>
          <input type="range" min={campo.min} max={campo.max} value={valor}
            onChange={e=>onChange(e.target.value)}
            style={{flex:1,accentColor:cor}}/>
          <span style={{color:cor,fontSize:11,minWidth:45,textAlign:'right'}}>{valor}</span>
        </div>
      )}

      {(campo.tipo==='text'||campo.tipo==='password')&&(
        <input
          type={campo.tipo}
          value={valor}
          onChange={e=>onChange(e.target.value)}
          style={baseInput}
          onFocus={e=>{e.target.style.borderColor=cor;}}
          onBlur={e=>{e.target.style.borderColor=`${cor}33`;}}
        />
      )}
    </div>
  );
}

export default App;