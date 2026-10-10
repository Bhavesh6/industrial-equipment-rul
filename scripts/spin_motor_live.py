import urllib.request
import json
import time

def post(body):
    req = urllib.request.Request(
        'http://localhost:8000/api/motor/control',
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def get_telem():
    req = urllib.request.Request('http://localhost:8000/api/telemetry')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

print(">>> [SPIN TEST] Starting motor at 180 PWM...")
res = post({'action': 'speed', 'value': 180})
print("Command Response:", res)

print("\n>>> Motor is actively spinning now! Monitoring live physical vitals...")
for i in range(10):
    time.sleep(1.0)
    t = get_telem()
    hw = t['data']['telemetry']
    pred = t['data']['prediction']
    pwm = hw.get('pwm')
    v_mot = hw.get('motor_voltage')
    i_mot = hw.get('motor_current')
    rpm = hw.get('rpm')
    vib = hw.get('vibration')
    temp = hw.get('temperature')
    rul = pred.get('rul_hours')
    print(f"T+{i+1}s: PWM={pwm} | V_mot={v_mot}V | I_mot={i_mot}A | Speed={rpm} RPM | Vib={vib}g | Temp={temp}C | RUL={rul}h")

print("\n>>> [SPIN TEST] Stopping motor safely...")
res_stop = post({'action': 'stop'})
print("Stop Response:", res_stop)

time.sleep(1.0)
t_end = get_telem()
hw_end = t_end['data']['telemetry']
print(f"Motor successfully stopped: PWM={hw_end.get('pwm')} | RPM={hw_end.get('rpm')} | V_mot={hw_end.get('motor_voltage')}V")
