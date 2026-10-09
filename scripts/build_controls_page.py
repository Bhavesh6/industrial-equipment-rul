import re
import sys

def build_controls_html():
    return '''      <!-- ════════════ SECTION: CONTROLS (HARDWARE CONTROL CENTER) ════════════ -->
      <section class="page-section" id="sec-controls">

        <!-- Top sub-header bar -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
          <div>
            <p style="font-size:.82rem;color:var(--faint);margin:0;display:flex;align-items:center;gap:6px">
              <i data-lucide="sliders" style="width:16px;height:16px;color:var(--accent)"></i>
              Actuator Modulation &bull; Digital Rotary Jog Wheel &bull; Dynamic ACS712 Sensor Calibration Studio
            </p>
          </div>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span class="badge" id="cpageHwBadge" style="background:var(--ok-soft);color:var(--ok);border:1px solid #c3ddcd;font-size:.72rem">
              <span class="live-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--ok);margin-right:4px"></span>
              <span id="cpageHwStatus">COM5 CONNECTED</span>
            </span>
            <span class="badge badge-info" id="cpageDirBadge">FORWARD (CW)</span>
            <span class="status-pill good" id="cpageMotorStatePill">
              <span class="status-dot"></span><span id="cpageMotorStateText">STANDBY</span>
            </span>
          </div>
        </div>

        <!-- ═════════ ROW 1: PRIMARY HARDWARE ACTUATION & JOG WHEEL ═════════ -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(460px, 1fr));gap:20px;margin-bottom:24px">

          <!-- Card 1: KY-040 Digital Rotary Jog Wheel & Stepper Console -->
          <div class="card" style="border-top:3px solid var(--accent);box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="disc"></i> KY-040 Rotary Encoder &amp; Jog Console</span>
              <span class="badge" style="background:var(--surface-alt);color:var(--muted);font-size:.66rem">HARDWARE INTERRUPT (CLK:18, DT:19, SW:23)</span>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:16px">

              <!-- Interactive Jog Wheel SVG Dial -->
              <div style="display:flex;align-items:center;justify-content:center;gap:30px;flex-wrap:wrap">
                <div style="position:relative;width:180px;height:180px;display:flex;align-items:center;justify-content:center">
                  <svg width="180" height="180" viewBox="0 0 180 180" style="transform:rotate(-90deg);overflow:visible">
                    <!-- Background Dial Track -->
                    <circle cx="90" cy="90" r="76" fill="none" stroke="var(--border)" stroke-width="12" stroke-linecap="round" stroke-dasharray="358" stroke-dashoffset="90" />
                    <!-- Active PWM Arc -->
                    <circle id="cpageJogRing" cx="90" cy="90" r="76" fill="none" stroke="var(--accent)" stroke-width="12" stroke-linecap="round"
                            stroke-dasharray="358" stroke-dashoffset="358" style="transition:stroke-dashoffset .2s ease-out;filter:drop-shadow(0 0 4px rgba(217,119,6,0.3))" />
                  </svg>

                  <!-- Rotating Pointer Needle -->
                  <div id="cpageJogNeedle" style="position:absolute;width:100%;height:100%;pointer-events:none;transform:rotate(-135deg);transition:transform .2s ease-out">
                    <div style="position:absolute;top:10px;left:50%;width:4px;height:14px;background:var(--accent);transform:translateX(-50%);border-radius:2px;box-shadow:0 0 6px var(--accent)"></div>
                  </div>

                  <!-- Central Readout Inside Dial -->
                  <div style="position:absolute;text-align:center;display:flex;flex-direction:column;align-items:center">
                    <span class="mono" id="cpageJogPwm" style="font-size:2.2rem;font-weight:900;color:var(--ink);line-height:1">0</span>
                    <span style="font-size:.65rem;font-weight:700;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-top:2px">PWM / 255</span>
                    <span class="badge badge-info mono" id="cpageJogPct" style="font-size:.7rem;margin-top:4px;padding:2px 6px">0%</span>
                  </div>
                </div>

                <!-- Live Electrical Drive Metrics -->
                <div style="display:flex;flex-direction:column;gap:10px;min-width:180px">
                  <div style="padding:10px 14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                    <div style="font-size:.65rem;font-weight:700;color:var(--faint);text-transform:uppercase">Terminal Drive Voltage</div>
                    <div class="mono" id="cpageJogVolt" style="font-size:1.15rem;font-weight:800;color:var(--info);margin-top:2px">0.00 V</div>
                    <div style="font-size:.65rem;color:var(--muted)">Duty cycle scaled pack tap</div>
                  </div>
                  <div style="padding:10px 14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                    <div style="font-size:.65rem;font-weight:700;color:var(--faint);text-transform:uppercase">Shaft Speed</div>
                    <div class="mono" id="cpageJogRpm" style="font-size:1.15rem;font-weight:800;color:var(--ok);margin-top:2px">0 RPM</div>
                    <div style="font-size:.65rem;color:var(--muted)">20 CPR pulse tachometer</div>
                  </div>
                </div>
              </div>

              <!-- Physical KY-040 Center Push Switch Button -->
              <div style="display:flex;justify-content:center;margin:6px 0">
                <button type="button" class="btn btn-outline" id="btnEncoderPushSwitch" onclick="clickEncoderButton()"
                        style="width:100%;max-width:380px;padding:12px;background:linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);border:2px solid var(--border);border-radius:var(--radius);display:flex;align-items:center;justify-content:center;gap:10px;box-shadow:var(--shadow);cursor:pointer;transition:transform .1s ease">
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--ok);box-shadow:0 0 6px var(--ok)"></span>
                  <strong style="font-size:.82rem;letter-spacing:.04em">🔘 KY-040 ENCODER PUSH SWITCH (CLICK TO RUN / PAUSE)</strong>
                </button>
              </div>

              <!-- Step Jog Array (Fine & Coarse) -->
              <div>
                <div style="font-size:.7rem;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
                  Rotary Dial Steppers (Incremental Jog)
                </div>
                <div style="display:grid;grid-template-columns:repeat(8, 1fr);gap:6px">
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(-25)" title="Step -25 PWM">-25</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(-10)" title="Step -10 PWM">-10</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(-5)"  title="Step -5 PWM">-5</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(-1)"  title="Step -1 PWM">-1</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(1)"   title="Step +1 PWM">+1</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(5)"   title="Step +5 PWM">+5</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(10)"  title="Step +10 PWM">+10</button>
                  <button type="button" class="btn btn-outline btn-sm mono" onclick="jogEncoder(25)"  title="Step +25 PWM">+25</button>
                </div>
              </div>

              <!-- Primary Actuation Control Row -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px">
                <button type="button" class="btn btn-primary" id="btnCpageStart" onclick="sendMotorCmd('start')"
                        style="background:#2f6b46;border-color:#2f6b46;color:#fff;display:flex;align-items:center;justify-content:center;gap:8px;padding:12px">
                  <i data-lucide="play" style="width:16px;height:16px"></i> <strong>START MOTOR</strong>
                </button>
                <button type="button" class="btn btn-outline" id="btnCpageStop" onclick="sendMotorCmd('stop')"
                        style="display:flex;align-items:center;justify-content:center;gap:8px;padding:12px">
                  <i data-lucide="square" style="width:16px;height:16px"></i> <strong>STOP MOTOR</strong>
                </button>
              </div>

              <!-- Direction & Clear Trip Row -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <button type="button" class="btn btn-outline" id="btnCpageReverse" onclick="sendMotorCmd('reverse')"
                        style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:.78rem;padding:9px">
                  <i data-lucide="repeat" style="width:14px;height:14px"></i> Flip Direction (IN1/IN2)
                </button>
                <button type="button" class="btn btn-outline" id="btnCpageReset" onclick="sendMotorCmd('reset')"
                        style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:.78rem;padding:9px">
                  <i data-lucide="rotate-ccw" style="width:14px;height:14px"></i> Acknowledge / Reset Trip
                </button>
              </div>

              <!-- Red Industrial E-STOP Button -->
              <button type="button" class="btn" id="btnCpageEstop" onclick="sendMotorCmd('estop')"
                      style="background:#dc2626;border:2px solid #b91c1c;color:#fff;font-weight:900;letter-spacing:.08em;padding:12px 16px;display:flex;align-items:center;justify-content:center;gap:10px;box-shadow:0 4px 14px rgba(220,38,38,0.35);cursor:pointer;border-radius:var(--radius)">
                <i data-lucide="octagon-alert" style="width:20px;height:20px"></i> EMERGENCY STOP (HARDWARE E-STOP)
              </button>

            </div>
          </div>

          <!-- Card 2: PWM Speed Modulation & Rapid Operational Presets -->
          <div class="card" style="border-top:3px solid var(--info);box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="gauge"></i> PWM Speed Modulation &amp; Presets</span>
              <span class="badge badge-info" style="font-size:.66rem">L298N LEDC CHANNEL 0</span>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:18px">

              <!-- Large Speed Header -->
              <div style="display:flex;align-items:baseline;justify-content:space-between;padding-bottom:12px;border-bottom:1px solid var(--border)">
                <div>
                  <div style="font-size:.75rem;font-weight:700;color:var(--faint);text-transform:uppercase">Modulation Target</div>
                  <div style="font-size:.72rem;color:var(--muted);margin-top:2px">5 kHz High-Frequency Motor Drive</div>
                </div>
                <div style="display:flex;align-items:baseline;gap:8px">
                  <span class="mono" id="cpageSpeedPwm" style="font-size:2.4rem;font-weight:900;color:var(--accent);line-height:1">0</span>
                  <span class="mono" style="font-size:.9rem;color:var(--muted)">/ 255</span>
                  <span class="badge badge-info mono" id="cpageSpeedPct" style="font-size:.85rem;font-weight:700">0%</span>
                </div>
              </div>

              <!-- Tactile PWM Range Slider -->
              <div>
                <input type="range" id="cpageSpeedSlider" min="0" max="255" value="0"
                       oninput="onCpageSliderInput(this.value)"
                       onchange="onCpageSliderChange(this.value)"
                       style="width:100%;height:10px;accent-color:var(--accent);cursor:pointer" />
                <div style="display:flex;justify-content:space-between;font-size:.68rem;color:var(--faint);margin-top:6px;font-family:var(--font-mono)">
                  <span>0 (STOP)</span>
                  <span>64 (25%)</span>
                  <span>128 (50%)</span>
                  <span>192 (75%)</span>
                  <span>255 (100%)</span>
                </div>
              </div>

              <!-- Operational Speed Presets Rack -->
              <div>
                <div style="font-size:.7rem;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">
                  Rapid Operational Presets
                </div>
                <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:8px">
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(0)" data-cpage-preset="0"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--danger)">0</strong><span style="font-size:.6rem;color:var(--muted)">STOP</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(150)" data-cpage-preset="150"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--info)">150</strong><span style="font-size:.6rem;color:var(--muted)">MIN RUN (59%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(160)" data-cpage-preset="160"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--ok)">160</strong><span style="font-size:.6rem;color:var(--muted)">CRUISE (63%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(180)" data-cpage-preset="180"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--accent)">180</strong><span style="font-size:.6rem;color:var(--muted)">NOMINAL (71%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(200)" data-cpage-preset="200"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--hazard)">200</strong><span style="font-size:.6rem;color:var(--muted)">HEAVY (78%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(225)" data-cpage-preset="225"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--accent)">225</strong><span style="font-size:.6rem;color:var(--muted)">TURBO (88%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setSpeedPreset(255)" data-cpage-preset="255"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px">
                    <strong style="color:var(--danger)">255</strong><span style="font-size:.6rem;color:var(--muted)">MAX (100%)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="runSpeedSweep()"
                          style="font-size:.74rem;display:flex;flex-direction:column;gap:2px;padding:8px 4px;border-color:var(--accent);background:var(--surface-alt)">
                    <strong style="color:var(--accent)">SWEEP</strong><span style="font-size:.6rem;color:var(--muted)">AUTO 6-STEP</span>
                  </button>
                </div>
              </div>

              <!-- Slew Rate Limiter Toggle -->
              <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                <div>
                  <div style="font-size:.75rem;font-weight:700;color:var(--ink)">Slew-Rate Soft Start Limiter</div>
                  <div style="font-size:.68rem;color:var(--muted)">Smoothly ramps speed (15ms/step) to prevent battery voltage sag &amp; inrush spikes</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px">
                  <span class="badge badge-ok" id="cpageSlewBadge">SOFT-START ON</span>
                  <button type="button" class="btn btn-outline btn-sm" onclick="toggleSlewRate()" style="font-size:.72rem">Toggle</button>
                </div>
              </div>

              <!-- Motor Mechanical Telemetry Mini-Rail -->
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
                <div style="padding:10px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border);text-align:center">
                  <div style="font-size:.62rem;font-weight:700;color:var(--faint);text-transform:uppercase">Motor Amps</div>
                  <div class="mono" id="cpageMotorAmps" style="font-size:1.1rem;font-weight:800;color:var(--hazard);margin-top:2px">0.00 A</div>
                </div>
                <div style="padding:10px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border);text-align:center">
                  <div style="font-size:.62rem;font-weight:700;color:var(--faint);text-transform:uppercase">Motor Temp</div>
                  <div class="mono" id="cpageMotorTemp" style="font-size:1.1rem;font-weight:800;color:var(--ok);margin-top:2px">28.5 &deg;C</div>
                </div>
                <div style="padding:10px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border);text-align:center">
                  <div style="font-size:.62rem;font-weight:700;color:var(--faint);text-transform:uppercase">Vibration RMS</div>
                  <div class="mono" id="cpageMotorVib" style="font-size:1.1rem;font-weight:800;color:var(--info);margin-top:2px">0.32 g</div>
                </div>
              </div>

            </div>
          </div>

        </div>

        <!-- ═════════ ROW 2: ADVANCED AUTOMATION & SENSOR CALIBRATION (PLUS-ONES) ═════════ -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(460px, 1fr));gap:20px;margin-bottom:24px">

          <!-- Card 3: Automated Multi-Speed Sweeper & Burn-In Scheduler (Plus-One Web Exclusive) -->
          <div class="card" style="border-top:3px solid #8b5cf6;box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="play-circle"></i> Automated Diagnostics &amp; Burn-In Suite</span>
              <span class="badge" style="background:#ede9fe;color:#6d28d9;border:1px solid #c4b5fd;font-size:.65rem">PLUS-ONE SUITE</span>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:18px">

              <!-- Tool A: Automated Multi-Speed Characterization Sweeper -->
              <div style="padding:14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                  <div>
                    <div style="font-size:.8rem;font-weight:800;color:var(--ink)">Automated Speed Characterizer</div>
                    <div style="font-size:.68rem;color:var(--muted)">Steps motor through [150, 170, 190, 210, 230, 0] to record electromechanical curve</div>
                  </div>
                  <span class="badge" id="cpageSweepStatus" style="background:#ede9fe;color:#6d28d9;font-size:.68rem">READY</span>
                </div>

                <!-- Sweep Configuration & Execution -->
                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;flex-wrap:wrap">
                  <div style="display:flex;align-items:center;gap:6px;font-size:.74rem;color:var(--muted)">
                    <span>Dwell / Step:</span>
                    <select id="cpageSweepDwell" style="padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:var(--surface);font-size:.74rem">
                      <option value="1.5">1.5 Seconds</option>
                      <option value="2.5" selected>2.5 Seconds</option>
                      <option value="5.0">5.0 Seconds</option>
                    </select>
                  </div>
                  <div style="display:flex;gap:8px">
                    <button type="button" class="btn btn-primary btn-sm" id="btnStartSweep" onclick="startCustomSweep()"
                            style="background:#7c3aed;border-color:#7c3aed;color:#fff;font-size:.74rem">
                      <i data-lucide="play"></i> Start Sweep
                    </button>
                    <button type="button" class="btn btn-outline btn-sm" id="btnAbortSweep" onclick="abortSweep()"
                            style="display:none;color:#dc2626;border-color:#f87171;font-size:.74rem">
                      <i data-lucide="square"></i> Abort Sweep
                    </button>
                  </div>
                </div>

                <!-- Visual Step Indicator & Progress -->
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:.68rem;color:var(--faint);margin-bottom:4px">
                    <span id="cpageSweepStepIndicator">Sequence: [150, 170, 190, 210, 230, 0]</span>
                    <span id="cpageSweepPctText">0%</span>
                  </div>
                  <div style="height:6px;background:var(--surface);border-radius:999px;overflow:hidden;border:1px solid var(--border)">
                    <div id="cpageSweepProgressBar" style="height:100%;width:0%;background:linear-gradient(90deg, #8b5cf6, #3b82f6);border-radius:999px;transition:width .3s ease"></div>
                  </div>
                </div>

                <!-- Live Results Table Preview -->
                <div id="cpageSweepTableWrap" style="margin-top:12px;display:none;max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:6px">
                  <table class="data" style="font-size:.68rem">
                    <thead>
                      <tr><th>PWM</th><th>Armature V</th><th>Current</th><th>Vibration</th><th>RPM</th></tr>
                    </thead>
                    <tbody id="cpageSweepTableBody"></tbody>
                  </table>
                </div>
              </div>

              <!-- Tool B: Timed Burn-In / Endurance Run Scheduler -->
              <div style="padding:14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                  <div>
                    <div style="font-size:.8rem;font-weight:800;color:var(--ink)">Timed Burn-In &amp; Stress Test Scheduler</div>
                    <div style="font-size:.68rem;color:var(--muted)">Runs at target PWM for countdown duration, then safely stops automatically</div>
                  </div>
                  <span class="mono" id="cpageBurnInTimer" style="font-size:1.4rem;font-weight:900;color:var(--accent)">00:00</span>
                </div>

                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                  <button type="button" class="btn btn-outline btn-sm" onclick="startBurnInRun(15)">15s Test</button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="startBurnInRun(30)">30s Stress</button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="startBurnInRun(60)">1m Burn-In</button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="startBurnInRun(300)">5m Endurance</button>
                  <button type="button" class="btn btn-outline btn-sm" id="btnCancelBurnIn" onclick="cancelBurnInRun()"
                          style="display:none;color:#dc2626;border-color:#f87171">Cancel Test</button>
                </div>
              </div>

            </div>
          </div>

          <!-- Card 4: ACS712 Current Sensor Calibration Studio (Fixes & Solves 16.78A Bug) -->
          <div class="card" style="border-top:3px solid var(--hazard);box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="target"></i> ACS712 Current Sensor Calibration Studio</span>
              <span class="badge" style="background:var(--hazard-soft);color:var(--hazard);border:1px solid #fde68a;font-size:.65rem">ANTI-SPIKE ACTIVE</span>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:16px">

              <!-- Bug Resolution Diagnostic Callout -->
              <div style="padding:10px 14px;background:#fefce8;border:1px solid #fde047;border-radius:var(--radius);color:#854d0e;font-size:.72rem">
                <div style="font-weight:700;display:flex;align-items:center;gap:6px">
                  <i data-lucide="shield-check" style="width:16px;height:16px;color:#ca8a04"></i>
                  16.78A Spurious Glitch Resolved &bull; Trimmed-Mean PWM Hash Rejection Active
                </div>
                <div style="margin-top:4px;color:#713f12">
                  L298N 5kHz inductive brush noise is rejected using 64-sample interquartile range (IQR) sorting. Outliers &gt; 5.0A are physically clamped, and quiescent 0A point is auto-tracked.
                </div>
              </div>

              <!-- Live Sensor Zero & Raw ADC Readouts -->
              <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:8px">
                <div style="padding:8px 10px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
                  <div style="font-size:.6rem;font-weight:700;color:var(--faint);text-transform:uppercase">Motor 0A Baseline</div>
                  <div class="mono" id="cpageZeroM" style="font-size:1.05rem;font-weight:800;color:var(--ink);margin-top:2px">1.140 V</div>
                  <div style="font-size:.6rem;color:var(--muted)">Quiescent V/2</div>
                </div>
                <div style="padding:8px 10px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
                  <div style="font-size:.6rem;font-weight:700;color:var(--faint);text-transform:uppercase">Total 0A Baseline</div>
                  <div class="mono" id="cpageZeroT" style="font-size:1.05rem;font-weight:800;color:var(--ink);margin-top:2px">1.148 V</div>
                  <div style="font-size:.6rem;color:var(--muted)">Supply Quiescent</div>
                </div>
                <div style="padding:8px 10px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
                  <div style="font-size:.6rem;font-weight:700;color:var(--faint);text-transform:uppercase">ACS Sensitivity</div>
                  <div class="mono" id="cpageLiveSens" style="font-size:1.05rem;font-weight:800;color:var(--info);margin-top:2px">0.100 V/A</div>
                  <div style="font-size:.6rem;color:var(--muted)">Transfer Slope</div>
                </div>
                <div style="padding:8px 10px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
                  <div style="font-size:.6rem;font-weight:700;color:var(--faint);text-transform:uppercase">Total Current</div>
                  <div class="mono" id="cpageTotalAmps" style="font-size:1.05rem;font-weight:800;color:var(--ok);margin-top:2px">0.25 A</div>
                  <div style="font-size:.6rem;color:var(--muted)">True DC Draw</div>
                </div>
              </div>

              <!-- Module Sensitivity Preset Selector -->
              <div>
                <div style="font-size:.7rem;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
                  ACS712 Sensor Hardware Model Selection
                </div>
                <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:8px">
                  <button type="button" class="btn btn-outline btn-sm" onclick="setAcsSensitivity(0.185)" data-sens-preset="0.185"
                          style="font-size:.72rem;display:flex;flex-direction:column;gap:2px;padding:8px">
                    <strong>ACS712-05B</strong>
                    <span style="font-size:.62rem;color:var(--muted)">185 mV/A (5A Model)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm is-active" onclick="setAcsSensitivity(0.100)" data-sens-preset="0.100"
                          style="font-size:.72rem;display:flex;flex-direction:column;gap:2px;padding:8px">
                    <strong style="color:var(--accent)">ACS712-20A [Default]</strong>
                    <span style="font-size:.62rem;color:var(--muted)">100 mV/A (20A Model)</span>
                  </button>
                  <button type="button" class="btn btn-outline btn-sm" onclick="setAcsSensitivity(0.066)" data-sens-preset="0.066"
                          style="font-size:.72rem;display:flex;flex-direction:column;gap:2px;padding:8px">
                    <strong>ACS712-30A</strong>
                    <span style="font-size:.62rem;color:var(--muted)">66 mV/A (30A Model)</span>
                  </button>
                </div>
              </div>

              <!-- Calibration Actions -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <button type="button" class="btn btn-primary" id="btnCpageZeroCal" onclick="zeroCalibrateNow()"
                        style="background:var(--accent);border-color:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;gap:6px;font-size:.78rem;padding:10px">
                  <i data-lucide="target" style="width:16px;height:16px"></i> <strong>Zero Calibrate Baseline (0A)</strong>
                </button>
                <button type="button" class="btn btn-outline" onclick="promptManualZero()"
                        style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:.78rem;padding:10px">
                  <i data-lucide="sliders" style="width:16px;height:16px"></i> Manual Zero-Offset Trim
                </button>
              </div>

              <!-- Multiplier Fine-Trim Slider -->
              <div style="padding:10px 14px;background:var(--surface-alt);border-radius:var(--radius);border:1px solid var(--border)">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                  <span style="font-size:.72rem;font-weight:700;color:var(--ink)">Motor Current Scaling Multiplier</span>
                  <span class="mono" id="cpageTrimVal" style="font-size:.82rem;font-weight:800;color:var(--accent)">1.00x</span>
                </div>
                <input type="range" id="cpageTrimSlider" min="0.5" max="1.5" step="0.05" value="1.0"
                       oninput="setMotorCurrentTrim(this.value)"
                       style="width:100%;height:8px;accent-color:var(--accent);cursor:pointer" />
                <div style="display:flex;justify-content:space-between;font-size:.62rem;color:var(--faint);margin-top:4px">
                  <span>0.50x (Scale Down)</span>
                  <span>1.00x (Nominal)</span>
                  <span>1.50x (Scale Up)</span>
                </div>
              </div>

            </div>
          </div>

        </div>

        <!-- ═════════ ROW 3: VIRTUAL SOFTWARE BMS & SCADA REMOTE CONSOLE ═════════ -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(460px, 1fr));gap:20px;margin-bottom:24px">

          <!-- Card 5: Virtual Software BMS & Cell Balancer Calibration -->
          <div class="card" style="border-top:3px solid var(--ok);box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="shield-check"></i> Virtual Software BMS &amp; Cell Balancer</span>
              <span class="badge badge-ok" id="cpageBmsBadge">SAFE MODE ACTIVE</span>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:16px">

              <!-- Battery Cell Gauges -->
              <div style="display:flex;flex-direction:column;gap:10px">
                <div style="display:flex;align-items:center;justify-content:space-between;font-size:.72rem;font-weight:700;color:var(--faint);text-transform:uppercase">
                  <span>3S 18650 Individual Cell Taps</span>
                  <span class="badge" id="cpageCellDeltaBadge" style="background:var(--hazard-soft);color:var(--hazard);font-size:.65rem">&Delta; 1.05 V IMBALANCE</span>
                </div>

                <!-- Cell 1 -->
                <div style="padding:8px 12px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius)">
                  <div style="display:flex;justify-content:space-between;font-size:.74rem;margin-bottom:4px">
                    <span style="font-weight:700">Cell 1 (Ground Tap)</span>
                    <span class="mono" id="cpageCell1" style="font-weight:800;color:var(--hazard)">2.91 V (Low Cell)</span>
                  </div>
                  <div style="height:6px;background:var(--surface);border-radius:999px;overflow:hidden;border:1px solid var(--border)">
                    <div id="cpageCellBar1" style="height:100%;width:20%;background:var(--hazard);border-radius:999px;transition:width .3s"></div>
                  </div>
                </div>

                <!-- Cell 2 -->
                <div style="padding:8px 12px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius)">
                  <div style="display:flex;justify-content:space-between;font-size:.74rem;margin-bottom:4px">
                    <span style="font-weight:700">Cell 2 (Middle Tap)</span>
                    <span class="mono" id="cpageCell2" style="font-weight:800;color:var(--ok)">3.95 V (Nominal)</span>
                  </div>
                  <div style="height:6px;background:var(--surface);border-radius:999px;overflow:hidden;border:1px solid var(--border)">
                    <div id="cpageCellBar2" style="height:100%;width:80%;background:var(--ok);border-radius:999px;transition:width .3s"></div>
                  </div>
                </div>

                <!-- Cell 3 -->
                <div style="padding:8px 12px;background:var(--surface-alt);border:1px solid var(--border);border-radius:var(--radius)">
                  <div style="display:flex;justify-content:space-between;font-size:.74rem;margin-bottom:4px">
                    <span style="font-weight:700">Cell 3 (Top Pack Tap)</span>
                    <span class="mono" id="cpageCell3" style="font-weight:800;color:var(--accent)">3.87 V (Nominal)</span>
                  </div>
                  <div style="height:6px;background:var(--surface);border-radius:999px;overflow:hidden;border:1px solid var(--border)">
                    <div id="cpageCellBar3" style="height:100%;width:74%;background:var(--ok);border-radius:999px;transition:width .3s"></div>
                  </div>
                </div>
              </div>

              <!-- BMS Safety Controls -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <button type="button" class="btn btn-outline" id="btnCpageBmsToggle" onclick="toggleBmsOverride()"
                        style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:.76rem;padding:10px">
                  <i data-lucide="shield" style="width:16px;height:16px;color:var(--ok)"></i>
                  <span id="cpageBmsToggleLabel">BMS Cutoff: SAFE MODE</span>
                </button>
                <button type="button" class="btn btn-outline" onclick="calibrateBatteryDividers()"
                        style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:.76rem;padding:10px">
                  <i data-lucide="sliders" style="width:16px;height:16px"></i>
                  Trim Resistor Dividers
                </button>
              </div>

            </div>
          </div>

          <!-- Card 6: SCADA Direct Command Terminal & Historian Export -->
          <div class="card" style="border-top:3px solid #0284c7;box-shadow:var(--shadow-md)">
            <div class="card-head" style="display:flex;align-items:center;justify-content:space-between">
              <span class="card-title"><i data-lucide="terminal"></i> SCADA Direct Command Terminal</span>
              <button type="button" class="btn btn-outline btn-sm" onclick="downloadTelemetryCsv()" style="font-size:.7rem">
                <i data-lucide="download"></i> Export Telemetry CSV
              </button>
            </div>
            <div class="card-body" style="padding:20px;display:flex;flex-direction:column;gap:14px">

              <div style="font-size:.72rem;color:var(--muted)">
                Direct bidirectional console link to ESP32 firmware over USB Serial (115200 baud) and Wireless UDP (port 8888).
              </div>

              <!-- Interactive Terminal Output Box -->
              <div id="scadaConsoleLog"
                   style="height:150px;background:#0f172a;border:1px solid #334155;border-radius:var(--radius);padding:10px 12px;font-family:var(--font-mono);font-size:.72rem;color:#38bdf8;overflow-y:auto;line-height:1.4">
                <div style="color:#94a3b8">-- RS-380 SCADA Terminal Online. Type a command below --</div>
                <div style="color:#22c55e">[BRIDGE] Connected to ESP32 on COM5 + UDP 192.168.4.1:8888</div>
              </div>

              <!-- Command Input Form -->
              <form onsubmit="sendRawConsoleCmd();return false;" style="display:flex;gap:8px">
                <input type="text" id="scadaConsoleInput" placeholder="Enter command (e.g. SPEED=180, CAL_ZERO, CAL_SENS=0.100, STATUS, RESET)..."
                       style="flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);color:var(--ink);font-family:var(--font-mono);font-size:.76rem" />
                <button type="submit" class="btn btn-primary btn-sm" style="background:#0284c7;border-color:#0284c7;color:#fff;font-size:.74rem">
                  Send Command
                </button>
              </form>

              <!-- Quick Command Pills -->
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
                <span style="font-size:.65rem;color:var(--faint);font-weight:700">QUICK CMDS:</span>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('STATUS')">STATUS</button>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('SPEED=160')">SPEED=160</button>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('STOP')">STOP</button>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('RESET')">RESET</button>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('CAL_ZERO')">CAL_ZERO</button>
                <button type="button" class="btn btn-outline btn-sm mono" style="font-size:.65rem;padding:2px 8px" onclick="injectConsoleCmd('CAL_SENS=0.100')">CAL_SENS=0.100</button>
              </div>

            </div>
          </div>

        </div>

      </section>
'''

def build_controls_js():
    return '''
// ══════════════════════════════════════════════════════════════════════════════
// DEDICATED HARDWARE CONTROL CENTER JAVASCRIPT LOGIC
// ══════════════════════════════════════════════════════════════════════════════

let slewRateActive = true;
let sweepInterval = null;
let sweepCurrentStep = -1;
const SWEEP_STEPS = [150, 170, 190, 210, 230, 0];
let sweepDwellSec = 2.5;
let sweepRecords = [];

let burnInTimer = null;
let burnInRemaining = 0;

function jogEncoder(delta) {
  let target = (motorControlState.pwm || 0) + delta;
  target = Math.max(0, Math.min(255, target));
  // Snap from 0 to 150 min starting torque on coarse step
  if (motorControlState.pwm === 0 && delta > 0 && target < 150 && Math.abs(delta) >= 10) {
    target = 150;
  }
  setSpeedPreset(target);
  animateJogFeedback(delta > 0 ? 'cw' : 'ccw');
}

function clickEncoderButton() {
  // Mimics physical KY-040 rotary push switch
  const swBtn = document.getElementById('btnEncoderPushSwitch');
  if (swBtn) {
    swBtn.style.transform = 'scale(0.96)';
    setTimeout(() => { swBtn.style.transform = 'scale(1)'; }, 150);
  }

  if (motorControlState.safetyTripped) {
    sendMotorCmd('reset');
  } else if (motorControlState.running && motorControlState.pwm > 0) {
    sendMotorCmd('stop');
  } else {
    sendMotorCmd('start');
  }
}

function animateJogFeedback(dir) {
  const needle = document.getElementById('cpageJogNeedle');
  if (needle) {
    const extra = dir === 'cw' ? 8 : -8;
    const baseRot = (motorControlState.pwm / 255) * 270 - 135;
    needle.style.transform = `rotate(${baseRot + extra}deg)`;
    setTimeout(() => {
      needle.style.transform = `rotate(${baseRot}deg)`;
    }, 120);
  }
}

function onCpageSliderInput(val) {
  onSpeedSliderInput(val);
  syncControlsPageUI();
}

function onCpageSliderChange(val) {
  onSpeedSliderChange(val);
  syncControlsPageUI();
}

function toggleSlewRate() {
  slewRateActive = !slewRateActive;
  sendMotorCmd('set_slew', slewRateActive ? 'ON' : 'OFF');
  const badge = document.getElementById('cpageSlewBadge');
  if (badge) {
    badge.textContent = slewRateActive ? 'SOFT-START ON' : 'INSTANT JUMP (OFF)';
    badge.className = slewRateActive ? 'badge badge-ok' : 'badge badge-hazard';
  }
}

async function setAcsSensitivity(sens) {
  await sendMotorCmd('cal_sens', sens);
  document.querySelectorAll('[data-sens-preset]').forEach(b => {
    b.classList.toggle('is-active', Math.abs(parseFloat(b.getAttribute('data-sens-preset')) - sens) < 0.005);
  });
  const sensEl = document.getElementById('cpageLiveSens');
  if (sensEl) sensEl.textContent = sens.toFixed(3) + ' V/A';
  appendConsoleLog(`[CALIB] Set ACS712 sensitivity to ${sens.toFixed(3)} V/A`, 'resp');
}

async function zeroCalibrateNow() {
  const btn = document.getElementById('btnCpageZeroCal');
  if (btn) btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Calibrating 0A Baseline...';
  appendConsoleLog('[CALIB] Sampling 40 IQR readings for 0A quiescent calibration...', 'user');
  await sendMotorCmd('cal_zero');
  setTimeout(() => {
    if (btn) {
      btn.innerHTML = '<i data-lucide="target"></i> <strong>Zero Calibrate Baseline (0A)</strong>';
      lucide.createIcons();
    }
    appendConsoleLog('[CALIB] Zero-point calibration complete.', 'resp');
  }, 1200);
}

function promptManualZero() {
  const currentZero = prompt('Enter manual Motor Zero Voltage (0.80 - 1.50 V):', '1.139');
  if (currentZero) {
    const val = parseFloat(currentZero);
    if (!isNaN(val) && val >= 0.8 && val <= 1.5) {
      sendMotorCmd('cal_zero_m', val);
      appendConsoleLog(`[CALIB] Set manual motor zero: ${val.toFixed(3)} V`, 'resp');
    } else {
      alert('Invalid zero voltage. Must be between 0.80 and 1.50 V.');
    }
  }
}

function setMotorCurrentTrim(val) {
  const mult = parseFloat(val);
  const el = document.getElementById('cpageTrimVal');
  if (el) el.textContent = mult.toFixed(2) + 'x';
  sendMotorCmd('cal_trim_imot', mult);
}

function calibrateBatteryDividers() {
  const b1 = prompt('Enter Trim Multiplier for Cell 1 (Tap B1, default 1.000):', '1.000');
  if (b1) sendMotorCmd('cal_trim', { channel: 'b1', value: parseFloat(b1) || 1.0 });
  const b2 = prompt('Enter Trim Multiplier for Cell 2 (Tap B2, default 1.000):', '1.000');
  if (b2) sendMotorCmd('cal_trim', { channel: 'b2', value: parseFloat(b2) || 1.0 });
  const bp = prompt('Enter Trim Multiplier for Pack (Tap BPack, default 1.000):', '1.000');
  if (bp) sendMotorCmd('cal_trim', { channel: 'bpack', value: parseFloat(bp) || 1.0 });
}

// ── Automated Multi-Speed Sweeper ──
async function startCustomSweep() {
  if (sweepInterval) return;
  const dwellSelect = document.getElementById('cpageSweepDwell');
  sweepDwellSec = parseFloat(dwellSelect ? dwellSelect.value : 2.5);
  sweepCurrentStep = 0;
  sweepRecords = [];

  document.getElementById('cpageSweepStatus').textContent = 'RUNNING';
  document.getElementById('cpageSweepStatus').style.background = '#fef3c7';
  document.getElementById('cpageSweepStatus').style.color = '#92400e';
  document.getElementById('btnStartSweep').style.display = 'none';
  document.getElementById('btnAbortSweep').style.display = 'inline-flex';
  document.getElementById('cpageSweepTableWrap').style.display = 'block';
  document.getElementById('cpageSweepTableBody').innerHTML = '';

  appendConsoleLog(`[SWEEP] Starting characterization sweep sequence with ${sweepDwellSec}s dwell...`, 'user');
  executeSweepStep();
}

async function executeSweepStep() {
  if (sweepCurrentStep >= SWEEP_STEPS.length) {
    finishSweep('COMPLETED');
    return;
  }
  const pwm = SWEEP_STEPS[sweepCurrentStep];
  const stepIdx = sweepCurrentStep + 1;
  const total = SWEEP_STEPS.length;

  document.getElementById('cpageSweepStepIndicator').textContent = `Step ${stepIdx}/${total}: Target PWM ${pwm}`;
  document.getElementById('cpageSweepPctText').textContent = Math.round((stepIdx / total) * 100) + '%';
  document.getElementById('cpageSweepProgressBar').style.width = Math.round((stepIdx / total) * 100) + '%';

  await sendMotorCmd('speed', pwm);
  appendConsoleLog(`[SWEEP] Step ${stepIdx}/${total} -> Setting PWM ${pwm} (holding ${sweepDwellSec}s)`, 'resp');

  setTimeout(() => {
    if (sweepCurrentStep >= 999) return; // Aborted
    // Capture snapshot from live state
    const row = {
      pwm,
      volt: +(document.getElementById('pwrMotVolt')?.textContent.replace(' V','') || 0),
      curr: +(document.getElementById('cpageMotorAmps')?.textContent.replace(' A','') || 0),
      vib: +(document.getElementById('cpageMotorVib')?.textContent.replace(' g','') || 0),
      rpm: +(document.getElementById('cpageJogRpm')?.textContent.replace(' RPM','') || 0)
    };
    sweepRecords.push(row);
    appendSweepTableRow(row);

    sweepCurrentStep++;
    executeSweepStep();
  }, sweepDwellSec * 1000);
}

function appendSweepTableRow(r) {
  const tbody = document.getElementById('cpageSweepTableBody');
  if (!tbody) return;
  const tr = document.createElement('tr');
  tr.innerHTML = `<td class="mono"><strong>${r.pwm}</strong></td>
                  <td class="mono">${r.volt.toFixed(2)} V</td>
                  <td class="mono">${r.curr.toFixed(2)} A</td>
                  <td class="mono">${r.vib.toFixed(2)} g</td>
                  <td class="mono">${r.rpm}</td>`;
  tbody.appendChild(tr);
}

function abortSweep() {
  sweepCurrentStep = 999;
  sendMotorCmd('stop');
  finishSweep('ABORTED');
  appendConsoleLog('[SWEEP] Characterization sweep aborted by user.', 'err');
}

function finishSweep(status) {
  document.getElementById('cpageSweepStatus').textContent = status;
  document.getElementById('cpageSweepStatus').style.background = status === 'COMPLETED' ? '#dcfce7' : '#fee2e2';
  document.getElementById('cpageSweepStatus').style.color = status === 'COMPLETED' ? '#166534' : '#991b1b';
  document.getElementById('btnStartSweep').style.display = 'inline-flex';
  document.getElementById('btnAbortSweep').style.display = 'none';
  sendMotorCmd('stop');
}

// ── Timed Burn-In Test ──
function startBurnInRun(seconds) {
  if (burnInTimer) clearInterval(burnInTimer);
  burnInRemaining = seconds;
  updateBurnInDisplay();

  if (!motorControlState.running || motorControlState.pwm === 0) {
    sendMotorCmd('speed', 160);
  }

  document.getElementById('btnCancelBurnIn').style.display = 'inline-flex';
  appendConsoleLog(`[BURN-IN] Started ${seconds}s timed endurance run @ PWM ${motorControlState.pwm || 160}`, 'user');

  burnInTimer = setInterval(() => {
    burnInRemaining--;
    updateBurnInDisplay();
    if (burnInRemaining <= 0) {
      clearInterval(burnInTimer);
      burnInTimer = null;
      sendMotorCmd('stop');
      document.getElementById('btnCancelBurnIn').style.display = 'none';
      appendConsoleLog('[BURN-IN] Test finished! Motor de-energized safely.', 'resp');
      alert('Timed Burn-in test complete! Motor safely stopped.');
    }
  }, 1000);
}

function cancelBurnInRun() {
  if (burnInTimer) {
    clearInterval(burnInTimer);
    burnInTimer = null;
  }
  burnInRemaining = 0;
  updateBurnInDisplay();
  document.getElementById('btnCancelBurnIn').style.display = 'none';
  sendMotorCmd('stop');
  appendConsoleLog('[BURN-IN] Test canceled by user.', 'err');
}

function updateBurnInDisplay() {
  const m = Math.floor(burnInRemaining / 60);
  const s = burnInRemaining % 60;
  const str = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  const el = document.getElementById('cpageBurnInTimer');
  if (el) el.textContent = str;
}

// ── Terminal Console ──
function appendConsoleLog(msg, type = 'resp') {
  const log = document.getElementById('scadaConsoleLog');
  if (!log) return;
  const d = document.createElement('div');
  const timeStr = new Date().toLocaleTimeString();
  if (type === 'user') {
    d.style.color = '#f8fafc';
    d.textContent = `[${timeStr}] > ${msg}`;
  } else if (type === 'err') {
    d.style.color = '#ef4444';
    d.textContent = `[${timeStr}] ! ${msg}`;
  } else {
    d.style.color = '#38bdf8';
    d.textContent = `[${timeStr}] < ${msg}`;
  }
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}

function injectConsoleCmd(cmd) {
  const inp = document.getElementById('scadaConsoleInput');
  if (inp) {
    inp.value = cmd;
    sendRawConsoleCmd();
  }
}

async function sendRawConsoleCmd() {
  const inp = document.getElementById('scadaConsoleInput');
  const cmd = inp ? inp.value.trim() : '';
  if (!cmd) return;
  inp.value = '';
  appendConsoleLog(cmd, 'user');

  try {
    const res = await fetch('/api/motor/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'raw_cmd', cmd })
    });
    const d = await res.json();
    appendConsoleLog(d.message || d.command || 'OK', 'resp');
  } catch (e) {
    appendConsoleLog('Error: ' + e.message, 'err');
  }
}

// ── Sync UI with Controls Page ──
function syncControlsPageUI() {
  const pwm = motorControlState.pwm || 0;
  const running = motorControlState.running;
  const tripped = motorControlState.safetyTripped;
  const reason = motorControlState.safetyTripReason;

  // 1. Rotary Jog Needle & Arc
  const needle = document.getElementById('cpageJogNeedle');
  if (needle) {
    const rot = (pwm / 255) * 270 - 135;
    needle.style.transform = `rotate(${rot}deg)`;
  }
  const ring = document.getElementById('cpageJogRing');
  if (ring) {
    // Circumference = 2 * PI * 76 = ~477.5. Dasharray is 358 (270 deg of circle)
    const offset = 358 - (pwm / 255) * 358;
    ring.style.strokeDashoffset = offset;
  }

  // 2. Central readouts
  const jogPwm = document.getElementById('cpageJogPwm');
  if (jogPwm) jogPwm.textContent = pwm;
  const jogPct = document.getElementById('cpageJogPct');
  if (jogPct) jogPct.textContent = Math.round((pwm / 255) * 100) + '%';
  const cpageSlider = document.getElementById('cpageSpeedSlider');
  if (cpageSlider && !motorControlState.isInteracting) cpageSlider.value = pwm;
  const cpagePwm = document.getElementById('cpageSpeedPwm');
  if (cpagePwm) cpagePwm.textContent = pwm;
  const cpagePct = document.getElementById('cpageSpeedPct');
  if (cpagePct) cpagePct.textContent = Math.round((pwm / 255) * 100) + '%';

  // 3. Status pills & badges
  const cStatePill = document.getElementById('cpageMotorStatePill');
  const cStateText = document.getElementById('cpageMotorStateText');
  if (cStatePill && cStateText) {
    if (tripped) {
      cStatePill.className = 'status-pill critical';
      cStateText.textContent = 'TRIP: ' + (reason || 'FAULT');
    } else if (running && pwm > 0) {
      cStatePill.className = 'status-pill good';
      cStateText.textContent = 'RUNNING (' + pwm + ')';
    } else {
      cStatePill.className = 'status-pill warning';
      cStateText.textContent = 'STANDBY / OFF';
    }
  }

  const cDirBadge = document.getElementById('cpageDirBadge');
  if (cDirBadge) {
    cDirBadge.textContent = motorControlState.direction === 'REV' ? 'REVERSE (CCW)' : 'FORWARD (CW)';
    cDirBadge.className = motorControlState.direction === 'REV' ? 'badge badge-hazard' : 'badge badge-info';
  }

  // Highlight active presets
  document.querySelectorAll('[data-cpage-preset]').forEach(b => {
    b.classList.toggle('is-active', parseInt(b.getAttribute('data-cpage-preset'), 10) === pwm);
  });
}
'''

def main():
    path = 'dashboard/index.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if sec-controls already exists
    if 'id="sec-controls"' in content:
        print("[INFO] sec-controls already present in index.html. Removing old block first...")
        content = re.sub(r'<!-- ════════════ SECTION: CONTROLS.*?<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->',
                         '<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->', content, flags=re.DOTALL)

    # Insert controls HTML between </section><!-- overview --> and sec-prognostics
    target_pattern = r'(</section>\s*<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->)'
    if not re.search(target_pattern, content):
        target_pattern = r'(</section>\s*<section class="page-section" id="sec-prognostics">)'

    controls_html = build_controls_html()
    replacement = f"</section>\n\n{controls_html}\n<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->"

    if re.search(r'</section>\s*<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->', content):
        content = re.sub(r'</section>\s*<!-- ════════════ SECTION: PROGNOSTICS ════════════ -->', replacement, content, count=1)
        print("[SUCCESS] Injected sec-controls HTML block before sec-prognostics.")
    else:
        print("[ERROR] Could not find insertion marker before sec-prognostics!")
        return

    # Check if controls JS is already present
    controls_js = build_controls_js()
    if '// DEDICATED HARDWARE CONTROL CENTER JAVASCRIPT LOGIC' not in content:
        # Insert before </script>
        script_idx = content.rfind('</script>')
        if script_idx != -1:
            content = content[:script_idx] + '\n' + controls_js + '\n' + content[script_idx:]
            print("[SUCCESS] Injected Controls JavaScript logic before </script>.")

    # Hook syncControlsPageUI into renderMotorControlUI and telemetry update
    if 'syncControlsPageUI();' not in content:
        content = content.replace('function renderMotorControlUI() {',
                                  'function renderMotorControlUI() {\n  syncControlsPageUI();')
        print("[SUCCESS] Hooked syncControlsPageUI() into renderMotorControlUI().")

    # Hook live telemetry fields update into onMessage / updateTelemetry
    telemetry_hook = '''
  // Update Controls Page Live Metrics
  const cJogVolt = document.getElementById('cpageJogVolt');
  if (cJogVolt) cJogVolt.textContent = ((hw.motor_voltage !== undefined ? hw.motor_voltage : 0).toFixed(2)) + ' V';
  const cJogRpm = document.getElementById('cpageJogRpm');
  if (cJogRpm) cJogRpm.textContent = (hw.rpm || 0) + ' RPM';
  const cMotAmps = document.getElementById('cpageMotorAmps');
  if (cMotAmps) cMotAmps.textContent = (hw.motor_current !== undefined ? hw.motor_current : 0).toFixed(2) + ' A';
  const cTotAmps = document.getElementById('cpageTotalAmps');
  if (cTotAmps) cTotAmps.textContent = (hw.total_current !== undefined ? hw.total_current : 0).toFixed(2) + ' A';
  const cMotTemp = document.getElementById('cpageMotorTemp');
  if (cMotTemp) cMotTemp.textContent = (hw.temperature !== undefined ? hw.temperature.toFixed(1) : '28.5') + ' °C';
  const cMotVib = document.getElementById('cpageMotorVib');
  if (cMotVib) cMotVib.textContent = (hw.vibration !== undefined ? hw.vibration.toFixed(2) : '0.20') + ' g';
  const cZeroM = document.getElementById('cpageZeroM');
  if (cZeroM && hw.zero_m !== undefined) cZeroM.textContent = hw.zero_m.toFixed(3) + ' V';
  const cZeroT = document.getElementById('cpageZeroT');
  if (cZeroT && hw.zero_t !== undefined) cZeroT.textContent = hw.zero_t.toFixed(3) + ' V';
  const cSens = document.getElementById('cpageLiveSens');
  if (cSens && hw.sens !== undefined) cSens.textContent = hw.sens.toFixed(3) + ' V/A';

  const cCell1 = document.getElementById('cpageCell1');
  if (cCell1) cCell1.textContent = (hw.cell1 !== undefined ? hw.cell1.toFixed(2) : '3.70') + ' V';
  const cCell2 = document.getElementById('cpageCell2');
  if (cCell2) cCell2.textContent = (hw.cell2 !== undefined ? hw.cell2.toFixed(2) : '3.70') + ' V';
  const cCell3 = document.getElementById('cpageCell3');
  if (cCell3) cCell3.textContent = (hw.cell3 !== undefined ? hw.cell3.toFixed(2) : '3.70') + ' V';
  const cDeltaBadge = document.getElementById('cpageCellDeltaBadge');
  if (cDeltaBadge && hw.cell_delta !== undefined) {
    cDeltaBadge.textContent = 'Δ ' + hw.cell_delta.toFixed(2) + ' V ' + (hw.cell_delta > 0.35 ? 'IMBALANCE' : 'BALANCED');
    cDeltaBadge.className = hw.cell_delta > 0.35 ? 'badge badge-hazard' : 'badge badge-ok';
  }
'''
    if 'cpageMotorAmps' not in content:
        content = content.replace("function updateVirtualBmsWatchdog(hw) {",
                                  "function updateVirtualBmsWatchdog(hw) {\n" + telemetry_hook)
        print("[SUCCESS] Hooked Controls Page live metric updates into updateVirtualBmsWatchdog().")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[SUCCESS] Successfully updated dashboard/index.html with dedicated Hardware Control Center!")

if __name__ == '__main__':
    main()
