# AIIairs 로고 (단풍잎 + 별) SVG 만들기: python3 make_icons.py → icon.svg, icon-maskable.svg, favicon.svg
# PNG(img/icon-*.png)는 이 SVG를 브라우저로 찍어서 만든다.
import math,sys
def P(cx,cy,a,r): t=math.radians(a); return (cx+r*math.cos(t), cy+r*math.sin(t))
def leaf(cx,cy,s):
    # 단풍잎: 5개 잎끝(별처럼) + 잎끝마다 양옆 톱니
    lobes=[(-90,1.0),(-90+68,0.93),(-90-68,0.93),(-90+132,0.58),(-90-132,0.58)]
    lobes.sort(key=lambda x:x[0]%360)
    pts=[]
    n=len(lobes)
    for i,(a,L) in enumerate(lobes):
        a2,L2=lobes[(i+1)%n]
        span=((a2-a)%360)
        # 잎끝
        pts.append(P(cx,cy,a,L*s))
        # 오른쪽 톱니
        pts.append(P(cx,cy,a+span*0.13,L*s*0.72))
        pts.append(P(cx,cy,a+span*0.24,L*s*0.80))
        pts.append(P(cx,cy,a+span*0.31,L*s*0.60))
        # 골짜기
        pts.append(P(cx,cy,a+span*0.5,s*(0.40 if span>80 else 0.30)))
        # 다음 잎 왼쪽 톱니 (대칭)
        pts.append(P(cx,cy,a2-span*0.31,L2*s*0.60))
        pts.append(P(cx,cy,a2-span*0.24,L2*s*0.80))
        pts.append(P(cx,cy,a2-span*0.13,L2*s*0.72))
    # 줄기: 아래 골짜기(90도)에 끼워 넣는다
    out=[]
    for i,(x,y) in enumerate(pts): out.append((x,y))
    return out
def star(cx,cy,R,r,rot=-90):
    return [P(cx,cy,rot+i*36,R if i%2==0 else r) for i in range(10)]
def path(pts): return 'M'+' L'.join(f'{x:.1f} {y:.1f}' for x,y in pts)+'Z'
def svg(bg,leafc,starc,scale=1.0,rx=0):
    cx,cy=256,262; s=200*scale
    stem=f'<path d="M{cx-7*scale:.1f} {cy+s*0.2:.1f} L{cx+7*scale:.1f} {cy+s*0.2:.1f} L{cx+12*scale:.1f} {cy+s*0.78:.1f} L{cx+0*scale:.1f} {cy+s*0.78:.1f}Z" fill="{leafc}"/>'
    st=path(star(cx,cy-6*scale,s*0.30,s*0.125))
    bgel=f'<rect width="512" height="512" rx="{rx}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{bgel}{stem}<path d="{path(leaf(cx,cy,s))}" fill="{leafc}" stroke="{leafc}" stroke-width="{10*scale:.1f}" stroke-linejoin="round"/><path d="{st}" fill="{starc}" stroke="{starc}" stroke-width="{3*scale:.1f}" stroke-linejoin="round"/></svg>'
INK,BG,ACC='#14110f','#efe8da','#c2410c'
open('icon.svg','w').write(svg(INK,ACC,BG,1.0,0))
open('icon-maskable.svg','w').write(svg(INK,ACC,BG,0.74,0))
open('icon-light.svg','w').write(svg(BG,ACC,BG,1.0,0))
open('favicon.svg','w').write(svg(INK,ACC,BG,1.12,96))
