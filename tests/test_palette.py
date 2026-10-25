from pathlib import Path
import colorsys,re

def test_team_contrast_and_health_hue_separation():
    css=(Path(__file__).resolve().parents[1]/'frontend/css/base.css').read_text()
    def rgb(name):
        value = re.search(r'--' + re.escape(name) + r'\s*:\s*#([0-9a-fA-F]{6})', css)[1]
        return tuple(int(value[i:i+2],16)/255 for i in [0,2,4])
    def luminance(c):
        c=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c]
        return sum(x*w for x,w in zip(c,[.2126,.7152,.0722]))
    for name in ['team-a','team-b']:
        color=rgb(name);hp=rgb('hp');h1=colorsys.rgb_to_hsv(*color)[0]*360;h2=colorsys.rgb_to_hsv(*hp)[0]*360
        assert min(abs(h1-h2),360-abs(h1-h2))>=30
        assert (luminance(color)+.05)/(luminance(rgb('panel'))+.05)>=4.5
    assert rgb('hp')!=rgb('mana')
    assert '.enemy .bar i{background:' not in css
