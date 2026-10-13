#!/usr/bin/env python3
"""
Generate a high-impact, frame-accurate 150 BPM Cyberpunk Industrial Bass / Phonk Trap
soundtrack for the KillTheHW Remotion promo video.
Duration: 25.6 seconds (1536 frames @ 60fps, 16 bars @ 150 BPM).
1 beat = 0.4s (24 frames), 1 bar = 1.6s (96 frames).
"""
import math
from pathlib import Path
import subprocess
import wave
import numpy as np

SR = 44100
DURATION = 25.6  # 16 bars at 150 BPM (1.6s per bar)
N_SAMPLES = int(SR * DURATION)
BPM = 150.0
BEAT_SEC = 60.0 / BPM        # 0.4s (24 frames @ 60fps)
BAR_SEC = BEAT_SEC * 4       # 1.6s (96 frames @ 60fps)


def midi_to_freq(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def add_stereo(mix_l: np.ndarray, mix_r: np.ndarray, sig_l: np.ndarray, sig_r: np.ndarray, start_sec: float):
    idx = int(start_sec * SR)
    if idx < 0:
        sig_l = sig_l[-idx:]
        sig_r = sig_r[-idx:]
        idx = 0
    end = min(N_SAMPLES, idx + len(sig_l))
    length = end - idx
    if length > 0:
        mix_l[idx:end] += sig_l[:length]
        mix_r[idx:end] += sig_r[:length]


def synth_kick(dur=0.32, punch=1.4):
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    # Fast pitch drop from 210Hz -> 55Hz -> 38Hz
    freq = 38.0 + 172.0 * np.exp(-t * 48.0) + 22.0 * np.exp(-t * 10.0)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 7.5)
    # Transient click
    click = np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 140.0) * 0.45
    sig = np.tanh((body + click) * punch * 1.8) * 0.95
    return sig, sig


def synth_snare(dur=0.22):
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    # Tonal body
    f_body = 180.0 + 140.0 * np.exp(-t * 45.0)
    tonal = np.sin(2 * np.pi * np.cumsum(f_body) / SR) * np.exp(-t * 22.0) * 0.7
    # Crispy stereo noise
    rng_l = np.random.default_rng(int(dur * 1000) + 1)
    rng_r = np.random.default_rng(int(dur * 1000) + 2)
    noise_l = rng_l.standard_normal(n) * np.exp(-t * 15.0) * 0.65
    noise_r = rng_r.standard_normal(n) * np.exp(-t * 15.0) * 0.65
    sig_l = np.tanh((tonal + noise_l) * 1.9) * 0.75
    sig_r = np.tanh((tonal + noise_r) * 1.9) * 0.75
    return sig_l, sig_r


def synth_hihat(dur=0.06, amp=0.28, pan=0.0):
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    rng = np.random.default_rng(int(dur * 10000 + amp * 100))
    # Metallic high-frequency FM + noise
    carriers = (
        np.sin(2 * np.pi * 6300 * t)
        + np.sin(2 * np.pi * 8750 * t)
        + np.sin(2 * np.pi * 11200 * t)
        + rng.standard_normal(n) * 1.2
    )
    env = np.exp(-t * (45.0 / max(dur, 0.03) * 0.06))
    sig = np.diff(carriers, prepend=0) * env * amp * 0.35
    l_gain = math.cos((pan + 1) * math.pi / 4)
    r_gain = math.sin((pan + 1) * math.pi / 4)
    return sig * l_gain, sig * r_gain


def synth_reese_bass(midi_note: float, dur: float, drive=2.5):
    """Heavy Cyberpunk distorted Reese + 808 Sub bass."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    f0 = midi_to_freq(midi_note)
    # Sub fundamental
    sub = np.sin(2 * np.pi * f0 * t) * 0.9
    # Detuned sawtooth pair for wide aggressive grit
    f_l = f0 * 0.993
    f_r = f0 * 1.007
    saw_l = 2.0 * ((t * f_l) % 1.0) - 1.0
    saw_r = 2.0 * ((t * f_r) % 1.0) - 1.0
    # Low-pass envelope simulation via harmonics + saturation
    harm_env = 0.35 + 0.65 * np.exp(-t * 6.0)
    env = np.ones(n)
    fade_in = min(int(0.008 * SR), n)
    fade_out = min(int(0.03 * SR), n)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    sig_l = np.tanh((sub + saw_l * 0.55 * harm_env) * drive) * env * 0.62
    sig_r = np.tanh((sub + saw_r * 0.55 * harm_env) * drive) * env * 0.62
    return sig_l, sig_r


def synth_phonk_lead(midi_note: float, dur: float, accent=1.0):
    """Aggressive Phonk Cowbell / Cyberpunk Brass Lead."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    f1 = midi_to_freq(midi_note)
    f2 = f1 * 1.498  # Classic 5th/cowbell metallic ratio
    # Pitch attack envelope
    p_env = 1.0 + 0.08 * np.exp(-t * 90.0)
    p1 = 2 * np.pi * np.cumsum(f1 * p_env) / SR
    p2 = 2 * np.pi * np.cumsum(f2 * p_env) / SR

    sq1 = np.sign(np.sin(p1)) * 0.6 + np.sin(p1) * 0.5
    sq2 = np.sign(np.sin(p2)) * 0.35 + np.sin(p1 * 2.003) * 0.4
    env = np.exp(-t * 11.0)
    attack = min(int(0.003 * SR), n)
    env[:attack] = np.linspace(0, 1, attack)

    raw_l = np.tanh((sq1 + sq2 * 0.8) * 2.4) * env * 0.38 * accent
    # Slight stereo Haas delay (12 samples)
    raw_r = np.roll(raw_l, 18) * 0.98
    return raw_l, raw_r


def synth_braaam_impact(dur=1.4, base_freq=55.0):
    """Massive cinematic trailer impact / Braaam hit for scene transitions."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    # Pitch drop sub
    f_sub = base_freq * (0.65 + 0.85 * np.exp(-t * 5.0))
    sub = np.sin(2 * np.pi * np.cumsum(f_sub) / SR) * np.exp(-t * 2.5)
    # Massive brassy detuned saws (D1, D2, A2, D3, F3)
    freqs = [base_freq, base_freq * 2, base_freq * 3, base_freq * 4, base_freq * 4.756]
    brass_l = np.zeros(n)
    brass_r = np.zeros(n)
    for i, f in enumerate(freqs):
        det = 1.0 + (i - 2) * 0.004
        saw_l = 2.0 * ((t * f * det) % 1.0) - 1.0
        saw_r = 2.0 * ((t * f / det) % 1.0) - 1.0
        brass_l += saw_l * (0.4 / (i + 1))
        brass_r += saw_r * (0.4 / (i + 1))
    # Metallic impact crash at start
    rng = np.random.default_rng(42)
    crash = rng.standard_normal(n) * np.exp(-t * 14.0) * 0.5
    env = np.exp(-t * 2.2)
    sig_l = np.tanh((sub * 1.1 + brass_l * 1.3 + crash) * 2.2) * env * 0.80
    sig_r = np.tanh((sub * 1.1 + brass_r * 1.3 - crash) * 2.2) * env * 0.80
    return sig_l, sig_r


def synth_riser(dur=1.2):
    """High-tension cyberpunk pitch + filter riser before scene drops."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    progress = (t / dur) ** 2.2
    f_l = 140.0 + 1800.0 * progress
    f_r = 143.0 + 1850.0 * progress
    osc_l = np.sin(2 * np.pi * np.cumsum(f_l) / SR) + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(f_l * 1.5) / SR))
    osc_r = np.sin(2 * np.pi * np.cumsum(f_r) / SR) + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(f_r * 1.5) / SR))
    rng = np.random.default_rng(99)
    noise = rng.standard_normal(n) * 0.35 * progress
    env = progress * np.sin(2 * np.pi * 12.0 * t * progress + 1.0) * 0.3 + progress * 0.7
    return (osc_l * 0.25 + noise) * env * 0.55, (osc_r * 0.25 - noise) * env * 0.55


def synth_glitch_burst(dur=0.12):
    """Digital data-burst / bitcrush glitch sound for code/terminal animations."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    # Rapidly stepping square wave
    steps = np.floor(t * 95.0)
    freqs = 400.0 + ((steps * 7919) % 2400.0)
    phase = 2 * np.pi * np.cumsum(freqs) / SR
    sig = np.sign(np.sin(phase)) * np.exp(-t * 12.0) * 0.32
    return sig, -sig * 0.9


def main():
    mix_l = np.zeros(N_SAMPLES, dtype=np.float64)
    mix_r = np.zeros(N_SAMPLES, dtype=np.float64)

    # Major Scene Cut Timestamps (in bars, 1 bar = 1.6s = 96 frames @ 60fps):
    # Bar 0 (0.0s, f=0): Intro Nightmare alarm
    # Bar 2 (3.2s, f=192): DROP 1 - KILL THE HW Title Slash!
    # Bar 4 (6.4s -> actually let's align with Scene cuts):
    # Let's check Scene exact bars:
    # Scene 1: Bar 0..2 (0.0s - 3.2s, f 0..192) -> Bar 1 (1.6s, f=96) is THE SLASH DROP!
    # Scene 2 (V8 Ghost): Bar 2..5 (3.2s - 8.0s, f 192..480)
    # Scene 3 (CoreGraphics Retina): Bar 5..8 (8.0s - 12.8s, f 480..768)
    # Scene 4 (OpenXML Clone): Bar 8..11 (12.8s - 17.6s, f 768..1056)
    # Scene 5 (Anti-Slop & Rubric Audit): Bar 11..14 (17.6s - 22.4s, f 1056..1344)
    # Scene 6 (Grand Finale): Bar 14..16 (22.4s - 25.6s, f 1344..1536)

    impact_bars = [0, 1, 2, 5, 8, 11, 14]
    for b in impact_bars:
        t_hit = b * BAR_SEC
        imp_l, imp_r = synth_braaam_impact(dur=1.3, base_freq=36.71 if b > 0 else 55.0)  # D1 = 36.71Hz
        add_stereo(mix_l, mix_r, imp_l, imp_r, t_hit)
        if b > 0:
            ris_l, ris_r = synth_riser(dur=0.8)
            add_stereo(mix_l, mix_r, ris_l, ris_r, t_hit - 0.8)

    # Bar 0 (0.0s - 1.6s): Tension Intro Alarm & Fast Build-up
    for step in range(8):
        t_step = step * (BEAT_SEC / 2.0)
        # Alarm pulse (D5 / Eb5 dissonance)
        lead_l, lead_r = synth_phonk_lead(74 if step % 2 == 0 else 75, dur=0.16, accent=0.85)
        add_stereo(mix_l, mix_r, lead_l, lead_r, t_step)
        if step >= 4:
            k_l, k_r = synth_kick(dur=0.18, punch=1.5)
            add_stereo(mix_l, mix_r, k_l, k_r, t_step)

    # Rapid snare roll before Bar 1 Slash (1.2s - 1.6s)
    for i in range(4):
        s_l, s_r = synth_snare(dur=0.12)
        add_stereo(mix_l, mix_r, s_l * (0.5 + 0.15 * i), s_r * (0.5 + 0.15 * i), 1.2 + i * 0.1)

    # Main High-Energy Cyberpunk Phonk / Industrial Drop: Bars 1 to 15 (1.6s to 25.6s)
    # Riff in D Phrygian (D=62, Eb=63, F=65, G=67, A=69, Bb=70, C=72, D5=74)
    riff_pattern = [
        # (offset_in_beats, midi_note, dur_beats, accent)
        (0.0, 62, 0.5, 1.2),   # D4
        (0.5, 62, 0.5, 0.9),   # D4
        (1.0, 65, 0.5, 1.1),   # F4
        (1.5, 63, 0.5, 1.0),   # Eb4
        (2.0, 62, 0.75, 1.2),  # D4
        (2.75, 60, 0.5, 0.95), # C4
        (3.25, 63, 0.375, 1.1),# Eb4
        (3.625, 62, 0.375, 1.0)# D4
    ]
    riff_pattern_alt = [
        (0.0, 74, 0.5, 1.3),   # D5 high energy
        (0.5, 74, 0.5, 0.95),
        (1.0, 77, 0.5, 1.2),   # F5
        (1.5, 75, 0.5, 1.15),  # Eb5
        (2.0, 74, 0.5, 1.25),  # D5
        (2.5, 70, 0.5, 1.1),   # Bb4
        (3.0, 69, 0.5, 1.15),  # A4
        (3.5, 63, 0.5, 1.2),   # Eb4
    ]

    bass_notes_by_bar = [
        38,  # Bar 0 (unused here)
        26,  # Bar 1: D1 (36.7Hz)
        26,  # Bar 2: D1
        29,  # Bar 3: F1
        27,  # Bar 4: Eb1
        26,  # Bar 5: D1 (Scene 3)
        26,  # Bar 6: D1
        31,  # Bar 7: G1
        27,  # Bar 8: Eb1 (Scene 4)
        26,  # Bar 9: D1
        29,  # Bar 10: F1
        26,  # Bar 11: D1 (Scene 5)
        34,  # Bar 12: Bb1
        33,  # Bar 13: A1
        26,  # Bar 14: D1 (Scene 6 Finale)
        26,  # Bar 15: D1
    ]

    for bar in range(1, 16):
        bar_start = bar * BAR_SEC
        bass_midi = bass_notes_by_bar[bar] + 12  # D2 range for fundamental + sub

        # 1. Heavy Reese/808 Bassline per bar
        bass_hits = [(0.0, 1.5), (1.5, 1.0), (2.5, 1.5)]
        for b_off, b_dur in bass_hits:
            bl, br = synth_reese_bass(bass_midi, b_dur * BEAT_SEC, drive=2.6)
            add_stereo(mix_l, mix_r, bl, br, bar_start + b_off * BEAT_SEC)

        # 2. Kick & Snare Pattern (Hard-hitting halftime / driving hybrid)
        # Kicks on 0.0, 0.75, 1.5, 2.5, 3.25
        kick_beats = [0.0, 0.75, 1.5, 2.5, 3.25] if bar % 2 == 1 else [0.0, 1.5, 2.25, 2.75, 3.5]
        for kb in kick_beats:
            kl, kr = synth_kick(dur=0.28, punch=1.55)
            add_stereo(mix_l, mix_r, kl, kr, bar_start + kb * BEAT_SEC)

        # Snare on Beat 1.0 and Beat 3.0 (2 and 4 in 4/4)
        for sb in [1.0, 3.0]:
            sl, sr = synth_snare(dur=0.22)
            add_stereo(mix_l, mix_r, sl, sr, bar_start + sb * BEAT_SEC)

        # 3. Trap Hi-Hat 16th + 32nd Rolls
        for sixteenth in range(16):
            t_hh = bar_start + sixteenth * (BEAT_SEC / 4.0)
            pan = 0.35 * math.sin(sixteenth * 1.1)
            if sixteenth in (6, 7, 14, 15) and bar % 2 == 0:
                # 32nd note triplet roll!
                for sub_h in range(2):
                    hl, hr = synth_hihat(dur=0.035, amp=0.24, pan=-pan)
                    add_stereo(mix_l, mix_r, hl, hr, t_hh + sub_h * (BEAT_SEC / 8.0))
            else:
                hl, hr = synth_hihat(dur=0.055 if sixteenth % 2 == 0 else 0.04, amp=0.30 if sixteenth % 2 == 0 else 0.18, pan=pan)
                add_stereo(mix_l, mix_r, hl, hr, t_hh)

        # 4. Cyberpunk Phonk Lead Riff
        pattern = riff_pattern_alt if bar in (3, 6, 9, 12, 14, 15) else riff_pattern
        for r_off, r_midi, r_dur, r_acc in pattern:
            ll, lr = synth_phonk_lead(r_midi, r_dur * BEAT_SEC * 0.92, accent=r_acc)
            add_stereo(mix_l, mix_r, ll, lr, bar_start + r_off * BEAT_SEC)

        # 5. Digital Glitch Bursts on sub-beats inside technical scenes
        if bar in (2, 3, 5, 7, 8, 10, 11, 13):
            gl, gr = synth_glitch_burst(dur=0.10)
            add_stereo(mix_l, mix_r, gl, gr, bar_start + 1.75 * BEAT_SEC)

    # Final massive hit at 24.0s (Bar 15) with resonant tail to 25.6s
    fin_l, fin_r = synth_braaam_impact(dur=1.55, base_freq=36.71)
    add_stereo(mix_l, mix_r, fin_l * 1.2, fin_r * 1.2, 15 * BAR_SEC)

    # Master Bus Limiter & Soft Clipper
    stereo = np.stack([mix_l, mix_r], axis=-1)
    peak = np.max(np.abs(stereo))
    if peak > 0:
        stereo = stereo / peak
    # Warm master saturation + ceiling at -0.3 dBFS
    stereo = np.tanh(stereo * 1.65) / np.tanh(1.65) * 0.96

    out_dir = Path(__file__).resolve().parent / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_wav = out_dir / "soundtrack_raw.wav"
    final_mp3 = out_dir / "soundtrack.mp3"

    pcm16 = (stereo * 32767.0).astype(np.int16)
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm16.tobytes())

    # Polish through FFmpeg mastering chain (Sub boost, crisp highs, punchy compressor)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav),
        "-af", "equalizer=f=55:width_type=o:width=1.2:g=3.5,equalizer=f=3500:width_type=o:width=1.5:g=2.5,acompressor=threshold=-14dB:ratio=3:attack=5:release=60:makeup=2.5,alimiter=limit=0.95",
        "-b:a", "320k",
        str(final_mp3)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated mastered soundtrack: {final_mp3} ({final_mp3.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
