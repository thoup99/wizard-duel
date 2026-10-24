"""Rule recognizer. Samples: seconds, ax, ay, az, gyro beta(x), gamma(y), alpha(z)."""
import json
from pathlib import Path
import numpy as np

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'config/gestures.json'

def load_config(path=DEFAULT_CONFIG):
    config = json.loads(Path(path).read_text())
    baseline = json.loads(DEFAULT_CONFIG.read_text())
    if set(config) != set(baseline):
        raise ValueError('Gesture config keys must match the shipped configuration.')
    for key, val in config.items():
        if key != 'platform_signs' and (not isinstance(val, (int, float)) or not np.isfinite(val) or val <= 0):
            raise ValueError(f'Invalid positive threshold: {key}')
    if not 20 <= config['sample_hz'] <= 100 or config['max_duration'] > 2:
        raise ValueError('Sampling frequency or duration outside limits.')
    for platform in ('ios', 'android', 'other'):
        signs = config['platform_signs'].get(platform, [])
        if len(signs) != 6 or any(x not in (-1, 1) for x in signs):
            raise ValueError('Platform signs must contain six +1/-1 entries.')
    return config

def validate_samples(samples):
    try:
        data = np.asarray(samples, dtype=float)
    except (ValueError, TypeError):
        raise ValueError('Samples must be numeric rows.') from None
    if data.ndim != 2 or data.shape[1] != 7 or not 5 <= len(data) <= 240:
        raise ValueError('Supply 5–240 rows of seven sensor values.')
    if not np.isfinite(data).all() or np.max(np.abs(data[:, 1:])) > 5000:
        raise ValueError('Sensor values must be finite and in range.')
    if np.any(np.diff(data[:, 0]) <= 0) or not 0 < data[-1, 0]-data[0, 0] <= 2:
        raise ValueError('Timestamps must increase in seconds over at most two seconds.')
    return data

def recognize(samples, platform='other', config=None):
    c = config or load_config()
    a = validate_samples(samples).copy()
    a[:, 0] -= a[0, 0]
    duration = a[-1, 0]
    if duration < c['min_duration'] or duration > c['max_duration']:
        return None, 0.0
    t = np.arange(0, duration + .0001, 1/c['sample_hz'])
    x = np.column_stack([np.interp(t, a[:, 0], a[:, i]) for i in range(1, 7)])
    x *= c['platform_signs'].get(platform, c['platform_signs']['other'])
    x = np.column_stack([np.convolve(np.pad(x[:,i], (1,1), mode='edge'), np.ones(3)/3, mode='valid') for i in range(6)])
    active = (np.linalg.norm(x[:,:3], axis=1) > c['idle_accel']) | (np.linalg.norm(x[:,3:], axis=1) > c['idle_gyro'])
    if not active.any():
        return None, 0.0
    indices = np.flatnonzero(active)
    x = x[max(0, indices[0]-2):min(len(x), indices[-1]+3)]
    if len(x) < 8:
        return None, 0.0
    # Preserve raw gyro for net pitch. Demeaning it would erase the Empower signal.
    raw = x.copy()
    x -= x.mean(axis=0)
    ay, gx, gz = x[:,1], x[:,3], x[:,5]
    dt = 1/c['sample_hz']
    span = (len(x)-1)*dt
    signs = np.sign(gz[np.abs(gz) > c['hex_amplitude']])
    changes = int(np.count_nonzero(np.diff(signs)))
    if changes >= c['hex_reversals'] and span <= 1.25:
        return 'hex', min(.99, .75 + .05*changes)
    if span >= .55 and np.std(gx) > c['ward_amplitude'] and np.std(gz) > c['ward_amplitude']:
        lag = max(1, len(x)//4)
        corr = np.corrcoef(gx[:-lag], gz[lag:])[0,1]
        zero_corr = abs(np.corrcoef(gx, gz)[0,1])
        if abs(corr) >= c['ward_correlation'] and zero_corr < .65 and changes < 3:
            return 'ward', min(.99, abs(float(corr)))
    pitch = raw[:,3]
    angle = abs(float(np.sum(pitch)*dt))
    sign_ratio = max(np.mean(pitch > 0), np.mean(pitch < 0))
    jerk = float(np.sqrt(np.mean(np.diff(pitch)**2))/dt)
    if .45 <= span <= 1.35 and angle >= c['empower_angle'] and sign_ratio >= c['empower_sign_ratio'] and jerk < c['empower_jerk_max']:
        return 'empower', min(.99, .75 + .2*angle/90)
    peak = int(np.argmax(np.abs(ay)))
    direction = np.sign(ay[peak])
    reversal = np.max(-direction*ay[peak+1:]) if peak+1 < len(ay) else 0
    if peak*dt <= .4 and abs(ay[peak]) >= c['bolt_peak'] and reversal >= c['bolt_reversal'] and np.sqrt(np.mean(raw[:,3:]**2)) < c['bolt_gyro_max']:
        if np.mean(ay**2) > 1.5*max(np.mean(x[:,0]**2), np.mean(x[:,2]**2)):
            return 'bolt', min(.99, .75 + .2*abs(ay[peak])/15)
    return None, 0.0
