import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const FONT_SANS = "'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Inter', system-ui, sans-serif";
const FONT_MONO = "'JetBrains Mono', 'SF Mono', 'Menlo', 'Monaco', monospace";

// Heavy impact frames aligned with 150 BPM bars (1 beat = 24f, 1 bar = 96f)
const IMPACT_FRAMES = [0, 96, 192, 480, 576, 768, 1056, 1200, 1344, 1440];

function useCameraImpact(frame: number) {
  // Subtle pulse on every beat (every 24 frames)
  const beatPhase = (frame % 24) / 24;
  const beatBoost = Math.exp(-beatPhase * 7) * 0.014;

  // Heavy camera shake & flash on major scene/drop hits
  let shakeIntensity = 0;
  let flashOpacity = 0;
  for (const hit of IMPACT_FRAMES) {
    const dt = frame - hit;
    if (dt >= 0 && dt < 22) {
      const decay = Math.exp(-dt / 4.5);
      shakeIntensity = Math.max(shakeIntensity, decay * 22);
      flashOpacity = Math.max(flashOpacity, Math.exp(-dt / 3.0) * 0.65);
    }
  }

  const dx = Math.sin(frame * 2.7) * Math.cos(frame * 1.9) * shakeIntensity;
  const dy = Math.cos(frame * 3.3) * Math.sin(frame * 2.1) * shakeIntensity;
  const rot = Math.sin(frame * 4.1) * (shakeIntensity * 0.06);
  const scale = 1 + beatBoost + (shakeIntensity > 2 ? 0.025 : 0);

  return { dx, dy, rot, scale, flashOpacity, shakeIntensity };
}

// Background 3D Cyber Grid + Energy Aura + Audio Spectrum Bar
const CyberStageBackground: React.FC<{ accentColor?: string; dangerMode?: boolean }> = ({
  accentColor = '#00F0FF',
  dangerMode = false,
}) => {
  const frame = useCurrentFrame();
  const gridOffset = (frame * 8) % 80;
  const primaryGlow = dangerMode ? '#FF0044' : accentColor;
  const secondaryGlow = dangerMode ? '#FF6600' : '#FF0055';

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#05050A',
        overflow: 'hidden',
        fontFamily: FONT_SANS,
      }}
    >
      {/* Deep Radial Neon Glows */}
      <div
        style={{
          position: 'absolute',
          inset: -200,
          background: `
            radial-gradient(circle at ${50 + Math.sin(frame * 0.04) * 18}% ${35 + Math.cos(frame * 0.03) * 12}%, ${primaryGlow}33 0%, transparent 52%),
            radial-gradient(circle at ${25 + Math.cos(frame * 0.05) * 15}% 80%, ${secondaryGlow}28 0%, transparent 48%),
            radial-gradient(circle at 85% 20%, #7000FF25 0%, transparent 45%)
          `,
        }}
      />

      {/* 3D Perspective Moving Floor Grid */}
      <div
        style={{
          position: 'absolute',
          left: '-30%',
          right: '-30%',
          bottom: '-35%',
          height: '85%',
          transform: 'perspective(550px) rotateX(68deg)',
          backgroundImage: `
            linear-gradient(to right, ${primaryGlow}30 2px, transparent 2px),
            linear-gradient(to bottom, ${primaryGlow}30 2px, transparent 2px)
          `,
          backgroundSize: '80px 80px',
          backgroundPosition: `0px ${gridOffset}px`,
          maskImage: 'linear-gradient(to top, rgba(0,0,0,1) 20%, rgba(0,0,0,0) 95%)',
          WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,1) 20%, rgba(0,0,0,0) 95%)',
        }}
      />

      {/* Bottom Audio Visualizer Bars (Beat Synced) */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 70,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          padding: '0 24px',
          opacity: 0.42,
          gap: 6,
        }}
      >
        {Array.from({ length: 64 }).map((_, i) => {
          const beatEnv = Math.exp(-((frame % 24) / 5.5));
          const wave =
            Math.abs(Math.sin(i * 0.45 + frame * 0.28)) * 0.65 +
            Math.abs(Math.cos(i * 0.9 - frame * 0.42)) * 0.35;
          const h = Math.max(6, (wave * 38 + beatEnv * 32) * (i % 4 === 0 ? 1.25 : 0.85));
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: h,
                borderRadius: '3px 3px 0 0',
                background: i % 3 === 0 ? primaryGlow : secondaryGlow,
                boxShadow: `0 0 12px ${primaryGlow}`,
              }}
            />
          );
        })}
      </div>

      {/* Subtle CRT Scanlines */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px, transparent 1px, transparent 4px)',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};

// Reusable Top Tactical Header for Hack Scenes
const TacticalHeader: React.FC<{
  code: string;
  title: string;
  subtitle: string;
  accent: string;
}> = ({ code, title, subtitle, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 220, mass: 0.7 } });

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '36px 64px 20px 64px',
        transform: `translateY(${interpolate(enter, [0, 1], [-60, 0])}px)`,
        opacity: enter,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
        <div
          style={{
            background: accent,
            color: '#05050A',
            fontFamily: FONT_MONO,
            fontWeight: 900,
            fontSize: 28,
            padding: '8px 20px',
            borderRadius: 8,
            boxShadow: `0 0 28px ${accent}`,
            letterSpacing: 1.5,
          }}
        >
          {code}
        </div>
        <div>
          <div
            style={{
              color: '#FFFFFF',
              fontSize: 48,
              fontWeight: 900,
              letterSpacing: -0.5,
              textShadow: `0 0 24px ${accent}88`,
            }}
          >
            {title}
          </div>
          <div
            style={{
              color: accent,
              fontFamily: FONT_MONO,
              fontSize: 20,
              fontWeight: 700,
              marginTop: 4,
              letterSpacing: 0.8,
            }}
          >
            {subtitle}
          </div>
        </div>
      </div>

      <div
        style={{
          border: `2px solid ${accent}88`,
          background: 'rgba(8, 12, 24, 0.85)',
          padding: '10px 22px',
          borderRadius: 10,
          fontFamily: FONT_MONO,
          color: '#E2E8F0',
          fontSize: 18,
          fontWeight: 700,
          boxShadow: `inset 0 0 18px ${accent}33`,
        }}
      >
        KILLTHEHW ENGINE // ACTIVE ⚡
      </div>
    </div>
  );
};

// ============================================================================
// SCENE 1 (0..192f | 0.0s..3.2s): THE NIGHTMARE -> THE SLASH DROP
// ============================================================================
const Scene1NightmareSlash: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const isSlashed = frame >= 96;

  const painCards = [
    {
      start: 0,
      tag: 'PAIN #01 // 时间黑洞',
      title: '实验代码 10 分钟跑完，Word 贴图调格式 3 小时？！',
      desc: '来回切窗口截图 40 次 · 调宋体小四 · 1.5倍行距 · 改到凌晨三点',
      rotate: -3.5,
      top: 120,
      left: 130,
    },
    {
      start: 24,
      tag: 'PAIN #02 // 教务处 2003 祖传模板.docx',
      title: '一粘贴文字：封面下划线飞出天际，合并单元格当场炸裂！',
      desc: 'W:tbl 嵌套八层奇葩表格 · 手动敲空格对齐 · 跨 WPS/Office 打开全乱',
      rotate: 2.8,
      top: 390,
      left: 260,
    },
    {
      start: 48,
      tag: 'PAIN #03 // 通用 AI 灾难级套话',
      title: '“综上所述，通过本次实验我深刻领悟了架构之美...”',
      desc: '狂抄 Conv2d 张量维度 + 八百字排比句感悟 ──► 助教 0.5 秒看穿直接判 0 分！',
      rotate: -1.8,
      top: 660,
      left: 160,
    },
  ];

  // Slash animation at frame 96
  const slashProgress = spring({
    frame: Math.max(0, frame - 96),
    fps,
    config: { damping: 12, stiffness: 280, mass: 0.6 },
  });

  const heroScale = spring({
    frame: Math.max(0, frame - 98),
    fps,
    config: { damping: 11, stiffness: 240, mass: 0.8 },
  });

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor="#00F0FF" dangerMode={!isSlashed} />

      {/* Phase A: Nightmare Cards (split apart after frame 96!) */}
      {painCards.map((c, idx) => {
        const appear = spring({
          frame: Math.max(0, frame - c.start),
          fps,
          config: { damping: 12, stiffness: 300, mass: 0.6 },
        });
        if (frame < c.start) return null;

        const splitDir = idx % 2 === 0 ? -1 : 1;
        const flyOutX = isSlashed ? splitDir * slashProgress * 1600 : 0;
        const flyOutY = isSlashed ? (idx - 1) * slashProgress * 500 : 0;
        const flyRot = isSlashed ? c.rotate + splitDir * slashProgress * 35 : c.rotate;
        const cardOpacity = isSlashed ? interpolate(frame, [96, 118], [1, 0], { extrapolateRight: 'clamp' }) : 1;

        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              top: c.top,
              left: c.left,
              width: 1460,
              padding: '28px 42px',
              background: 'linear-gradient(135deg, rgba(40, 8, 18, 0.96), rgba(18, 5, 10, 0.96))',
              border: '3px solid #FF1E56',
              borderRadius: 18,
              boxShadow: '0 24px 60px rgba(255, 0, 68, 0.45), inset 0 0 30px rgba(255, 30, 86, 0.25)',
              transform: `translate(${flyOutX}px, ${flyOutY}px) scale(${interpolate(appear, [0, 1], [1.6, 1])}) rotate(${flyRot}deg)`,
              opacity: cardOpacity,
            }}
          >
            <div
              style={{
                display: 'inline-block',
                background: '#FF1E56',
                color: '#FFFFFF',
                fontFamily: FONT_MONO,
                fontWeight: 900,
                fontSize: 20,
                padding: '4px 14px',
                borderRadius: 6,
                marginBottom: 10,
              }}
            >
              {c.tag}
            </div>
            <div style={{ color: '#FFFFFF', fontSize: 44, fontWeight: 900, letterSpacing: -0.5 }}>
              {c.title}
            </div>
            <div style={{ color: '#FDA4AF', fontSize: 24, fontWeight: 600, marginTop: 8, fontFamily: FONT_MONO }}>
              {c.desc}
            </div>
          </div>
        );
      })}

      {/* Phase B: Frame 96 SLASH & HERO REVEAL */}
      {isSlashed && (
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          {/* Laser Slash Beam */}
          <div
            style={{
              position: 'absolute',
              width: 2600,
              height: interpolate(frame, [96, 125], [26, 3], { extrapolateRight: 'clamp' }),
              background: '#FFFFFF',
              boxShadow: '0 0 60px 20px #00F0FF, 0 0 120px 40px #FF0055',
              transform: 'rotate(-14deg)',
              opacity: interpolate(frame, [96, 145], [1, 0.25], { extrapolateRight: 'clamp' }),
            }}
          />

          {/* Top Tag */}
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: 28,
              fontWeight: 900,
              color: '#00F0FF',
              letterSpacing: 6,
              padding: '10px 32px',
              border: '2px solid #00F0FF',
              borderRadius: 999,
              background: 'rgba(0, 240, 255, 0.12)',
              boxShadow: '0 0 40px rgba(0, 240, 255, 0.5)',
              transform: `scale(${heroScale})`,
              marginBottom: 24,
            }}
          >
            AGENT SKILL NUCLEAR WEAPON // 终结实验报告内耗
          </div>

          {/* Giant Chromatic Title */}
          <div style={{ position: 'relative', transform: `scale(${interpolate(heroScale, [0, 1], [2.4, 1])})` }}>
            {/* Red Ghost */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                fontSize: 188,
                fontWeight: 900,
                fontFamily: FONT_MONO,
                color: '#FF0055',
                letterSpacing: -6,
                transform: `translate(${Math.sin(frame * 0.8) * 8}px, -4px)`,
                opacity: 0.75,
                mixBlendMode: 'screen',
              }}
            >
              KILL THE HW
            </div>
            {/* Cyan Ghost */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                fontSize: 188,
                fontWeight: 900,
                fontFamily: FONT_MONO,
                color: '#00F0FF',
                letterSpacing: -6,
                transform: `translate(${-Math.sin(frame * 0.8) * 8}px, 4px)`,
                opacity: 0.75,
                mixBlendMode: 'screen',
              }}
            >
              KILL THE HW
            </div>
            {/* Main Crisp White Core */}
            <div
              style={{
                position: 'relative',
                fontSize: 188,
                fontWeight: 900,
                fontFamily: FONT_MONO,
                color: '#FFFFFF',
                letterSpacing: -6,
                textShadow: '0 0 50px rgba(0, 240, 255, 0.85), 0 12px 40px rgba(0,0,0,0.9)',
              }}
            >
              KILL THE HW
            </div>
          </div>

          {/* Explosive Chinese Subtitle */}
          <div
            style={{
              marginTop: 18,
              fontSize: 54,
              fontWeight: 900,
              color: '#FFFFFF',
              background: 'linear-gradient(90deg, #FF0055, #7000FF, #00F0FF)',
              padding: '14px 48px',
              borderRadius: 14,
              boxShadow: '0 18px 50px rgba(255, 0, 85, 0.5)',
              transform: `translateY(${interpolate(heroScale, [0, 1], [80, 0])}px)`,
            }}
          >
            捅穿 V8 虚拟机 · CoreGraphics 显存直抽 · OpenXML 基因夺舍
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 2 (192..480f | 3.2s..8.0s): V8 GHOST PROTOCOL (vscode_headless.py)
// ============================================================================
const Scene2V8Ghost: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const steps = [
    {
      delay: 12,
      cmd: 'ps -eo pid,command | grep "--inspect-port=0"',
      out: '──► 锁定目标工作区 PID: 48291 [Code Helper (Plugin)]',
      color: '#38BDF8',
    },
    {
      delay: 54,
      cmd: 'os.kill(48291, signal.SIGUSR1)',
      out: '──► 发射 Unix 信号强行唤醒隐藏 V8 Inspector: ws://127.0.0.1:9229',
      color: '#F43F5E',
    },
    {
      delay: 96,
      cmd: 'socket.sendall(RFC6455_Frame[0x81 | 0x80] + Runtime.evaluate)',
      out: '──► 零第三方库依赖！纯手搓二进制掩码帧直连 V8 内存缓存提取 vscode 实例',
      color: '#A855F7',
    },
    {
      delay: 138,
      cmd: 'vscode.window.showTextDocument() && terminal.sendText("python train.py")',
      out: '──► 后台幽灵打开代码、清除选区残影、拉起内置 PTY 跑完实验！',
      color: '#10B981',
    },
  ];

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor="#00F0FF" />
      <TacticalHeader
        code="HACK 01"
        title="V8 虚拟机内存级夺舍 · 零焦点后台幽灵操控"
        subtitle="scripts/vscode_headless.py // SIGUSR1 + Raw RFC6455 WebSocket Injection"
        accent="#00F0FF"
      />

      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          gap: 36,
          padding: '12px 64px 48px 64px',
          height: 820,
        }}
      >
        {/* Left Column: User Foreground Status (Zero Interruption) */}
        <div
          style={{
            position: 'relative',
            flex: 0.95,
            background: 'rgba(10, 18, 32, 0.94)',
            border: '2.5px solid #10B981',
            borderRadius: 20,
            padding: 32,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 20px 60px rgba(16, 185, 129, 0.28)',
          }}
        >
          <div>
            <div
              style={{
                display: 'inline-block',
                background: 'rgba(16, 185, 129, 0.2)',
                border: '1.5px solid #10B981',
                color: '#34D399',
                fontFamily: FONT_MONO,
                fontWeight: 800,
                fontSize: 18,
                padding: '6px 16px',
                borderRadius: 8,
                marginBottom: 18,
              }}
            >
              前台用户状态 // 100% 无感打游戏/刷推
            </div>
            <div style={{ color: '#FFFFFF', fontSize: 38, fontWeight: 900, lineHeight: 1.25 }}>
              告别 <span style={{ color: '#F43F5E', textDecoration: 'line-through' }}>PyAutoGUI 乱晃鼠标</span>
              <br />
              告别 <span style={{ color: '#F43F5E', textDecoration: 'line-through' }}>osascript 弹窗抢焦点</span>
            </div>
          </div>

          {/* Giant Zero-Focus Gauges */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {[
              { label: '窗口焦点抢占 (FOCUS STEALING)', val: '0.00%', badge: 'ZERO INTERRUPT' },
              { label: '鼠标与键盘劫持 (INPUT HIJACK)', val: '0 ms', badge: 'GHOST MODE' },
              { label: '系统剪贴板污染 (CLIPBOARD)', val: '0 Bytes', badge: 'NO PBCOPY' },
            ].map((item, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(5, 10, 20, 0.85)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  borderRadius: 14,
                  padding: '18px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ color: '#94A3B8', fontFamily: FONT_MONO, fontSize: 16, fontWeight: 700 }}>
                    {item.label}
                  </div>
                  <div
                    style={{
                      color: '#10B981',
                      fontFamily: FONT_MONO,
                      fontSize: 15,
                      fontWeight: 800,
                      marginTop: 4,
                    }}
                  >
                    ● {item.badge}
                  </div>
                </div>
                <div
                  style={{
                    color: '#FFFFFF',
                    fontFamily: FONT_MONO,
                    fontSize: 44,
                    fontWeight: 900,
                    textShadow: '0 0 20px #10B981',
                  }}
                >
                  {item.val}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Live V8 Inspector Exploit Chain */}
        <div
          style={{
            flex: 1.35,
            background: 'rgba(8, 12, 24, 0.95)',
            border: '2px solid #00F0FF',
            borderRadius: 20,
            padding: 32,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 20px 60px rgba(0, 240, 255, 0.25)',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ color: '#00F0FF', fontFamily: FONT_MONO, fontSize: 20, fontWeight: 900 }}>
              ⚡ V8 EXTENSION HOST MEMORY INJECTION CHAIN
            </div>
            <div
              style={{
                background: '#F43F5E',
                color: '#FFF',
                fontFamily: FONT_MONO,
                fontSize: 16,
                fontWeight: 900,
                padding: '4px 12px',
                borderRadius: 6,
              }}
            >
              SIGUSR1 ARMED
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 12 }}>
            {steps.map((s, i) => {
              const sSpring = spring({
                frame: Math.max(0, frame - s.delay),
                fps,
                config: { damping: 14, stiffness: 220 },
              });
              return (
                <div
                  key={i}
                  style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    borderLeft: `6px solid ${s.color}`,
                    borderRadius: '0 12px 12px 0',
                    padding: '16px 22px',
                    transform: `translateX(${interpolate(sSpring, [0, 1], [120, 0])}px)`,
                    opacity: sSpring,
                    boxShadow: `0 8px 25px ${s.color}22`,
                  }}
                >
                  <div
                    style={{
                      color: '#F8FAFC',
                      fontFamily: FONT_MONO,
                      fontSize: 22,
                      fontWeight: 800,
                    }}
                  >
                    <span style={{ color: s.color }}>[STEP 0{i + 1}]</span> {s.cmd}
                  </div>
                  <div
                    style={{
                      color: '#CBD5E1',
                      fontSize: 21,
                      fontWeight: 700,
                      marginTop: 6,
                    }}
                  >
                    {s.out}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Simulated Background Terminal Output Bar */}
          <div
            style={{
              background: '#020617',
              border: '1px solid #334155',
              borderRadius: 12,
              padding: '14px 20px',
              fontFamily: FONT_MONO,
              fontSize: 18,
              color: '#34D399',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>
              $ python3 cnn_experiment.py ──► Epoch 10/10 | Loss: 0.184 | Test Acc: 91.42%
            </span>
            <span style={{ color: '#00F0FF', fontWeight: 900 }}>[SILENT PTY READY]</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 3 (480..768f | 8.0s..12.8s): COREGRAPHICS RETINA VRAM EXTRACTION
// ============================================================================
const Scene3CoreGraphicsRetina: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const revealRetina = spring({
    frame: Math.max(0, frame - 45),
    fps,
    config: { damping: 13, stiffness: 200 },
  });

  const scanY = interpolate(frame % 96, [0, 96], [0, 100]);

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor="#F59E0B" />
      <TacticalHeader
        code="HACK 02"
        title="手撕 macOS WindowServer · 穿透台前调度 3D 畸变"
        subtitle="scripts/capture_window.py // CoreGraphics.framework + kCGWindowImageBestResolution"
        accent="#F59E0B"
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'stretch',
          gap: 32,
          padding: '12px 64px 48px 64px',
          height: 820,
        }}
      >
        {/* Left: Broken Stage Manager 3D Skewed Thumbnail */}
        <div
          style={{
            flex: 0.78,
            background: 'rgba(30, 10, 16, 0.9)',
            border: '2px dashed #F43F5E',
            borderRadius: 20,
            padding: 28,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'relative',
          }}
        >
          <div style={{ width: '100%' }}>
            <div style={{ color: '#F43F5E', fontFamily: FONT_MONO, fontSize: 20, fontWeight: 900 }}>
              ❌ 传统 screencapture -l &lt;WindowID&gt;
            </div>
            <div style={{ color: '#FDA4AF', fontSize: 26, fontWeight: 800, marginTop: 6 }}>
              开启台前调度 (Stage Manager) 后：
            </div>
          </div>

          {/* 3D Skewed Tiny Blurry Window */}
          <div
            style={{
              width: 300,
              height: 340,
              background: '#1E293B',
              border: '3px solid #64748B',
              borderRadius: 14,
              transform: 'perspective(380px) rotateY(34deg) skewY(-10deg) scale(0.88)',
              filter: 'blur(2.2px)',
              padding: 18,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '-25px 30px 40px rgba(0,0,0,0.8)',
            }}
          >
            <div style={{ color: '#94A3B8', fontFamily: FONT_MONO, fontSize: 16 }}>
              280 × 334 px (缩略图)
            </div>
            <div style={{ color: '#64748B', fontFamily: FONT_MONO, fontSize: 13 }}>
              def model():
              <br />
              &nbsp;&nbsp;# 糊成马赛克
              <br />
              &nbsp;&nbsp;conv = nn.Conv2d(...)
            </div>
            <div style={{ color: '#F43F5E', fontFamily: FONT_MONO, fontSize: 15, fontWeight: 800 }}>
              3D Matrix Warped!
            </div>
          </div>

          {/* Rejected Stamp */}
          <div
            style={{
              position: 'absolute',
              top: '48%',
              border: '6px solid #FF0044',
              color: '#FF0044',
              fontFamily: FONT_MONO,
              fontSize: 42,
              fontWeight: 900,
              padding: '8px 26px',
              borderRadius: 12,
              transform: 'rotate(-16deg)',
              background: 'rgba(20, 0, 5, 0.88)',
              boxShadow: '0 0 35px rgba(255,0,68,0.6)',
            }}
          >
            3D 倾斜畸变废片
          </div>

          <div
            style={{
              color: '#FECDD3',
              fontSize: 20,
              fontWeight: 700,
              textAlign: 'center',
            }}
          >
            窗口退居后台侧边栏时被施加 3D 变换，常规截图直接报废
          </div>
        </div>

        {/*Right: CoreGraphics Native Retina Backing Store Extraction */}
        <div
          style={{
            flex: 1.45,
            background: 'rgba(10, 16, 28, 0.96)',
            border: '3px solid #F59E0B',
            borderRadius: 20,
            padding: 32,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 20px 70px rgba(245, 158, 11, 0.28)',
            transform: `scale(${interpolate(revealRetina, [0, 1], [0.92, 1])})`,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Laser Scanbar */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: `${scanY}%`,
              height: 4,
              background: '#F59E0B',
              boxShadow: '0 0 30px 8px #F59E0B',
              pointerEvents: 'none',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ color: '#F59E0B', fontFamily: FONT_MONO, fontSize: 20, fontWeight: 900 }}>
                ✅ KillTheHW 显存帧缓冲直抽 (Backing Store Direct Read)
              </div>
              <div style={{ color: '#FFFFFF', fontSize: 36, fontWeight: 900, marginTop: 4 }}>
                哪怕窗口被压在八层底下，照样静默抽出满血原画！
              </div>
            </div>
            <div
              style={{
                background: '#F59E0B',
                color: '#05050A',
                fontFamily: FONT_MONO,
                fontSize: 28,
                fontWeight: 900,
                padding: '10px 22px',
                borderRadius: 12,
                boxShadow: '0 0 30px #F59E0B',
              }}
            >
              2940 × 1846 PX
            </div>
          </div>

          {/* Crisp Captured IDE Window Preview */}
          <div
            style={{
              background: '#0F172A',
              border: '2px solid #38BDF8',
              borderRadius: 14,
              padding: 24,
              fontFamily: FONT_MONO,
              boxShadow: '0 12px 40px rgba(0,0,0,0.7)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                borderBottom: '1px solid #334155',
                paddingBottom: 12,
                marginBottom: 14,
                color: '#38BDF8',
                fontSize: 18,
                fontWeight: 800,
              }}
            >
              <span>● ● ●  VS Code — lab2_cnn_fashion.py (Off-screen Backing Store)</span>
              <span style={{ color: '#10B981' }}>0% SHADOW | 0° SKEW | RETINA 2X</span>
            </div>
            <div style={{ color: '#E2E8F0', fontSize: 20, lineHeight: 1.55 }}>
              <span style={{ color: '#F472B6' }}>ctypes</span>.cdll.LoadLibrary(
              <span style={{ color: '#A7F3D0' }}>'CoreGraphics.framework/CoreGraphics'</span>)<br />
              cg.<span style={{ color: '#38BDF8', fontWeight: 900 }}>CGWindowListCreateImage</span>(
              CGRectNull, kCGWindowListOptionIncludingWindow, win_id,<br />
              &nbsp;&nbsp;<span style={{ color: '#FBBF24', fontWeight: 900 }}>
                kCGWindowImageBoundsIgnoreFraming | kCGWindowImageBestResolution
              </span>
              )
            </div>
            <div
              style={{
                marginTop: 14,
                background: '#020617',
                padding: '12px 18px',
                borderRadius: 8,
                color: '#34D399',
                fontSize: 18,
                fontWeight: 700,
              }}
            >
              [TERMINAL OUTPUT] Fashion-MNIST CNN Test Accuracy: 91.68% ──► Evidence Bound to REQ-02
            </div>
          </div>

          {/* Bottom Metric Badges */}
          <div style={{ display: 'flex', gap: 18 }}>
            {[
              '绕过 Stage Manager 3D 变换矩阵',
              '自动剔除 macOS 窗口毛玻璃阴影',
              '智能锁定主文档窗口 (拒绝悬浮小条)',
            ].map((t, idx) => (
              <div
                key={idx}
                style={{
                  flex: 1,
                  background: 'rgba(245, 158, 11, 0.14)',
                  border: '1px solid #F59E0B',
                  borderRadius: 10,
                  padding: '12px 16px',
                  color: '#FDE68A',
                  fontSize: 20,
                  fontWeight: 800,
                  textAlign: 'center',
                }}
              >
                ⚡ {t}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 4 (768..1056f | 12.8s..17.6s): OPENXML AST CLONING (build_report.py)
// ============================================================================
const Scene4OpenXMLClone: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pulse = Math.sin(frame * 0.25) * 0.5 + 0.5;
  const cardEnter = spring({ frame, fps, config: { damping: 14, stiffness: 200 } });

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor="#A855F7" />
      <TacticalHeader
        code="HACK 03"
        title="OpenXML 语法树夺舍 · 100% 像素级克隆往期排版"
        subtitle='scripts/build_report.py // "style_from": "REF:P0007" + Dual-Font XML Injection'
        accent="#A855F7"
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 28,
          padding: '12px 64px 48px 64px',
          height: 820,
          transform: `scale(${interpolate(cardEnter, [0, 1], [0.92, 1])})`,
        }}
      >
        {/* Left: Reference Past A+ Report */}
        <div
          style={{
            flex: 1,
            height: '100%',
            background: 'rgba(18, 12, 36, 0.94)',
            border: '2px solid #A855F7',
            borderRadius: 20,
            padding: 30,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ color: '#C084FC', fontFamily: FONT_MONO, fontSize: 19, fontWeight: 900 }}>
              SOURCE // 往期满分报告 (reference_docx)
            </div>
            <div style={{ color: '#FFFFFF', fontSize: 34, fontWeight: 900, marginTop: 6 }}>
              直接扒下底层 XML 基因节点
            </div>
          </div>

          <div
            style={{
              background: '#090514',
              border: '1px solid #7E22CE',
              borderRadius: 14,
              padding: 22,
              fontFamily: FONT_MONO,
              fontSize: 19,
              color: '#E9D5FF',
              lineHeight: 1.65,
            }}
          >
            <div style={{ color: '#F472B6', fontWeight: 800 }}>&lt;w:p id="REF:P0007"&gt;</div>
            <div>&nbsp;&nbsp;&lt;w:pPr&gt;</div>
            <div style={{ color: '#38BDF8' }}>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;w:spacing w:line="360" w:after="0"/&gt;
            </div>
            <div style={{ color: '#38BDF8' }}>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;w:ind w:firstLineChars="200"/&gt;
            </div>
            <div>&nbsp;&nbsp;&lt;/w:pPr&gt;</div>
            <div>&nbsp;&nbsp;&lt;w:rPr&gt;</div>
            <div style={{ color: '#34D399', fontWeight: 800 }}>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;w:rFonts w:eastAsia="宋体"
              <br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;w:ascii="Times New Roman"/&gt;
            </div>
            <div style={{ color: '#FBBF24' }}>&nbsp;&nbsp;&nbsp;&nbsp;&lt;w:sz w:val="24"/&gt; &lt;!-- 小四 --&gt;</div>
            <div>&nbsp;&nbsp;&lt;/w:rPr&gt;</div>
            <div style={{ color: '#F472B6', fontWeight: 800 }}>&lt;/w:p&gt;</div>
          </div>

          <div
            style={{
              background: 'rgba(168, 85, 247, 0.18)',
              borderRadius: 12,
              padding: '14px 20px',
              color: '#F3E8FF',
              fontSize: 21,
              fontWeight: 800,
            }}
          >
            🧬 严禁 AI 瞎猜 Calibri！原封不动克隆你平时的排版基因
          </div>
        </div>

        {/* Center: DNA Clone Conduit */}
        <div
          style={{
            width: 220,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 18,
          }}
        >
          <div
            style={{
              background: 'linear-gradient(135deg, #A855F7, #EC4899)',
              color: '#FFFFFF',
              fontFamily: FONT_MONO,
              fontWeight: 900,
              fontSize: 22,
              padding: '16px 20px',
              borderRadius: 16,
              textAlign: 'center',
              boxShadow: `0 0 ${30 + pulse * 25}px #A855F7`,
            }}
          >
            style_from:
            <br />
            "REF:P0007"
          </div>
          <div style={{ fontSize: 56, color: '#00F0FF', textShadow: '0 0 25px #00F0FF' }}>
            ══►
          </div>
          <div
            style={{
              background: 'rgba(0, 240, 255, 0.14)',
              border: '1.5px solid #00F0FF',
              color: '#00F0FF',
              fontFamily: FONT_MONO,
              fontSize: 16,
              fontWeight: 800,
              padding: '10px 14px',
              borderRadius: 10,
              textAlign: 'center',
            }}
          >
            SHA-256 模板锁
            <br />
            B0003 / CELL0004
          </div>
        </div>

        {/* Right: Target Ancient School Template Perfectly Preserved */}
        <div
          style={{
            flex: 1.15,
            height: '100%',
            background: 'rgba(10, 20, 32, 0.95)',
            border: '3px solid #00F0FF',
            borderRadius: 20,
            padding: 30,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 20px 60px rgba(0, 240, 255, 0.25)',
          }}
        >
          <div>
            <div style={{ color: '#00F0FF', fontFamily: FONT_MONO, fontSize: 19, fontWeight: 900 }}>
              TARGET // 教务处祖传模板.docx ──► 零损保版成品
            </div>
            <div style={{ color: '#FFFFFF', fontSize: 34, fontWeight: 900, marginTop: 6 }}>
              封面下划线不歪 · 合并单元格不炸
            </div>
          </div>

          {/* Simulated Crisp DOCX Page */}
          <div
            style={{
              background: '#F8FAFC',
              color: '#0F172A',
              borderRadius: 12,
              padding: '22px 28px',
              boxShadow: '0 10px 30px rgba(0,0,0,0.6)',
            }}
          >
            <div
              style={{
                borderBottom: '2px solid #0F172A',
                paddingBottom: 8,
                marginBottom: 12,
                display: 'flex',
                justifyContent: 'space-between',
                fontWeight: 900,
                fontSize: 20,
              }}
            >
              <span>《深度学习与计算机视觉》实验报告</span>
              <span style={{ color: '#0284C7', fontFamily: FONT_MONO }}>CELL0004 [LOCKED]</span>
            </div>
            <div style={{ fontSize: 19, lineHeight: 1.6, fontWeight: 600, color: '#1E293B' }}>
              <strong>一、实验内容与结果：</strong>
              <br />
              先导入相关库划分 Fashion-MNIST 数据集，搭建多层感知机并加入 Dropout 缓解过拟合，随后改用卷积神经网络对比测试准确率。
            </div>
            <div
              style={{
                marginTop: 12,
                background: '#0F172A',
                color: '#38BDF8',
                padding: '12px 16px',
                borderRadius: 8,
                fontFamily: FONT_MONO,
                fontSize: 16,
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>[RETINA SCREENSHOT #1: MLP Acc 87.3%]</span>
              <span style={{ color: '#34D399' }}>WIDTH: 14.0 CM</span>
            </div>
            <div
              style={{
                marginTop: 6,
                background: '#0F172A',
                color: '#A7F3D0',
                padding: '12px 16px',
                borderRadius: 8,
                fontFamily: FONT_MONO,
                fontSize: 16,
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>[RETINA SCREENSHOT #2: CNN Acc 91.6%]</span>
              <span style={{ color: '#FBBF24' }}>无缝上下连贴 · 无斜体图注</span>
            </div>
          </div>

          <div
            style={{
              background: 'rgba(16, 185, 129, 0.18)',
              border: '1.5px solid #10B981',
              borderRadius: 12,
              padding: '12px 20px',
              color: '#6EE7B7',
              fontSize: 20,
              fontWeight: 800,
              textAlign: 'center',
            }}
          >
            ✅ 跨 macOS Office / Windows Word / WPS 打开 100% 字体不降级
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 5 (1056..1344f | 17.6s..22.4s): ANTI-SLOP SUBTRACTION + RUBRIC AUDIT
// ============================================================================
const Scene5AntiSlopAndAudit: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const showAudit = frame >= 144; // At 1200f global (1056 + 144 = 1200)

  const auditEnter = spring({
    frame: Math.max(0, frame - 144),
    fps,
    config: { damping: 12, stiffness: 240, mass: 0.7 },
  });

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor={showAudit ? '#10B981' : '#FF0055'} />
      <TacticalHeader
        code={showAudit ? 'HACK 05' : 'HACK 04'}
        title={
          showAudit
            ? '助教视角 Rubric 铁腕审计 + 进程级防休眠锁'
            : '反 AI 侦测终极奥义：真实大学生「偷懒减法法则」'
        }
        subtitle={
          showAudit
            ? 'scripts/check_deliverables.py + caffeinate_guard // 零漏题 · 零扣分交付'
            : 'references/writing-style.md // 字数强对齐 · 绝不复读代码参数 · 80字大白话体会'
        }
        accent={showAudit ? '#10B981' : '#FF0055'}
      />

      <div style={{ padding: '12px 64px 48px 64px', height: 820, position: 'relative' }}>
        {/* Part A: Anti-Slop Subtraction Comparison */}
        <div
          style={{
            display: 'flex',
            gap: 32,
            height: '100%',
            opacity: showAudit ? 0.12 : 1,
            filter: showAudit ? 'blur(8px)' : 'none',
            transition: 'opacity 0.2s',
          }}
        >
          {/* Left: Crushed AI Slop */}
          <div
            style={{
              flex: 1,
              background: 'rgba(40, 8, 20, 0.92)',
              border: '2px solid #F43F5E',
              borderRadius: 20,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ color: '#F43F5E', fontFamily: FONT_MONO, fontSize: 22, fontWeight: 900 }}>
              🚫 严厉禁止的「AI 教科书废话味」
            </div>
            <div
              style={{
                background: 'rgba(0,0,0,0.55)',
                padding: 24,
                borderRadius: 14,
                color: '#FDA4AF',
                fontSize: 24,
                lineHeight: 1.6,
                textDecoration: 'line-through',
              }}
            >
              “第一层采用 Conv2d(1, 32, kernel_size=3, padding=1) 配合 BatchNorm2d 将特征图下采样至 (32, 14, 14)……综上所述，通过局部感受野和权重共享，我深刻领悟了平移不变性的架构之美……”
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                '❌ 傻瓜式复读截图里已有的代码参数与张量维度',
                '❌ 字数膨胀到 800 字（往期报告明明只有 350 字）',
                '❌ 画蛇添足加 Word 斜体图注下标「图 2-16 xxx」',
              ].map((t, i) => (
                <div
                  key={i}
                  style={{
                    background: 'rgba(244, 63, 94, 0.15)',
                    padding: '12px 18px',
                    borderRadius: 10,
                    color: '#FFE4E6',
                    fontSize: 21,
                    fontWeight: 700,
                  }}
                >
                  {t}
                </div>
              ))}
            </div>
          </div>

          {/* Right: Authentic Student Subtraction Law */}
          <div
            style={{
              flex: 1.15,
              background: 'rgba(8, 24, 20, 0.95)',
              border: '3px solid #10B981',
              borderRadius: 20,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 20px 60px rgba(16, 185, 129, 0.25)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ color: '#10B981', fontFamily: FONT_MONO, fontSize: 22, fontWeight: 900 }}>
                ✅ KillTheHW「偷懒减法红线」
              </div>
              <div
                style={{
                  background: '#10B981',
                  color: '#05050A',
                  fontFamily: FONT_MONO,
                  fontWeight: 900,
                  fontSize: 20,
                  padding: '6px 16px',
                  borderRadius: 8,
                }}
              >
                往期 350 字 ──► 本次 342 字
              </div>
            </div>

            <div
              style={{
                background: '#051814',
                border: '1.5px solid #10B981',
                padding: 24,
                borderRadius: 14,
                color: '#ECFDF5',
                fontSize: 26,
                fontWeight: 700,
                lineHeight: 1.6,
              }}
            >
              “在服装数据集中用 MLP 模型能把准确率做到 87% 左右，加入 Dropout 可以缓解过拟合。换成 CNN 模型后准确率提升至 91% 以上，分类效果明显更好。”
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                '⚡ 字数强对齐往期报告：多写一句废话直接砍！',
                '⚡ 代码已经在图里了：正文 1~2 句大白话直接甩截图！',
                '⚡ 对比图直接上下连贴 + 实验体会严格锁死 2 句话 80 字以内！',
              ].map((t, i) => (
                <div
                  key={i}
                  style={{
                    background: 'rgba(16, 185, 129, 0.16)',
                    padding: '12px 18px',
                    borderRadius: 10,
                    color: '#A7F3D0',
                    fontSize: 21,
                    fontWeight: 800,
                  }}
                >
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Part B: Frame 1200+ Holographic Rubric Audit & Caffeinate Guard Overlay */}
        {showAudit && (
          <AbsoluteFill
            style={{
              justifyContent: 'center',
              alignItems: 'center',
              padding: '0 64px 40px 64px',
            }}
          >
            <div
              style={{
                width: '100%',
                height: '100%',
                background: 'linear-gradient(135deg, rgba(6, 22, 18, 0.97), rgba(8, 15, 28, 0.98))',
                border: '3px solid #10B981',
                borderRadius: 24,
                padding: '38px 48px',
                boxShadow: '0 30px 100px rgba(16, 185, 129, 0.45)',
                transform: `scale(${interpolate(auditEnter, [0, 1], [1.35, 1])})`,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ color: '#34D399', fontFamily: FONT_MONO, fontSize: 22, fontWeight: 900 }}>
                    DELIVERABLE PRE-FLIGHT AUDIT // 助教视角终审报告
                  </div>
                  <div style={{ color: '#FFFFFF', fontSize: 46, fontWeight: 900, marginTop: 4 }}>
                    把指导书角落里每一个扣分点，在交作业前彻底按死！
                  </div>
                </div>
                <div
                  style={{
                    background: '#10B981',
                    color: '#04120C',
                    fontFamily: FONT_MONO,
                    fontSize: 42,
                    fontWeight: 900,
                    padding: '14px 32px',
                    borderRadius: 16,
                    boxShadow: '0 0 40px #10B981',
                  }}
                >
                  AUDIT: 100 / 100
                </div>
              </div>

              {/* SHA-256 Real-time Evidence Verification Matrix Bar */}
              <div
                style={{
                  background: 'rgba(4, 18, 12, 0.92)',
                  border: '1.5px solid #10B981',
                  borderRadius: 14,
                  padding: '18px 28px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  boxShadow: 'inset 0 0 25px rgba(16, 185, 129, 0.25)',
                }}
              >
                <div style={{ fontFamily: FONT_MONO, fontSize: 20, color: '#A7F3D0', fontWeight: 800 }}>
                  ⚡ SHA-256 EVIDENCE CHAIN // job.json ⇄ template-map.json ⇄ output_report.docx
                </div>
                <div style={{ fontFamily: FONT_MONO, fontSize: 20, color: '#00F0FF', fontWeight: 900 }}>
                  [████████████████████ 100% VERIFIED]
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22 }}>
                {[
                  {
                    k: '必答小问与思考题覆盖率',
                    v: '6 / 6 全部命中 (100%)',
                    d: '自动扫描指导书角落隐蔽思考题，杜绝漏题白扣 20 分',
                  },
                  {
                    k: '截图证据链 SHA-256 绑定',
                    v: '8 张 Retina 原图已验真',
                    d: '题号、命令输出与报告章节一对一哈希锁死，拒绝张冠李戴',
                  },
                  {
                    k: 'caffeinate 防休眠守护进程',
                    v: 'caffeinate -dimsu -w <PID>',
                    d: '跑长实验自动挂系统电源断言防锁屏中断，任务结束即焚',
                  },
                  {
                    k: '模板残留与排版红线核验',
                    v: '0 占位符残留 / 0 表格溢出',
                    d: '自动清除“请在此处填写”提示词，检验图片尺寸与分页边界',
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    style={{
                      background: 'rgba(15, 35, 28, 0.88)',
                      border: '1.5px solid rgba(16, 185, 129, 0.5)',
                      borderRadius: 16,
                      padding: '22px 28px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#94A3B8', fontFamily: FONT_MONO, fontSize: 19, fontWeight: 800 }}>
                        {item.k}
                      </span>
                      <span style={{ color: '#34D399', fontFamily: FONT_MONO, fontSize: 22, fontWeight: 900 }}>
                        ✅ {item.v}
                      </span>
                    </div>
                    <div style={{ color: '#F8FAFC', fontSize: 23, fontWeight: 700, marginTop: 10 }}>
                      {item.d}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </AbsoluteFill>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 6 (1344..1536f | 22.4s..25.6s): GRAND FINALE
// ============================================================================
const Scene6GrandFinale: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const boom = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 240, mass: 0.8 },
  });

  return (
    <AbsoluteFill>
      <CyberStageBackground accentColor="#00F0FF" />

      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 80px',
        }}
      >
        {/* Three Workflow Mode Pills */}
        <div
          style={{
            display: 'flex',
            gap: 24,
            marginBottom: 36,
            transform: `translateY(${interpolate(boom, [0, 1], [-60, 0])}px)`,
          }}
        >
          {[
            { m: 'MODE 01', t: '整理与保版装配', c: '#00F0FF' },
            { m: 'MODE 02', t: '全流程静默运行取证', c: '#FF0055' },
            { m: 'MODE 03', t: '助教级预检与审计', c: '#10B981' },
          ].map((item, i) => (
            <div
              key={i}
              style={{
                background: 'rgba(10, 16, 30, 0.92)',
                border: `2.5px solid ${item.c}`,
                borderRadius: 14,
                padding: '14px 28px',
                boxShadow: `0 0 30px ${item.c}44`,
                display: 'flex',
                alignItems: 'center',
                gap: 14,
              }}
            >
              <span style={{ color: item.c, fontFamily: FONT_MONO, fontSize: 22, fontWeight: 900 }}>
                {item.m}
              </span>
              <span style={{ color: '#FFFFFF', fontSize: 24, fontWeight: 900 }}>{item.t}</span>
            </div>
          ))}
        </div>

        {/* Slogan Line 1 */}
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 64,
            fontWeight: 900,
            color: '#94A3B8',
            letterSpacing: 2,
            transform: `scale(${interpolate(boom, [0, 1], [1.4, 1])})`,
          }}
        >
          DON&apos;T FORMAT HOMEWORK.
        </div>

        {/* Massive Slogan Line 2 */}
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 184,
            fontWeight: 900,
            color: '#FFFFFF',
            letterSpacing: -6,
            lineHeight: 1.05,
            textShadow: '0 0 60px #00F0FF, 0 0 120px #FF0055',
            transform: `scale(${interpolate(boom, [0, 1], [2.2, 1])})`,
            marginTop: 6,
          }}
        >
          KILL THE HW.
        </div>

        {/* Chinese Tagline */}
        <div
          style={{
            marginTop: 28,
            fontSize: 42,
            fontWeight: 900,
            color: '#05050A',
            background: 'linear-gradient(90deg, #00F0FF, #38BDF8, #A855F7, #FF0055)',
            padding: '14px 52px',
            borderRadius: 999,
            boxShadow: '0 0 50px rgba(0, 240, 255, 0.6)',
          }}
        >
          把垃圾排版时间碾碎 · 把生命还给真正的代码与创造 ⚡
        </div>

        {/* Footer Tech Stack Signature */}
        <div
          style={{
            marginTop: 42,
            fontFamily: FONT_MONO,
            fontSize: 22,
            fontWeight: 700,
            color: '#64748B',
            letterSpacing: 3,
          }}
        >
          AGENT SKILL // V8 INSPECTOR · COREGRAPHICS RETINA · POSIX PTY · OPENXML AST
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================================
// MASTER COMPOSITION WITH CAMERA SHAKE & AUDIO
// ============================================================================
export const PromoVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { dx, dy, rot, scale, flashOpacity } = useCameraImpact(frame);

  return (
    <AbsoluteFill style={{ backgroundColor: '#05050A', overflow: 'hidden' }}>
      <Audio src={staticFile('soundtrack.mp3')} volume={1} />

      <AbsoluteFill
        style={{
          transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg) scale(${scale})`,
          transformOrigin: 'center center',
        }}
      >
        <Sequence from={0} durationInFrames={192}>
          <Scene1NightmareSlash />
        </Sequence>

        <Sequence from={192} durationInFrames={288}>
          <Scene2V8Ghost />
        </Sequence>

        <Sequence from={480} durationInFrames={288}>
          <Scene3CoreGraphicsRetina />
        </Sequence>

        <Sequence from={768} durationInFrames={288}>
          <Scene4OpenXMLClone />
        </Sequence>

        <Sequence from={1056} durationInFrames={288}>
          <Scene5AntiSlopAndAudit />
        </Sequence>

        <Sequence from={1344} durationInFrames={192}>
          <Scene6GrandFinale />
        </Sequence>
      </AbsoluteFill>

      {/* High-Impact Beat Drop Flash Overlay */}
      {flashOpacity > 0.01 && (
        <AbsoluteFill
          style={{
            background: 'radial-gradient(circle, rgba(255,255,255,0.95) 0%, rgba(0,240,255,0.5) 60%, transparent 100%)',
            opacity: flashOpacity,
            pointerEvents: 'none',
            mixBlendMode: 'screen',
          }}
        />
      )}
    </AbsoluteFill>
  );
};
